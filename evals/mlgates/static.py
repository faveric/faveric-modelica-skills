"""Engine-free gates over Modelica text, the spec, the manifest and the record.

Every function returns (status, message) with status in pass|fail|open|skip.
These are text-level checks, not a Modelica parser: they find defects a careful
reader would, and nothing more (see AGENTS.md, known gaps).
"""
import re
from pathlib import Path

from .spec import load_spec, read_text

DECL = re.compile(r"^\s*(?:(?:parameter|constant|input|output|final|inner|outer|discrete)\s+)*Real\b\s+(\w+)(.*)$")
SPEC_RE = None
# Class prefixes the Modelica grammar allows; a short definition (`function f = g(...);`) has no 'end' line.
CLASS_START = re.compile(
    r"^\s*(?:(?:partial|encapsulated|expandable|pure|impure|final|redeclare|replaceable|inner|outer|operator)\s+)*"
    r"(?:package|model|function|block|connector|record|class)\s+(\w+)\b(?!\s*=)", re.M)


# A class header has no ';' (`model A "doc"`), so without this the first declaration of every class is glued to it.
CLASS_HEADER = re.compile(CLASS_START.pattern + r'[ \t]*(?:""[ \t]*)?', re.M)


def _headers_out(t):
    return CLASS_HEADER.sub(lambda m: ";" + "\n" * m.group(0).count("\n"), t)


def _strip_comments(s):
    """Remove comments but keep every newline, so offsets map back to source line numbers."""
    s = re.sub(r"/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), s, flags=re.S)
    return "\n".join(re.sub(r"//.*$", "", ln) for ln in s.splitlines())


def _line(text, pos):
    return text.count("\n", 0, pos) + 1


def _files(root, spec):
    return [Path(root) / p for p in spec["model_files"]]


def g1_syntax(root, spec):
    """Static syntax only. Without an engine the gate is 'skip' at best, never 'pass'."""
    problems = []
    for p in _files(root, spec):
        t = _strip_comments(read_text(p))
        if t.count("(") != t.count(")"):
            problems.append(f"{p.name}: unbalanced parentheses")
        found = [(m.group(1), _line(t, m.start())) for m in CLASS_START.finditer(t)]
        starts = [n for n, _ in found]
        ends = [e for e in re.findall(r"^\s*end\s+(\w+)\s*;", t, flags=re.M) if e not in ("if", "for", "while", "when")]
        if sorted(starts) != sorted(ends):
            no_end = sorted(set(starts) - set(ends))
            no_class = sorted(set(ends) - set(starts))
            where = ", ".join(f"{n} (line {ln})" for n, ln in found if n in no_end)
            problems.append(f"{p.name}: class without 'end' line {no_end or '[]'}{' at ' + where if where else ''}; "
                            f"'end' line without class {no_class}"
                            " (a text check, not a parser: may be a false positive for a class declared or ended more than once,"
                            " or an unusual class prefix; the engine's translation is the authority)")
    if problems:
        return "fail", "; ".join(problems)
    return "skip", "no engine: translation and balance not checked (static syntax ok)"


def _strings_out(t):
    return re.sub(r'"(?:[^"\\]|\\.)*"', lambda m: '""' + "\n" * m.group(0).count("\n"), t)


def g2_units(root, spec):
    missing = []
    for p in _files(root, spec):
        text = _headers_out(_strings_out(_strip_comments(read_text(p))))
        pos = 0
        for stmt in text.split(";"):
            start, pos = pos, pos + len(stmt) + 1
            flat = " ".join(stmt.split())
            m = DECL.match(flat)
            if not m:
                continue
            body = flat[flat.index("Real") + 4:]
            parts, depth, cur = [], 0, ""
            for ch in body:
                depth += ch in "([{"; depth -= ch in ")]}"
                if ch == "," and depth == 0:
                    parts.append(cur); cur = ""
                else:
                    cur += ch
            parts.append(cur)
            for part in parts:
                name = re.match(r"\s*(\w+)", part)
                if name and "unit=" not in part.replace(" ", ""):
                    missing.append(f"{p.name}:{_line(text, start + len(stmt) - len(stmt.lstrip()))}: {name.group(1)}")
    if missing:
        return "fail", ("Real without unit: " + ", ".join(missing)
                        + " (text check: a false positive if the declaration is not a component declaration; unit may come from a type)")
    return "pass", "every Real declaration carries a unit (text check; dimensional consistency of equations needs an engine)"


def g5_guards(root, spec):
    """Every envelope variable declared in the code needs an assert that uses it, and the spec must say,
    per side, which literal bound the assert uses (guard_min / guard_max) or null with a guard_note."""
    text = "\n".join(_strip_comments(read_text(p)) for p in _files(root, spec))
    asserts_list = [a for a in re.findall(r"assert\s*\((.*?)\)\s*;", _strings_out(text), flags=re.S)]
    # Only a conjunction of comparisons can be read as a bound by text matching. An assert with 'or', 'not' or a
    # boolean constant is undecidable here: it is reported as 'cannot decide' (skip), never as a defect.
    complex_ = [a for a in asserts_list if re.search(r"\bor\b|\b(true|false)\b|\bnot\b", a)]
    asserts = " ".join(a for a in asserts_list if a not in complex_)
    complex_text = " ".join(complex_)
    declared = {m.group(1) for ln in text.splitlines() if (m := DECL.match(ln))}
    declared |= set(re.findall(r"\binput\s+Real\s+(\w+)", text))
    problems, undecided = [], []
    lit = r"([-+]?\d+\.?\d*(?:[eE][-+]?\d+)?)"
    for e in spec.get("envelope") or []:
        v = e["var"]
        if v not in declared:
            continue
        if not re.search(rf"\b{re.escape(v)}\b", asserts):
            if re.search(rf"\b{re.escape(v)}\b", complex_text):
                undecided.append(f"{v}: guarded only by an assert with 'or', 'not' or a boolean constant")
            else:
                problems.append(f"{v}: no assert guard")
            continue
        lows = [float(x) for x in re.findall(rf"\b{re.escape(v)}\s*>=?\s*{lit}", asserts)] + \
               [float(x) for x in re.findall(rf"{lit}\s*<=?\s*{re.escape(v)}\b", asserts)]
        highs = [float(x) for x in re.findall(rf"\b{re.escape(v)}\s*<=?\s*{lit}", asserts)] + \
                [float(x) for x in re.findall(rf"{lit}\s*>=?\s*{re.escape(v)}\b", asserts)]
        for key, vals in (("guard_min", lows), ("guard_max", highs)):
            if key not in e:
                problems.append(f"{v}: spec must declare {key} (a number, or null with guard_note)")
            elif e[key] is None:
                if not e.get("guard_note"):
                    problems.append(f"{v}: {key} is null without guard_note")
            elif not any(abs(x - e[key]) <= 1e-12 * max(1.0, abs(e[key])) for x in vals):
                problems.append(f"{v}: assert has no bound equal to {key}={e[key]:g} (found {vals or 'none'})")
            else:
                side = e.get("min") if key == "guard_min" else e.get("max")  # None: envelope unbounded on this side
                if e[key] != side and not e.get("guard_note"):
                    problems.append(f"{v}: {key}={e[key]:g} differs from the envelope bound {side} without guard_note")
    if problems:
        return "fail", "; ".join(problems) + " (text check: an assert written in another form, e.g. through a function, is not seen)"
    if undecided:
        return "skip", ("cannot decide from text: " + "; ".join(undecided)
                        + "; read the assert by hand or let the engine exercise the limit")
    return "pass", "declared envelope variables are guarded by asserts using the declared bounds (limit behaviour needs an engine)"


def g8_reference_state(root, spec):
    rs = (spec.get("reference_state") or {}).get("id")
    if not rs:
        return "fail", "spec declares no reference_state.id"
    text = "\n".join(read_text(p) for p in _files(root, spec))
    tags = re.findall(r"//\s*reference-state:\s*(\S+)", text)
    if not tags:
        return "fail", "no '// reference-state:' tag in the model files"
    if not any(t.strip(" ,;()") == rs for t in tags):
        return "fail", f"reference-state tag {tags} does not match spec id {rs!r}"
    return "pass", f"reference state {rs!r} declared in spec and code (consistency across components needs more than one component)"


def _bib_keys(path):
    if not Path(path).exists():
        return set()
    return set(re.findall(r"@\w+\s*\{\s*([^,\s]+)\s*,", read_text(path)))


def _exceeds(env, val):
    """A null bound means unbounded: a null validity bound limits nothing; a null envelope bound exceeds any finite validity bound."""
    lo_v, hi_v, lo_e, hi_e = val.get("min"), val.get("max"), env.get("min"), env.get("max")
    return (lo_v is not None and (lo_e is None or lo_e < lo_v)) or (hi_v is not None and (hi_e is None or hi_e > hi_v))


def g9_citations(root, spec, bib=None):
    level = spec["level"]
    cands = [bib] if bib else ["refs/refs.bib", "refs.bib"]
    keys = set()
    for c in cands:
        keys |= _bib_keys(Path(root) / c)
    code = "\n".join(read_text(p) for p in _files(root, spec))
    env = {e["var"]: e for e in spec.get("envelope") or []}
    fails, opens = [], []
    for s in spec.get("sources") or []:
        k = s["key"]
        if k not in keys:
            fails.append(f"{k}: not in manifest")
        if not re.search(rf"//\s*cite:\s*{re.escape(k)}\b", code):
            fails.append(f"{k}: no '// cite:' tag in code")
        for v in s.get("validity") or []:
            e = env.get(v["var"])
            if e and _exceeds(e, v) and not s.get("extrapolation_adr"):
                fails.append(f"{k}: envelope of {v['var']} [{e.get('min')}, {e.get('max')}] exceeds validity [{v.get('min')}, {v.get('max')}] and no extrapolation ADR")
        tr = s.get("transcription")
        if tr not in ("pending", "cross-implemented", "numeric-checked"):
            fails.append(f"{k}: transcription status undeclared or unknown ({tr!r})")
        pend = []
        if tr in ("pending", "cross-implemented"):
            pend.append(f"transcription {tr} (only published values from the source give numeric-checked)")
        if level == "L1" and not s.get("validity"):
            fails.append(f"{k}: no validity range recorded (required at L1)")
        if tr == "numeric-checked":
            script = s.get("check_script")
            if not script or not (Path(root) / script).exists():
                fails.append(f"{k}: numeric-checked but check_script missing")
            else:
                import subprocess, sys as _sys
                r = subprocess.run([_sys.executable, "-I", str(Path(script))], cwd=root, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
                if r.returncode != 0:
                    fails.append(f"{k}: check_script failed: {(r.stdout + r.stderr).strip()[:120]}")
        if s.get("validity") and s.get("validity_verified") is not True:
            pend.append("validity ranges not read from the source")
        if str(s.get("locator", "")).strip() in ("", "TO-VERIFY"):
            pend.append("locator TO-VERIFY")
        if pend:
            (fails if level == "L1" else opens).append(f"{k}: " + ", ".join(pend))
    if fails:
        return "fail", "; ".join(fails + opens)
    if opens:
        return "open", "; ".join(opens)
    return "pass", "all sources registered, tagged, within validity, transcription checked"


def g10_fresh(root, spec, record):
    if not Path(record).exists():
        return "skip", "no record"
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools import mlrecord
    res = [m for s, m in mlrecord.check(record, root) if m.startswith("G10")]
    if res:
        return "fail", "; ".join(res)
    return "pass", "stored hashes equal current hashes"


def record_claims(root, record, spec=None, computed=None):
    """Record claims vs its own gates, vs the spec, and vs a fresh recomputation of the gates."""
    if not Path(record).exists():
        return "skip", "no record"
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools import mlrecord
    res = [m for s_, m in mlrecord.check(record, root) if not m.startswith("G10")]
    ents = mlrecord.entries(mlrecord.load(record))
    ext = mlrecord.ext_type(ents)
    if spec is not None and ext:
        lv = (mlrecord.values(ents, ext, "intended-use.level") or [None])[0]
        if lv != spec["level"]:
            res.append(f"record level {lv!r} differs from spec level {spec['level']!r}")
        rec_src = {}
        for v in mlrecord.values(ents, ext, "source"):
            parts = v.split("|")
            if len(parts) == 3:
                rec_src[parts[0]] = parts[2].strip()
        for src in spec.get("sources") or []:
            if rec_src.get(src["key"]) != src.get("transcription"):
                res.append(f"source {src['key']}: record transcription {rec_src.get(src['key'])!r} differs from spec {src.get('transcription')!r}")
    kept = []
    if computed is not None and ext:
        for k, v, _ in ents.get(ext, []):
            if k.startswith(("gate.", "mirror.")):
                g = k.split(".", 1)[1]
                stored = v.split(";")[0].strip().lower()
                if g in computed and g not in ("G10", "RECORD") and computed[g][0] != stored:
                    if computed[g][0] == "skip" and stored in ("pass", "fail") and k.startswith("gate."):
                        kept.append(g)  # not recomputed in this run (no engine here); the stored result stays, bound to its hashes by G10
                        continue
                    res.append(f"{k} stored as {stored} but recomputed as {computed[g][0]}")
        if spec is not None:
            from . import accept
            gaps, problems = accept.parse(spec)
            res += problems
            rec_gaps = {x.split("|")[0] for x in mlrecord.values(ents, ext, "accepted-gap")}
            if rec_gaps != set(gaps):
                res.append(f"record accepted gaps {sorted(rec_gaps)} differ from the issue {sorted(gaps)} (re-run with --write)")
    if res:
        return "fail", "; ".join(res)
    extra = f"; stored results kept, not recomputed in this run: {', '.join(sorted(kept))}" if kept else ""
    return "pass", "record claims agree with its gates, the spec and a fresh run of the gates" + extra


def stored_results(record):
    """{gate: stored value string} for the model gates in the record (status; engine=..; date=..; hash=..)."""
    if not Path(record).exists():
        return {}
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from tools import mlrecord
    ents = mlrecord.entries(mlrecord.load(record))
    ext = mlrecord.ext_type(ents)
    return {k.split(".", 1)[1]: v for k, v, _ in ents.get(ext, []) if k.startswith("gate.")}
