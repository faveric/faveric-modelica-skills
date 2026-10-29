#!/usr/bin/env python3
"""Engine adapter for OpenModelica (omc) — local binary or Docker container.

Implements the engine contract (ADR-0002):
  available() -> bool
  engine_info() -> str
  check_model(files, model, libraries=None, root=None) -> dict
  simulate(files, model, stop_time=1.0, overrides=None, variables=None, libraries=None, root=None) -> dict
  read_results(result_file, variables) -> dict[str, list[float]]
  evaluate_model_gates(root, spec, static_g1=None, static_g2=None, static_g5=None) -> dict
"""
import csv, hashlib, json, math, os, re, shutil, subprocess, tempfile
from pathlib import Path

import yaml

_ENGINE_CACHE = {}
_GATE_CACHE = {}

_CONTAINER_RUNNER = r"""
import csv, json, os, pathlib, shutil, subprocess, sys, tempfile

req = json.loads(sys.stdin.read())
env = os.environ.copy()
for st in req.get("stage_files") or []:
    src_dir = pathlib.Path(st["src"])
    if src_dir.is_dir():
        dst_dir = pathlib.Path(st["dst"])
        dst_dir.mkdir(parents=True, exist_ok=True)
        for f in src_dir.glob(st.get("glob", "*")):
            target = dst_dir / f.name
            if not target.exists():
                shutil.copy2(f, target)
        if st.get("env_var"):
            env[st["env_var"]] = str(dst_dir)

with tempfile.TemporaryDirectory(prefix="omc_eval_") as d:
    d_path = pathlib.Path(d)
    for rel, content in req.get("files", {}).items():
        p = d_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
    mos_path = d_path / "run.mos"
    mos_path.write_text(req["mos"], encoding="utf-8")
    cmd = ["omc"] + req.get("omc_flags", []) + ["run.mos"]
    p = subprocess.run(cmd, cwd=d_path, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=req.get("timeout", 300))
    runs = []
    exe_name = req.get("exe_name")
    if exe_name:
        exe_path = d_path / exe_name
        if exe_path.exists():
            for rspec in req.get("override_runs", []):
                override_arg = ",".join(f"{k}={v}" for k, v in rspec.get("overrides", {}).items())
                rcmd = [str(exe_path), "-output=" + ",".join(rspec.get("vars", ["Q"]))]
                if override_arg:
                    rcmd.append(f"-override={override_arg}")
                rp = subprocess.run(rcmd, cwd=d_path, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
                runs.append({"id": rspec.get("id"), "rc": rp.returncode, "out": rp.stdout, "err": rp.stderr})
    csv_data = {}
    for cfile in sorted(d_path.glob("*_res.csv")):
        with cfile.open("r", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            if rows:
                csv_data[cfile.name] = {k: [float(r[k]) for r in rows if r.get(k) not in (None, "")] for k in rows[0].keys()}
    print(json.dumps({
        "stdout": p.stdout,
        "stderr": p.stderr,
        "returncode": p.returncode,
        "runs": runs,
        "csv_data": csv_data,
    }))
"""


def _load_engine_config(root=None):
    if root is not None:
        cfg_path = Path(root) / ".modelica-skills" / "config.yml"
        if cfg_path.exists():
            try:
                data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
                return data.get("engine") or {}
            except Exception:
                return {}
    return {}


def _detect_docker_container(explicit_container=None):
    docker = shutil.which("docker")
    if not docker:
        return None, None
    cands = []
    if explicit_container:
        cands.append(explicit_container)
    if os.environ.get("OMC_DOCKER_CONTAINER"):
        cands.append(os.environ["OMC_DOCKER_CONTAINER"])
    try:
        ps = subprocess.run([docker, "ps", "--format", "{{.Names}}"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=5)
        if ps.returncode == 0:
            for name in ps.stdout.splitlines():
                if "openmodelica" in name.lower() or "omc" in name.lower():
                    cands.append(name.strip())
    except Exception:
        pass
    for c in dict.fromkeys(cands):
        try:
            p = subprocess.run([docker, "exec", c, "omc", "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
            if p.returncode == 0:
                return c, f"{p.stdout.strip()} (docker:{c})"
        except Exception:
            pass
    return None, None


def _detect_backend(root=None):
    cfg = _load_engine_config(root)
    explicit_container = cfg.get("docker_container")
    cache_id = explicit_container or "default"
    if cache_id in _ENGINE_CACHE:
        return _ENGINE_CACHE[cache_id]
    local_omc = shutil.which("omc")
    if local_omc and not explicit_container:
        try:
            p = subprocess.run([local_omc, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
            if p.returncode == 0:
                _ENGINE_CACHE[cache_id] = ("local", local_omc, p.stdout.strip())
                return _ENGINE_CACHE[cache_id]
        except Exception:
            pass
    cname, cinfo = _detect_docker_container(explicit_container)
    if cname:
        _ENGINE_CACHE[cache_id] = ("docker", cname, cinfo)
        return _ENGINE_CACHE[cache_id]
    for win_cand in (
        r"C:\Program Files\OpenModelica1.27.0-64bit\bin\omc.exe",
        r"C:\Program Files\OpenModelica1.26.0-64bit\bin\omc.exe",
    ):
        if Path(win_cand).exists():
            try:
                p = subprocess.run([win_cand, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=10)
                if p.returncode == 0:
                    _ENGINE_CACHE[cache_id] = ("local", win_cand, p.stdout.strip())
                    return _ENGINE_CACHE[cache_id]
            except Exception:
                pass
    _ENGINE_CACHE[cache_id] = (None, None, "omc not available")
    return _ENGINE_CACHE[cache_id]


def available(root=None):
    kind, _, _ = _detect_backend(root)
    return kind is not None


def engine_info(root=None):
    _, _, info = _detect_backend(root)
    return info


def _collect_files(files, root=None):
    cfg = _load_engine_config(root)
    mount_host = cfg.get("mount_host") or os.environ.get("OMC_LIBRARY_HOST")
    mount_container = cfg.get("mount_container") or os.environ.get("OMC_LIBRARY_CONTAINER", "/library")
    file_map = {}
    load_stmts = []
    for f in files or []:
        p = Path(f) if root is None or Path(f).is_absolute() else (Path(root) / f)
        p_res = p.resolve()
        if mount_host:
            try:
                rel_lib = p_res.relative_to(Path(mount_host).resolve())
                cpath = f"{mount_container.rstrip('/')}/{rel_lib.as_posix()}"
                load_stmts.append((str(p_res), cpath, None, None))
                continue
            except ValueError:
                pass
        rel_key = Path(f).as_posix() if not Path(f).is_absolute() else p_res.name
        content = p_res.read_text(encoding="utf-8")
        file_map[rel_key] = content
        load_stmts.append((str(p_res), rel_key, rel_key, content))
    return file_map, load_stmts


def _exec_payload(req, use_cache=True, root=None):
    cfg = _load_engine_config(root)
    if cfg.get("stage_files") and "stage_files" not in req:
        req = dict(req, stage_files=cfg["stage_files"])
    cache_key = None
    if use_cache and req.get("files"):
        cache_key = hashlib.sha256(json.dumps(req, sort_keys=True).encode()).hexdigest()
        if cache_key in _GATE_CACHE:
            return _GATE_CACHE[cache_key]
    kind, target, _ = _detect_backend(root)
    if kind is None:
        return None
    if kind == "docker":
        p = subprocess.run(
            ["docker", "exec", "-i", target, "python3", "-c", _CONTAINER_RUNNER],
            input=json.dumps(req),
            capture_output=True,
            text=True, encoding="utf-8", errors="replace",
            timeout=req.get("timeout", 300) + 30,
        )
        if p.returncode != 0:
            res = {"stdout": p.stdout, "stderr": p.stderr, "returncode": p.returncode, "runs": [], "csv_data": {}}
        else:
            res = json.loads(p.stdout)
        if cache_key:
            _GATE_CACHE[cache_key] = res
        return res
    with tempfile.TemporaryDirectory(prefix="omc_eval_") as d:
        d_path = Path(d)
        for rel, content in req.get("files", {}).items():
            fp = d_path / rel
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")
        (d_path / "run.mos").write_text(req["mos"], encoding="utf-8")
        cmd = [target] + req.get("omc_flags", []) + ["run.mos"]
        p = subprocess.run(cmd, cwd=d_path, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=req.get("timeout", 300))
        runs = []
        exe_name = req.get("exe_name")
        if exe_name:
            for cand in (d_path / exe_name, d_path / f"{exe_name}.exe"):
                if cand.exists():
                    for rspec in req.get("override_runs", []):
                        override_arg = ",".join(f"{k}={v}" for k, v in rspec.get("overrides", {}).items())
                        rcmd = [str(cand), "-output=" + ",".join(rspec.get("vars", ["Q"]))]
                        if override_arg:
                            rcmd.append(f"-override={override_arg}")
                        rp = subprocess.run(rcmd, cwd=d_path, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
                        runs.append({"id": rspec.get("id"), "rc": rp.returncode, "out": rp.stdout, "err": rp.stderr})
                    break
        csv_data = {}
        for cfile in sorted(d_path.glob("*_res.csv")):
            csv_data[cfile.name] = read_results(cfile)
        return {"stdout": p.stdout, "stderr": p.stderr, "returncode": p.returncode, "runs": runs, "csv_data": csv_data}


def load_library_mos(libraries=None, root=None):
    cfg = _load_engine_config(root)
    lib_paths = cfg.get("library_paths") or {}
    lines = []
    for lib in libraries or []:
        if lib == "Modelica":
            lines.append("loadModel(Modelica); getErrorString();")
        elif lib in lib_paths:
            lines.append(f'loadFile("{lib_paths[lib]}"); getErrorString();')
        elif str(lib).endswith(".mo"):
            lines.append(f'loadFile("{lib}"); getErrorString();')
        else:
            lines.append(f"loadModel({lib}); getErrorString();")
    return "\n".join(lines)


def _infer_model_name(files, root=None, explicit=None):
    if explicit:
        return explicit
    for f in files or []:
        p = Path(f) if root is None or Path(f).is_absolute() else (Path(root) / f)
        text = p.read_text(encoding="utf-8")
        pkg = re.search(r"^\s*package\s+([A-Za-z_]\w*)", text, re.M)
        models = re.findall(r"^\s*model\s+([A-Za-z_]\w*)", text, re.M)
        if pkg and models:
            target = next((m for m in models if "Example" in m), models[-1])
            return f"{pkg.group(1)}.{target}"
        if models:
            return models[-1]
    return None


def _parse_equation_counts(text):
    return [(int(m.group(1)), int(m.group(2))) for m in re.finditer(r"has\s+(\d+)\s+equation\(s\)\s+and\s+(\d+)\s+variable\(s\)", text)]


def _has_unit_inconsistency(text):
    low = text.lower()
    return (
        "inconsistent due to specified unit" in low
        or "incompatible units" in low
        or ("sub-expressions" in low and "unit" in low)
    )


def _parse_output_vars(text):
    vals = {}
    for line in (text or "").splitlines():
        for m in re.finditer(r"([A-Za-z_][\w.]*)=([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)", line):
            vals[m.group(1)] = float(m.group(2))
    return vals


def read_results(result_file, variables=None):
    path = Path(result_file)
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8", errors="replace") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        return {}
    cols = variables or list(rows[0].keys())
    return {k: [float(r[k]) for r in rows if r.get(k) not in (None, "")] for k in cols if k in rows[0]}


def check_model(files, model=None, libraries=None, root=None, build=True, unit_check=True):
    if not available(root):
        return {"ok": None, "balanced": None, "equations": None, "variables": None, "unit_inconsistency": None, "messages": "omc not found", "status": "skip"}
    model = _infer_model_name(files, root=root, explicit=model)
    file_map, load_stmts = _collect_files(files, root=root)
    kind, _, _ = _detect_backend(root)
    loads = [load_library_mos(libraries, root=root)] if libraries else []
    for host_p, cpath, _, _ in load_stmts:
        target_p = cpath if kind == "docker" else host_p
        loads.append(f'loadFile("{target_p}");\ngetErrorString();')
    cmds = loads + [f"checkModel({model});", "getErrorString();"]
    if build:
        cmds += [f"buildModel({model});", "getErrorString();"]
    flags = ["--unitChecking"] if unit_check else []
    res = _exec_payload({"files": file_map, "mos": "\n".join(cmds), "omc_flags": flags}, root=root)
    if res is None:
        return {"ok": None, "balanced": None, "equations": None, "variables": None, "unit_inconsistency": None, "messages": "omc not found", "status": "skip"}
    combined = (res.get("stdout") or "") + "\n" + (res.get("stderr") or "")
    counts = _parse_equation_counts(combined)
    eqs, vrs = counts[-1] if counts else (None, None)
    balanced = (eqs is not None) and (eqs == vrs)
    low = combined.lower()
    build_failed = (
        "translation error" in low
        or "pre-optimization module" in low
        or "clockpartitioning" in low
        or "pantelides" in low
        or "under-determined" in low
        or "over-determined" in low
        or "too many equations" in low
        or "too few equations" in low
        or "error: building" in low
    )
    unit_bad = _has_unit_inconsistency(combined)
    ok = bool(balanced and not build_failed and res.get("returncode") == 0)
    return {
        "ok": ok,
        "balanced": balanced,
        "equations": eqs,
        "variables": vrs,
        "unit_inconsistency": unit_bad,
        "messages": combined,
        "status": "pass" if ok else "fail",
    }


def simulate(files, model=None, stop_time=1.0, overrides=None, variables=None, libraries=None, root=None):
    if not available(root):
        return {"ok": None, "result_file": None, "series": {}, "messages": "omc not found", "status": "skip"}
    model = _infer_model_name(files, root=root, explicit=model)
    file_map, load_stmts = _collect_files(files, root=root)
    kind, _, _ = _detect_backend(root)
    loads = [load_library_mos(libraries, root=root)] if libraries else []
    for host_p, cpath, _, _ in load_stmts:
        target_p = cpath if kind == "docker" else host_p
        loads.append(f'loadFile("{target_p}");\ngetErrorString();')
    sim_flags = f'-override={",".join(f"{k}={v}" for k, v in (overrides or {}).items())}' if overrides else ""
    flag_arg = f', simflags="{sim_flags}"' if sim_flags else ""
    mos = "\n".join(loads + [
        f'simulate({model}, stopTime={stop_time}, outputFormat="csv"{flag_arg});',
        "getErrorString();",
    ])
    res = _exec_payload({"files": file_map, "mos": mos}, root=root)
    if res is None:
        return {"ok": None, "result_file": None, "series": {}, "messages": "omc not found", "status": "skip"}
    combined = (res.get("stdout") or "") + "\n" + (res.get("stderr") or "")
    csv_data = res.get("csv_data") or {}
    ok = bool(csv_data) and "simulation execution failed" not in combined.lower()
    first_csv = next(iter(csv_data.values()), {})
    if variables and first_csv:
        first_csv = {k: v for k, v in first_csv.items() if k in variables}
    return {
        "ok": ok,
        "result_file": next(iter(csv_data.keys()), None),
        "series": first_csv,
        "messages": combined,
        "status": "pass" if ok else "fail",
    }


def _evaluate_library_project(root, spec, static_g1, static_g2, static_g5):
    root = Path(root)
    ver = spec.get("verification") or {}
    libs = ver.get("libraries") or ["Modelica"]
    check_models = ver.get("check_models") or []
    sim_checks = ver.get("simulations") or []

    mos_lines = [load_library_mos(libs, root=root)]
    for cm in check_models:
        mos_lines.append(f"checkModel({cm});")
        mos_lines.append("getErrorString();")
    seen_sims = set()
    for sc in sim_checks:
        m = sc["model"]
        stop = sc.get("stop_time", 1.0)
        if (m, stop) not in seen_sims:
            seen_sims.add((m, stop))
            mos_lines.append(f'simulate({m}, stopTime={stop}, outputFormat="csv");')
            mos_lines.append("getErrorString();")

    h = hashlib.sha256()
    for mf in sorted(spec.get("model_files") or []):
        mp = root / mf
        if mp.exists():
            h.update(mf.encode())
            h.update(mp.read_bytes())
    h.update("\n".join(mos_lines).encode())
    h.update(json.dumps({"g1": static_g1, "g2": static_g2, "g5": static_g5, "sim": sim_checks}, sort_keys=True).encode())
    lib_cache_key = "lib_" + h.hexdigest()
    if lib_cache_key in _GATE_CACHE:
        return dict(_GATE_CACHE[lib_cache_key])

    res = _exec_payload({
        "files": {},
        "mos": "\n".join(mos_lines),
        "omc_flags": ["--unitChecking"],
        "timeout": 600,
    }, use_cache=False, root=root)
    combined = (res.get("stdout") or "") + "\n" + (res.get("stderr") or "")
    low = combined.lower()
    counts = _parse_equation_counts(combined)
    balanced = len(counts) == len(check_models) and all(e == v for e, v in counts)
    check_ok = balanced and "simulation execution failed" not in low and "clockpartitioning" not in low and "pantelides" not in low
    unit_bad = _has_unit_inconsistency(combined)
    csv_data = res.get("csv_data") or {}

    out = {}
    if static_g1 and static_g1[0] == "fail":
        out["G1"] = static_g1
    elif not check_ok:
        out["G1"] = ("fail", f"omc checkModel/simulate failed on library models ({len(counts)}/{len(check_models)} checked)")
    else:
        out["G1"] = ("pass", f"omc checked {len(check_models)} model(s) and simulated {len(csv_data)} model(s) with balanced DAE")

    if static_g2 and static_g2[0] == "fail":
        out["G2"] = static_g2
    elif unit_bad:
        out["G2"] = ("fail", "omc --unitChecking reported unit inconsistency")
    else:
        out["G2"] = ("pass", (static_g2[1] if static_g2 else "units ok") + "; omc --unitChecking passed")

    # Evaluate G3, G4, G5, G6a from simulated CSV trajectories and reference cases
    g3_msgs, g4_msgs, g5_msgs, g6a_msgs = [], [], [], []
    g3_ok, g4_ok, g5_ok, g6a_ok = True, True, (static_g5[0] != "fail" if static_g5 else True), True
    for sc in sim_checks:
        m = sc["model"]
        cname = f"{m}_res.csv"
        series = csv_data.get(cname)
        if not series:
            g3_ok = g4_ok = g5_ok = g6a_ok = False
            g3_msgs.append(f"missing {cname}")
            continue
        gate = sc.get("gate", "G3")
        var = sc.get("var")
        if var and var in series:
            vals = series[var]
            v_end = vals[-1]
            v_min, v_max = min(vals), max(vals)
            max_abs = sc.get("max_abs")
            min_val = sc.get("min")
            max_val = sc.get("max")
            ok = True
            if max_abs is not None and max(abs(x) for x in vals) > max_abs:
                ok = False
            if min_val is not None and v_min < min_val:
                ok = False
            if max_val is not None and v_max > max_val:
                ok = False
            if sc.get("sign_change") and not (v_min < -1e-4 and v_max > 1e-4):
                ok = False
            msg = f"{m}.{var}: end={v_end:.3e}, range=[{v_min:.3e}, {v_max:.3e}]"
            if gate == "G3":
                g3_ok = g3_ok and ok
                g3_msgs.append(msg)
            elif gate == "G4":
                g4_ok = g4_ok and ok
                g4_msgs.append(msg)
            elif gate == "G5":
                g5_ok = g5_ok and ok
                g5_msgs.append(msg)
            elif gate == "G6a":
                g6a_ok = g6a_ok and ok
                g6a_msgs.append(msg)
        else:
            msg = f"{m}.{var}: missing in CSV"
            if gate == "G3":
                g3_ok = False
                g3_msgs.append(msg)
            elif gate == "G4":
                g4_ok = False
                g4_msgs.append(msg)
            elif gate == "G5":
                g5_ok = False
                g5_msgs.append(msg)
            elif gate == "G6a":
                g6a_ok = False
                g6a_msgs.append(msg)
    out["G3"] = ("pass" if g3_ok and g3_msgs else "fail", "; ".join(g3_msgs) or "no G3 simulation checks")
    out["G4"] = ("pass" if g4_ok and g4_msgs else "fail", "; ".join(g4_msgs) or "no G4 simulation checks")
    if static_g5 and static_g5[0] == "fail":
        out["G5"] = static_g5
    else:
        out["G5"] = ("pass" if g5_ok and g5_msgs else "fail", (static_g5[1] + "; " if static_g5 else "") + ("; ".join(g5_msgs) or "no G5 simulation checks"))
    out["G6a"] = ("pass" if g6a_ok and g6a_msgs else "fail", "; ".join(g6a_msgs) or "no G6a simulation checks")
    _GATE_CACHE[lib_cache_key] = dict(out)
    return out


def evaluate_model_gates(root, spec, static_g1=None, static_g2=None, static_g5=None):
    if not available(root):
        return None
    return _evaluate_library_project(root, spec, static_g1, static_g2, static_g5)
