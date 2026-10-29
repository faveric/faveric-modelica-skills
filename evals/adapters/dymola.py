#!/usr/bin/env python3
"""Engine adapter for Dymola, through the functions of the Dymola MCP server (server/dymola_mcp.py, ADR-0016/0017).

Same entry point as the OpenModelica adapter: evaluate_model_gates(root, spec, static_g1, static_g2, static_g5).
It calls translate_model and run_simulation in-process, so the result and its hash are computed by this code,
not typed in. Configuration (.modelica-skills/config.yml):

  engine:
    backend: dymola
    dymola: {path: <install dir>, packages: [<package.mo>...], basedir: <dir for relative package paths>}

What it can and cannot establish:
  G1  translation of every verification.check_models entry and every simulated model; no equation-count parsing.
  G2  stays the static text result: translate_model returns no unit check.
  G3, G4, G5, G6a  from verification.simulations entries (model, var, stop_time, max_abs / min / max / sign_change),
      judged on the min and max over time of the variable. A gate with no entry is skip; a trajectory that could
      not be read is skip, never pass.

Tested only against a fake DymolaInterface. Not run against a real Dymola (see AGENTS.md, known gaps).
"""
import importlib.util
from pathlib import Path

from . import omc_cli

SERVER = Path(__file__).resolve().parents[2] / "server" / "dymola_mcp.py"
MODEL_GATES = ("G3", "G4", "G5", "G6a")
_server = None
_version = None


def _load_server():
    """Import server/dymola_mcp.py by path; raises ImportError when the mcp package is missing."""
    global _server
    if _server is None:
        spec = importlib.util.spec_from_file_location("dymola_mcp_adapter", SERVER)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        _server = mod
    return _server


def _config(root):
    return (omc_cli._load_engine_config(root).get("dymola")) or {}


def _kwargs(root):
    cfg = _config(root)
    kw = {}
    if cfg.get("packages"):
        kw["packages"] = list(cfg["packages"])
    if cfg.get("basedir"):
        kw["basedir"] = cfg["basedir"]
    if cfg.get("path"):
        kw["dymola_path"] = cfg["path"]
    return kw


def available(root=None):
    try:
        return _load_server().interface_importable(_config(root).get("path"))
    except ImportError:
        return False


def engine_info(root=None):
    return f"Dymola {_version} (via dymola_mcp)" if _version else "Dymola (version not reported; via dymola_mcp)"


def _unavailable(reason):
    return {g: ("skip", f"Dymola not usable: {reason}") for g in MODEL_GATES}


def _judge(check, stats):
    """(status, message) for one simulation check against {min, max} over time."""
    var, mn, mx = check.get("var"), stats["min"], stats["max"]
    ok = True
    if check.get("max_abs") is not None and max(abs(mn), abs(mx)) > check["max_abs"]:
        ok = False
    if check.get("min") is not None and mn < check["min"]:
        ok = False
    if check.get("max") is not None and mx > check["max"]:
        ok = False
    if check.get("sign_change") and not (mn < -1e-4 and mx > 1e-4):
        ok = False
    return ("pass" if ok else "fail"), f"{check['model']}.{var}: range=[{mn:.3e}, {mx:.3e}]"


def evaluate_model_gates(root, spec, static_g1=None, static_g2=None, static_g5=None):
    global _version
    try:
        srv = _load_server()
    except ImportError as exc:
        return _unavailable(f"server module needs the mcp package ({exc})")
    if not srv.interface_importable(_config(root).get("path")):
        return _unavailable("Dymola Python interface not importable (set engine.dymola.path)")
    kw = _kwargs(root)
    ver = spec.get("verification") or {}
    sims = ver.get("simulations") or []
    models = list(dict.fromkeys(list(ver.get("check_models") or []) + [s["model"] for s in sims]))

    problems = []
    for m in models:
        try:
            r = srv.translate_model(m, **kw)
        except Exception as exc:
            return _unavailable(f"translate_model raised {type(exc).__name__}: {exc}")
        _version = r.get("engine_version") or _version
        if not r.get("success"):
            problems.append(f"{m}: {str(r.get('error'))[:200]}")

    out = {}
    if static_g1 and static_g1[0] == "fail":
        out["G1"] = static_g1
    elif problems:
        out["G1"] = ("fail", "Dymola translation failed: " + "; ".join(problems))
    elif not models:
        out["G1"] = ("skip", "no verification.check_models or simulations declared; nothing translated")
    else:
        out["G1"] = ("pass", f"Dymola translated {len(models)} model(s); equation count and warnings are not parsed")
    out["G2"] = static_g2 or ("skip", "no static G2 result")
    if out["G2"][0] == "pass":
        out["G2"] = ("pass", out["G2"][1] + "; Dymola: unit check not run by translate_model")

    runs = {}
    for key in dict.fromkeys((s["model"], s.get("stop_time", 1.0)) for s in sims):
        names = list(dict.fromkeys(s["var"] for s in sims if (s["model"], s.get("stop_time", 1.0)) == key and s.get("var")))
        try:
            runs[key] = srv.run_simulation(key[0], names, stop_time=key[1], with_stats=True, **kw)
        except Exception as exc:
            runs[key] = {"__error__": f"{type(exc).__name__}: {str(exc)[:200]}"}
        _version = runs[key].get("__engine_version__") or _version

    per = {g: [] for g in MODEL_GATES}
    for c in sims:
        gate = c.get("gate", "G3")
        run = runs[(c["model"], c.get("stop_time", 1.0))]
        if gate not in per:
            continue
        if run.get("__error__") or run.get("__warning__"):
            per[gate].append(("fail", f"{c['model']}: simulation failed: {run.get('__error__') or run.get('__warning__')}"[:240]))
        elif c.get("var") not in (run.get("__stats__") or {}):
            per[gate].append(("skip", f"{c['model']}.{c.get('var')}: trajectory not available ({run.get('__stats_error__', 'no stats returned')})"))
        else:
            per[gate].append(_judge(c, run["__stats__"][c["var"]]))
    for g in MODEL_GATES:
        items = per[g]
        if g == "G5" and static_g5 and static_g5[0] == "fail":
            out[g] = static_g5
        elif not items:
            out[g] = ("skip", f"no {g} entry in verification.simulations")
        else:
            st = "fail" if any(s == "fail" for s, _ in items) else "skip" if any(s == "skip" for s, _ in items) else "pass"
            out[g] = (st, "; ".join(m for _, m in items))
    return out
