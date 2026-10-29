"""Run all engine-free (or engine-backed) gates on a project directory (a copy of the example or a real repo).

Keys: G1..G10 judge the MODEL. Without an engine, G3/G6a are 'skip' (nothing was computed on the model).
When engine='omc' or 'dymola' is supplied, G1..G6a are evaluated on the Modelica model by that engine.
M3/M4/M5/M6a are the same checks on the Python mirror: informative about the physics and the checks,
not about the Modelica file (their equivalence is not checked).
"""
from pathlib import Path

from . import static
from .spec import load_spec

NEED_ENGINE = "needs an engine run of the model"


def run_all(root, spec_name="ISSUE.md", record=None, engine=None):
    root = Path(root)
    spec = load_spec(root / spec_name)
    tol = spec.get("tolerances") or {}
    if record is None:
        recs = sorted((root / "records").glob("*.srmd.xml")) if (root / "records").is_dir() else []
        rec = recs[0] if recs else (root / "records" / "credibility-record.srmd.xml")
    else:
        rec = root / record
    out = {}
    g1 = static.g1_syntax(root, spec)
    g2 = static.g2_units(root, spec)
    g5, g5msg = static.g5_guards(root, spec)
    out["G1"] = g1
    out["G2"] = g2
    out["G5"] = (g5, g5msg) if g5 == "fail" else ("skip", g5msg + "; limit-case behaviour needs an engine")
    for g in ("G3", "G6a"):
        out[g] = ("skip", NEED_ENGINE)
    if engine in ("omc", True):
        from evals.adapters import omc_cli
        eng_res = omc_cli.evaluate_model_gates(root, spec, static_g1=g1, static_g2=g2, static_g5=(g5, g5msg))
        if eng_res:
            out.update(eng_res)
    elif engine == "dymola":
        from evals.adapters import dymola
        eng_res = dymola.evaluate_model_gates(root, spec, static_g1=g1, static_g2=g2, static_g5=(g5, g5msg))
        if eng_res:
            out.update(eng_res)
    out["G8"] = static.g8_reference_state(root, spec)
    out["G9"] = static.g9_citations(root, spec)
    out["G10"] = static.g10_fresh(root, spec, rec)
    out["RECORD"] = static.record_claims(root, rec, spec, out)
    return out
