#!/usr/bin/env python3
"""Run the gates on a project; --write stores results and file hashes in its record.

  python3 evals/run_gates.py <model-dir> [--spec ISSUE.md] [--record records/x.srmd.xml]
                             [--engine none|omc|dymola|auto] [--write] [--raw] [--question TEXT]

Model gates are G*; M* are checks on the Python mirror (see evals/mlgates/run.py). The record never
receives M* as gate results: they go to `mirror.*` entries. The default output is the one-page summary
(evals/mlgates/summary.py); --raw prints every gate with its full message.

A result the current run could not recompute (no engine here) does not overwrite an earlier engine result in
the record when the files are unchanged since it was computed. A gate accepted in the issue (`accepted_gaps`)
keeps its raw result but no longer fails the run.
"""
import argparse, datetime, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evals.mlgates import accept, summary  # noqa: E402
from evals.mlgates.run import run_all  # noqa: E402
from evals.mlgates import static  # noqa: E402
from evals.mlgates.spec import load_spec  # noqa: E402
from tools import mlrecord  # noqa: E402

ENGINE = "none (static + numeric mirror)"


def evaluated_files(root, spec, spec_name):
    root = Path(root)
    files = list(spec["model_files"]) + [spec_name]
    for extra in ("refs/refs.bib", "refs.bib"):
        if (root / extra).exists():
            files.append(extra)
    files += list(spec.get("evidence_files") or [])
    for s in spec.get("sources") or []:
        for cand in (f"refs/transcriptions/{s['key']}.md", s.get("check_script")):
            if cand and (root / cand).exists():
                files.append(cand)
    rc = spec.get("reference_cases") or {}
    files += [x for x in (rc.get("script"), rc.get("file")) if x and (root / x).exists()]
    return sorted(set(files))


def _record_path(root, record):
    """The record: the given one, else the first in records/, else the default name."""
    if record:
        return Path(root) / record
    recs = sorted((Path(root) / "records").glob("*.srmd.xml")) if (Path(root) / "records").is_dir() else []
    return recs[0] if recs else Path(root) / "records" / "credibility-record.srmd.xml"


def resolve_engine(root, engine):
    """'auto' takes engine.backend from .modelica-skills/config.yml when engine.mode is mcp; anything else is static-only."""
    if engine in ("omc", "dymola"):
        return engine
    if engine == "auto":
        from evals.adapters import omc_cli
        cfg = omc_cli._load_engine_config(root)
        if cfg.get("mode") == "mcp" and cfg.get("backend") in ("omc", "dymola"):
            return cfg["backend"]
    return None


def write_record(root, record, spec_name, res, engine=None):
    root = Path(root)
    rec = root / record if record else None
    if rec is None or not rec.exists():
        recs = sorted((root / "records").glob("*.srmd.xml")) if (root / "records").is_dir() else []
        rec = recs[0] if recs else (root / "records" / "credibility-record.srmd.xml")
    spec = load_spec(root / spec_name)
    ents = mlrecord.entries(mlrecord.load(rec))
    ext = mlrecord.ext_type(ents)
    files = evaluated_files(root, spec, spec_name)
    mlrecord.replace_entries(rec, ext, "model.file", [f"{f}|{mlrecord.sha256(root / f)}" for f in files])
    ents = mlrecord.entries(mlrecord.load(rec))
    digest = mlrecord.combined_digest(ents, ext, root)
    date = datetime.date.today().isoformat()
    eng_label = ENGINE
    if engine in ("omc", True):
        from evals.adapters import omc_cli
        eng_label = omc_cli.engine_info()
    elif engine == "dymola":
        from evals.adapters import dymola
        eng_label = dymola.engine_info(root)
    stored = {k: v for k, v, _ in ents.get(ext, []) if k.startswith("gate.")}
    eff = {}
    for g, (s, _) in res.items():
        if g in ("RECORD", "G10"):
            continue  # judged afresh on every run; never stored
        key = ("mirror." if g.startswith("M") else "gate.") + g
        old = stored.get(key)
        if (s == "skip" and old and old.split(";")[0].strip().lower() in ("pass", "fail")
                and mlrecord.gate_hash(old) == digest):
            eff[g] = old.split(";")[0].strip().lower()
            continue  # not recomputed in this run: the earlier engine result for these exact files stays visible
        eff[g] = s
        mlrecord.set_entry(rec, ext, key, f"{s}; engine={eng_label}; date={date}; hash={digest}")
    gaps, _ = accept.parse(spec)
    mlrecord.replace_entries(rec, ext, "accepted-gap", accept.record_values(gaps))
    mlrecord.set_entry(rec, ext, "acceptance", accept.acceptance_text(gaps))
    mlrecord.set_entry(rec, ext, "intended-use.level", spec["level"])
    mlrecord.replace_entries(rec, ext, "source", [f"{s['key']}|{s.get('locator')}|{s.get('transcription')}" for s in spec.get("sources") or []])
    model_ok = all(eff.get(g, "skip") == "pass" for g in ("G1", "G2", "G3", "G4", "G5"))
    mlrecord.set_entry(rec, ext, "coherence-checks",
                       "passed (G1-G5)" if model_ok else "not established: " + ", ".join(
                           f"{g}={eff.get(g, 'skip')}" for g in ("G1", "G2", "G3", "G4", "G5") if eff.get(g, "skip") != "pass"))


def execute(root, spec="ISSUE.md", record=None, engine=None, write=False):
    """Run the gates; with write=True also refresh the record. Returns {gate: (status, message)}."""
    eng = resolve_engine(root, engine)
    res = run_all(root, spec_name=spec, record=record, engine=eng)
    if write:
        write_record(root, record, spec, res, engine=eng)
        root_p = Path(root)
        spec_d = load_spec(root_p / spec)
        rec_p = _record_path(root_p, record)
        res["G10"] = static.g10_fresh(root_p, spec_d, rec_p)
        res["RECORD"] = static.record_claims(root_p, rec_p, spec_d, res)
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("--spec", default="ISSUE.md")
    ap.add_argument("--record", default=None)
    ap.add_argument("--engine", default=None, choices=[None, "none", "omc", "dymola", "auto"])
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--raw", action="store_true", help="print every gate with its full message instead of the summary")
    ap.add_argument("--question", default=None, help="the physical question of the task, printed at the top of the summary")
    a = ap.parse_args(argv)
    res = execute(a.root, a.spec, a.record, a.engine, a.write)
    gaps, _ = accept.parse(load_spec(Path(a.root) / a.spec))
    if a.raw:
        for g in sorted(res, key=lambda x: (x[0] == "R", x[0] == "M", len(x), x)):
            s, m = res[g]
            print(f"{g:7} {s.upper():5} {m}" + ("  [accepted gap]" if g in gaps else ""))
    else:
        stored = static.stored_results(_record_path(a.root, a.record))
        print(summary.render(res, gaps, stored, a.question))
    if a.write:
        print("record updated")
    return 1 if accept.blocking(res, gaps) else 0


if __name__ == "__main__":
    sys.exit(main())
