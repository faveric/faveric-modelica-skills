#!/usr/bin/env python3
"""Learner for the library overlay (ADR-0018): evidence from a finished issue, candidates, approval, library.

  python3 tools/mllearn.py collect <ISSUE> [--root .]
  python3 tools/mllearn.py propose --issue <ISSUE> --kind note|skill|proposal --target <name> --title "..." \
                                   --evidence E1,E2 --body-file <path|-> [--root .]
  python3 tools/mllearn.py list [--status candidate|active|rejected|archived] [--root .]
  python3 tools/mllearn.py show <ID> | edit <ID> --body-file <path|-> | index | verify
  python3 tools/mllearn.py approve <ID> --by <name> | reject <ID> --by <name> --reason "..." | retire <ID> --by <name> --reason "..."

Everything lives under `.modelica-skills/learned/` of the target library: evidence/<ISSUE>.json (what the learner may
cite), entries/<ID>.json (candidates and their later status), ledger.jsonl (append-only), index.md (generated),
<base-skill>.md (approved notes) and, outside it, `.claude/skills/<name>/SKILL.md` (approved library skills).

The learner proposes; a person approves. `approve` is only called by the user-invoked `approve-lessons` skill.
This is a rule of the workflow and is visible in the ledger (who, when, file hash); it is not a sandbox.
Validation is text matching: it refuses what it can recognise, not everything unwise.
"""
import argparse, datetime, hashlib, json, os, re, subprocess, sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from tools import mlissue  # noqa: E402

LEARNED = Path(".modelica-skills") / "learned"
KINDS = ("note", "skill", "proposal")
BASE_SKILLS = {"setup-modelica-skills", "interview-model", "to-issue", "to-tasks", "implement", "review-model", "calibrate",
               "verify-physics", "cite-source", "credibility-record", "model-design", "diagnosing-simulation", "interviewing",
               "learn-from-issue", "approve-lessons"}
MAX_NOTE, MAX_TITLE, MAX_SKILL_LINES, MAX_DESC = 400, 120, 120, 300
GENERIC_NAMES = {"modelica", "examples", "tests", "test", "interfaces", "components", "types", "utilities", "icons", "package", "library"}
FORBIDDEN = [
    (r"\b(loosen|relax|widen|raise|increase|enlarge)\b[^.\n]{0,40}\btoleran", "tells the agent to loosen a tolerance"),
    (r"\b(remove|delete|drop|comment out|disable|bypass|weaken)\b[^.\n]{0,30}\b(asserts?|guards?|range checks?|gates?|checks?)\b",
     "tells the agent to remove or disable a guard or check"),
    (r"\b(skip|ignore|suppress)\b[^.\n]{0,30}\b(gates?|failures?|warnings?|accepted[_ ]gaps?|checks?)\b",
     "tells the agent to skip or ignore a gate"),
    (r"\b(edit|modify|write)\b[^.\n]{0,20}\b(the )?(record|hash(es)?|gate\.)", "tells the agent to edit generated record entries"),
    (r"https?://|\bcurl\b|\bwget\b", "contains a URL or a download command"),
    (r"\b(ignore|forget|disregard)\b[^.\n]{0,30}\b(previous|above|earlier|all)\b[^.\n]{0,20}\b(instructions?|rules?)\b",
     "reads as an attempt to override instructions"),
]


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _cfg(root):
    p = Path(root) / ".modelica-skills" / "config.yml"
    try:
        return (yaml.safe_load(p.read_text(encoding="utf-8")) or {}).get("learning") or {}
    except (OSError, yaml.YAMLError):
        return {}


def _dir(root):
    d = Path(root) / LEARNED
    (d / "entries").mkdir(parents=True, exist_ok=True)
    (d / "evidence").mkdir(parents=True, exist_ok=True)
    return d


def _skills_dir(root):
    return Path(root) / (_cfg(root).get("skills_dir") or ".claude/skills")


def _load_entries(root):
    d = Path(root) / LEARNED / "entries"
    out = {}
    for p in sorted(d.glob("*.json")) if d.is_dir() else []:
        e = json.loads(p.read_text(encoding="utf-8"))
        out[e["id"]] = e
    return out


def _save(root, entry):
    (_dir(root) / "entries" / f"{entry['id']}.json").write_text(json.dumps(entry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _ledger(root, action, entry_id, by, **extra):
    rec = {"ts": now(), "action": action, "id": entry_id, "by": by, **extra}
    with (_dir(root) / "ledger.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


# ---- evidence -------------------------------------------------------------------------------------------------

def _git(root, *args):
    try:
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout if r.returncode == 0 else None


NUM = r"[-+]?\d[\d.]*(?:[eE][-+]?\d+)?"


def _flags(root, issue):
    """Deterministic owner flags from the issue's commits: removed or rewritten asserts, loosened tolerances."""
    log = _git(root, "log", "--fixed-strings", "--grep", issue, "--format=COMMIT:%H", "-p", "--no-color")
    if not log:
        return []
    flags, sha_, path, olds, news = [], None, None, {}, {}

    def close_file():
        for k in olds.keys() & news.keys():
            old, new = float(olds[k]), float(news[k])
            if new != old:
                loose = new < old if k.endswith("floor") else abs(new) > abs(old)
                flags.append({"kind": "flag", "ref": "tolerance-" + ("loosened" if loose else "changed"),
                              "text": f"{k}: {olds[k]} -> {news[k]} in {path} at {sha_[:10]}"})
        olds.clear(); news.clear()

    for ln in log.splitlines():
        if ln.startswith("COMMIT:"):
            close_file(); sha_ = ln[7:]; path = None
        elif ln.startswith("+++ "):
            close_file(); path = ln[6:] if ln.startswith("+++ b/") else None
        elif path and ln.startswith("-") and not ln.startswith("---"):
            if path.endswith(".mo") and re.match(r"-\s*assert\s*\(", ln):
                flags.append({"kind": "flag", "ref": "assert-removed-or-rewritten", "text": f"{ln[1:].strip()[:100]} in {path} at {sha_[:10]}"})
            if path.endswith(".md"):
                for k, v in re.findall(rf"(G\w*?_[A-Za-z_0-9]+):\s*({NUM})", ln):
                    olds[k] = v
        elif path and path.endswith(".md") and ln.startswith("+") and not ln.startswith("+++"):
            for k, v in re.findall(rf"(G\w*?_[A-Za-z_0-9]+):\s*({NUM})", ln):
                news[k] = v
    close_file()
    return flags


def collect(root, issue):
    root = Path(root)
    problems = mlissue.can_close(issue, str(root / "docs" / "issues"))
    if problems:
        raise ValueError("the learner starts after the conclusion is written: " + "; ".join(problems))
    concl = root / "docs" / "issues" / f"{issue}-conclusion.md"
    text = concl.read_text(encoding="utf-8-sig", errors="replace")
    items = [{"id": "E1", "kind": "conclusion", "ref": concl.relative_to(root).as_posix(), "text": text}]
    log = _git(root, "log", "--fixed-strings", "--grep", issue, "--format=%H%x09%s")
    for ln in (log or "").splitlines():
        h, _, subj = ln.partition("\t")
        items.append({"id": f"E{len(items) + 1}", "kind": "commit", "ref": h, "text": subj})
    issue_file = next((f for f in sorted((root / "docs" / "issues").glob(f"{issue}*.md")) if not f.name.endswith("-conclusion.md")), None)
    if issue_file:
        from evals.mlgates.spec import load_spec
        try:
            spec = load_spec(issue_file)
        except (ValueError, OSError, yaml.YAMLError):
            spec = {}
        for g in spec.get("accepted_gaps") or []:
            items.append({"id": f"E{len(items) + 1}", "kind": "accepted-gap", "ref": str(g.get("gate")),
                          "text": f"{g.get('owner')}: {g.get('reason')}"})
    for i, f in enumerate(_flags(root, issue), 1):
        items.append({"id": f"F{i}", **f})
    entries = _load_entries(root)
    bundle = {"issue": issue, "created": now(), "items": items,
              "existing": [f"{e['id']} [{e['status']}] {e['kind']} {e['target']}: {e['title']}" for e in entries.values()
                           if e["status"] in ("candidate", "active")]}
    p = _dir(root) / "evidence" / f"{issue}.json"
    p.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return p, bundle


# ---- validation -----------------------------------------------------------------------------------------------

def deny_terms(root):
    root = Path(root)
    terms = {str(t).lower() for t in _cfg(root).get("deny_terms") or []}
    terms.add(root.resolve().name.lower())
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "refs")]
        if len(Path(dirpath).relative_to(root).parts) > 6:
            dirs[:] = []
        if "package.mo" in files:
            try:
                t = (Path(dirpath) / "package.mo").read_text(encoding="utf-8-sig", errors="replace")
            except OSError:
                continue
            terms.update(m.lower() for m in re.findall(r"^\s*(?:within\s+[\w.]*\s*;\s*)?package\s+(\w+)", t, flags=re.M))
    return {t for t in terms if len(t) >= 4 and t not in GENERIC_NAMES}


def _frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return None
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None
    return fm if isinstance(fm, dict) else None


def validate(root, e):
    """Return a list of reasons the entry is refused (empty: valid)."""
    root, bad = Path(root), []
    if e["kind"] not in KINDS:
        return [f"kind must be one of {KINDS}"]
    title, body = e["title"].strip(), e["body"]
    if not title or len(title) > MAX_TITLE or "\n" in title:
        bad.append(f"title must be one line of 1 to {MAX_TITLE} characters")
    if not body.strip():
        bad.append("body is empty")
    ev = root / LEARNED / "evidence" / f"{e['issue']}.json"
    if not ev.exists():
        return bad + [f"no evidence bundle for {e['issue']}: run `collect` first"]
    items = {i["id"]: i for i in json.loads(ev.read_text(encoding="utf-8"))["items"]}
    if not e["evidence"]:
        bad.append("evidence ids are required")
    for i in e["evidence"]:
        if i not in items:
            bad.append(f"evidence {i} is not in the bundle")
        elif items[i]["kind"] == "flag":
            bad.append(f"evidence {i} is an owner flag; flags are not lessons")
    for pat, why in FORBIDDEN:
        if re.search(pat, title + "\n" + body, flags=re.I):
            bad.append(f"refused: {why}")
    others = [x for x in _load_entries(root).values() if x["id"] != e.get("id")]
    live = [x for x in others if x["issue"] == e["issue"] and x["status"] in ("candidate", "active")]
    if len(live) >= int(_cfg(root).get("max_per_issue") or 3):
        bad.append(f"already {len(live)} live entries for {e['issue']} (limit {_cfg(root).get('max_per_issue') or 3})")
    norm = lambda s: " ".join(s.lower().split())
    if any(x["status"] in ("candidate", "active") and (norm(x["title"]) == norm(title) or norm(x["body"]) == norm(body)) for x in others):
        bad.append("duplicates an existing candidate or active entry")
    t = e["target"]
    if e["kind"] in ("note", "proposal"):
        if t not in BASE_SKILLS:
            bad.append(f"target must be a base skill name: {sorted(BASE_SKILLS)}")
    if e["kind"] == "note" and (len(body.strip()) > MAX_NOTE or "\n" in body.strip()):
        bad.append(f"a note is one paragraph of at most {MAX_NOTE} characters")
    if e["kind"] == "proposal":
        hit = sorted(x for x in deny_terms(root) if re.search(rf"\b{re.escape(x)}\b", title + " " + body, flags=re.I))
        if hit:
            bad.append(f"a universal proposal must not name the library: found {hit}")
    if e["kind"] == "skill":
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{2,40}", t) or t in BASE_SKILLS:
            bad.append("skill name: 3 to 41 lowercase letters, digits or hyphens, not a base skill name")
        elif (_skills_dir(root) / t).exists():
            bad.append(f"{_skills_dir(root).name}/{t} already exists; a learned skill never overwrites a skill")
        fm = _frontmatter(body)
        if fm is None:
            bad.append("skill body must start with front matter (name, description)")
        else:
            if set(fm) - {"name", "description"}:
                bad.append(f"front matter may only hold name and description, found extra keys {sorted(set(fm) - {'name', 'description'})}")
            if fm.get("name") != t:
                bad.append("front matter name must equal the target")
            d = str(fm.get("description") or "")
            if not d or len(d) > MAX_DESC or not re.search(r"\b(use|when)\b", d, flags=re.I):
                bad.append(f"description: 1 to {MAX_DESC} characters and a trigger sentence ('Use when ...')")
        if len(body.splitlines()) > MAX_SKILL_LINES:
            bad.append(f"skill is over {MAX_SKILL_LINES} lines")
    return bad


# ---- lifecycle ------------------------------------------------------------------------------------------------

def propose(root, issue, kind, target, title, evidence, body):
    entries = _load_entries(root)
    n = 1 + sum(1 for e in entries.values() if e["issue"] == issue)
    e = {"id": f"L-{issue}-{n}", "kind": kind, "target": target, "title": title.strip(), "issue": issue,
         "evidence": list(evidence), "body": body.strip("\n") if kind == "skill" else body.strip(), "status": "candidate", "created": now()}
    bad = validate(root, e)
    if bad:
        raise ValueError("; ".join(bad))
    _save(root, e)
    _ledger(root, "proposed", e["id"], "learner", body_sha=sha(e["body"]))
    return e


def edit(root, entry_id, body):
    e = _load_entries(root)[entry_id]
    if e["status"] != "candidate":
        raise ValueError("only a candidate can be edited")
    e["body"] = body.strip("\n") if e["kind"] == "skill" else body.strip()
    bad = validate(root, e)
    if bad:
        raise ValueError("; ".join(bad))
    _save(root, e)
    _ledger(root, "edited", entry_id, "owner", body_sha=sha(e["body"]))
    return e


def approve(root, entry_id, by):
    if not by.strip():
        raise ValueError("--by is required: who approves")
    e = _load_entries(root).get(entry_id)
    if e is None or e["status"] != "candidate":
        raise ValueError(f"{entry_id} is not a candidate")
    if e["kind"] == "proposal":
        raise ValueError("a proposal is not installed here: carry it to the public skills repository by a pull request")
    bad = validate(root, e)
    if bad:
        raise ValueError("; ".join(bad))
    root = Path(root)
    if e["kind"] == "note":
        p = _dir(root) / f"{e['target']}.md"
        line = f"- [{e['id']}] ({e['created'][:10]}; {e['issue']}) {e['body']}\n"
        if not p.exists():
            p.write_text(f"# Library lessons for {e['target']}\n\nApproved by the owner (tools/mllearn.py). One line each.\n\n", encoding="utf-8")
        with p.open("a", encoding="utf-8") as f:
            f.write(line)
        art = {"path": p.relative_to(root).as_posix(), "sha256": sha(line)}
    else:
        p = _skills_dir(root) / e["target"] / "SKILL.md"
        p.parent.mkdir(parents=True, exist_ok=True)
        text = e["body"].rstrip("\n") + "\n"
        p.write_text(text, encoding="utf-8")
        art = {"path": p.relative_to(root).as_posix(), "sha256": sha(text)}
    e.update(status="active", approved_by=by.strip(), approved=now(), artifact=art)
    _save(root, e)
    _ledger(root, "approved", e["id"], by.strip(), artifact=art)
    write_index(root)
    return e


def _close(root, entry_id, by, reason, status, action):
    e = _load_entries(root).get(entry_id)
    allowed = ("candidate",) if status == "rejected" else ("active",)
    if e is None or e["status"] not in allowed:
        raise ValueError(f"{entry_id} cannot be {status} from its current state")
    if not by.strip() or not reason.strip():
        raise ValueError("--by and --reason are required")
    if status == "archived" and e["kind"] != "proposal":
        art = e["artifact"]
        p = Path(root) / art["path"]
        if e["kind"] == "skill" and p.exists():
            arch = _dir(root) / "archive" / e["target"]
            arch.mkdir(parents=True, exist_ok=True)
            p.replace(arch / "SKILL.md")
            try:
                p.parent.rmdir()
            except OSError:
                pass
        elif e["kind"] == "note" and p.exists():
            lines = [ln for ln in p.read_text(encoding="utf-8").splitlines(keepends=True) if not ln.startswith(f"- [{e['id']}]")]
            p.write_text("".join(lines), encoding="utf-8")
    e.update(status=status, closed_by=by.strip(), closed=now(), reason=reason.strip())
    _save(root, e)
    _ledger(root, action, entry_id, by.strip(), reason=reason.strip())
    write_index(root)
    return e


def reject(root, entry_id, by, reason):
    return _close(root, entry_id, by, reason, "rejected", "rejected")


def retire(root, entry_id, by, reason):
    """Archive, never delete: a skill moves to learned/archive/, a note leaves its file, the entry stays."""
    return _close(root, entry_id, by, reason, "archived", "retired")


def write_index(root):
    lines = ["# Library lessons (generated by tools/mllearn.py; do not edit)", "",
             "One line per approved entry. Open the file only when its cue matches the work.", ""]
    for e in _load_entries(root).values():
        if e["status"] == "active":
            lines.append(f"- [{e['id']}] {e['kind']} `{e['target']}`: {e['title']} ({e['issue']}; {e['artifact']['path']})")
    p = _dir(root) / "index.md"
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def verify(root):
    """Problems: an active artifact edited or missing, an approval missing from the ledger, a stale index."""
    root, bad = Path(root), []
    led = Path(root) / LEARNED / "ledger.jsonl"
    approvals = {}
    for ln in (led.read_text(encoding="utf-8").splitlines() if led.exists() else []):
        r = json.loads(ln)
        if r["action"] == "approved":
            approvals[r["id"]] = r
    for e in _load_entries(root).values():
        if e["status"] != "active":
            continue
        art, p = e["artifact"], root / e["artifact"]["path"]
        if e["id"] not in approvals:
            bad.append(f"{e['id']}: active but no approval in the ledger")
        elif approvals[e["id"]]["artifact"]["sha256"] != art["sha256"]:
            bad.append(f"{e['id']}: entry differs from the approved artifact hash")
        if not p.exists():
            bad.append(f"{e['id']}: {art['path']} is missing")
        elif e["kind"] == "skill" and sha(p.read_text(encoding="utf-8")) != art["sha256"]:
            bad.append(f"{e['id']}: {art['path']} was edited after approval")
        elif e["kind"] == "note":
            want = f"- [{e['id']}] ({e['created'][:10]}; {e['issue']}) {e['body']}\n"
            if want not in p.read_text(encoding="utf-8"):
                bad.append(f"{e['id']}: its line in {art['path']} was edited or removed after approval")
    idx = Path(root) / LEARNED / "index.md"
    if idx.exists() or approvals:
        before = idx.read_text(encoding="utf-8") if idx.exists() else ""
        if before != write_index(root).read_text(encoding="utf-8"):
            bad.append("index.md was stale; regenerated")
    return bad


def _read_body(path):
    return sys.stdin.read() if path == "-" else Path(path).read_text(encoding="utf-8")


def show(e):
    return (f"{e['id']}  [{e['status']}]  {e['kind']} -> {e['target']}\n  title: {e['title']}\n  issue: {e['issue']}  evidence: {', '.join(e['evidence'])}\n"
            f"  --- body ---\n{e['body']}\n  ---")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["collect", "propose", "list", "show", "edit", "approve", "reject", "retire", "index", "verify"])
    ap.add_argument("id", nargs="?")
    ap.add_argument("--root", default=".")
    ap.add_argument("--issue")
    ap.add_argument("--kind")
    ap.add_argument("--target")
    ap.add_argument("--title")
    ap.add_argument("--evidence", default="")
    ap.add_argument("--body-file")
    ap.add_argument("--status")
    ap.add_argument("--by", default="")
    ap.add_argument("--reason", default="")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "collect":
            p, b = collect(a.root, a.id)
            print(f"{p}: {len(b['items'])} evidence items, {sum(1 for i in b['items'] if i['kind'] == 'flag')} owner flag(s)")
        elif a.cmd == "propose":
            e = propose(a.root, a.issue, a.kind, a.target, a.title, [x for x in a.evidence.split(",") if x], _read_body(a.body_file))
            print(f"proposed {e['id']}")
        elif a.cmd == "list":
            for e in _load_entries(a.root).values():
                if not a.status or e["status"] == a.status:
                    print(f"{e['id']}  [{e['status']}]  {e['kind']} -> {e['target']}: {e['title']}")
        elif a.cmd == "show":
            print(show(_load_entries(a.root)[a.id]))
        elif a.cmd == "edit":
            print(f"edited {edit(a.root, a.id, _read_body(a.body_file))['id']}")
        elif a.cmd == "approve":
            print(f"approved {approve(a.root, a.id, a.by)['id']}")
        elif a.cmd == "reject":
            print(f"rejected {reject(a.root, a.id, a.by, a.reason)['id']}")
        elif a.cmd == "retire":
            print(f"retired {retire(a.root, a.id, a.by, a.reason)['id']}")
        elif a.cmd == "index":
            print(write_index(a.root))
        else:
            bad = verify(a.root)
            print("\n".join(bad) if bad else "library matches the ledger")
            return 1 if bad else 0
    except (ValueError, KeyError) as exc:
        print(f"refused: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
