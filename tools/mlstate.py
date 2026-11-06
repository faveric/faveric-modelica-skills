#!/usr/bin/env python3
"""Where is the work? Derives the stage of every issue from the files, so nothing extra is stored and nothing can drift.

  python3 tools/mlstate.py [--root .] [--json]

Stages of an issue, first match wins: header (does not parse), tracker (tasks live elsewhere), tasks (none yet), approval
(a task awaits the person), implement (open tasks; a task can wait for another task or for an issue concluded met), review
(all tasks closed, no conclusion), failure (missed, not diagnosed), approve (candidates waiting), learn (conclusion,
learner not run), done. A task is closed when its "Done when" boxes are all ticked. Each issue also carries its goal (the
header's decision), its opening order and what it waits for ('#N' in a task's blocked_by names the task by its file number). With a tracker other than files the tasks cannot be
read here and the stage is "tracker". The `startsession` skill reads this and suggests the next command; it does not
change anything.
"""
import argparse, json, re, sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from evals.mlgates.spec import load_spec, read_text  # noqa: E402
from tools import mlissue, mlrecord, mlwork  # noqa: E402

PLACEHOLDER = re.compile(r"^(one sentence|<)", re.I)


def _cfg(root):
    p = Path(root) / ".modelica-skills" / "config.yml"
    try:
        return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _front(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text.lstrip("﻿"), flags=re.S)
    if not m:
        return None, text
    try:
        fm = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        return None, text
    return (fm if isinstance(fm, dict) else None), m.group(2)


def _section(body, heading):
    m = re.search(rf"^##\s+{re.escape(heading)}[^\n]*\n(.*?)(?=^##\s|\Z)", body, flags=re.S | re.M)
    return m.group(1).strip() if m else ""


def _closed(boxes):
    """A task is closed when every Done-when box is ticked."""
    return bool(boxes) and all(b.lower() == "x" for b in boxes)


def blocker_text(blocker, tasks_by_number):
    """None when the task a '#N' names is closed, else why it still blocks."""
    m = re.fullmatch(r"#(\d+)", blocker)
    t = tasks_by_number.get(int(m.group(1))) if m else None
    if t is None:
        return f"{blocker} (unknown: no task with that number)"
    return None if t["closed"] else f"{blocker} (open)"


def read_tasks(root, cfg):
    tr = cfg.get("tracker") or {"kind": "files", "path": "docs/tasks"}
    if tr.get("kind", "files") != "files":
        return None, tr.get("kind")
    d = Path(root) / (tr.get("path") or "docs/tasks")
    tasks = []
    for p in sorted(d.glob("*.md")) if d.is_dir() else []:
        fm, body = _front(read_text(p))
        if not fm or "issue" not in fm:
            continue
        boxes = re.findall(r"^\s*-\s*\[([ xX])\]", _section(body, "Done when"), flags=re.M)
        question = _section(body, "Physical question")
        named = mlissue.parse_name(p.name)
        tasks.append({"id": str(fm.get("id") or p.stem), "number": named[0] if named else None, "issue": str(fm["issue"]), "file": p.relative_to(root).as_posix(),
                      "blocked_by": [str(x) for x in fm.get("blocked_by") or []], "status": fm.get("status"),
                      "closed": _closed(boxes),
                      "question": bool(question) and not PLACEHOLDER.match(question)})
    return tasks, None


def next_task(tasks, waits):
    return next((t for t in tasks if not t["closed"] and not waits(t)), None)


def issue_state(root, path, tasks, tracker_kind, entries):
    out = {"file": path.relative_to(root).as_posix(), "id": None, "title": None, "stage": None, "next": None, "why": None,
           "blockers": [], "warnings": [], "waiting": [], "goal": None}
    try:
        spec = load_spec(path)
    except Exception as exc:  # noqa: BLE001 - any parse failure is the same finding
        out.update(id=path.stem, stage="header", next="/to-issue", why=f"the header does not parse: {str(exc)[:80]}")
        return out
    out.update(id=str(spec.get("id") or path.stem), title=spec.get("title"), level=spec.get("level"), goal=spec.get("decision"))
    text = read_text(path)
    if mlissue.BEGIN.split(" (")[0] in text:
        if mlissue._replace(text, mlissue.summary_block(spec, path.parent)) != text:
            out["warnings"].append("the at-a-glance block is stale: run `python3 tools/mlissue.py summary <issue> --write`")
    iid = out["id"]
    if tracker_kind:
        out.update(stage="tracker", next=None, why=f"tasks live in the {tracker_kind} tracker; read them there and suggest the next one")
        return out
    mine = [t for t in tasks if t["issue"] == iid]
    idir = Path(root) / "docs" / "issues"
    unconcluded = mlissue.can_close(iid, str(idir))  # problems found: no conclusion written yet
    if not mine and unconcluded:
        out.update(stage="tasks", next="/to-tasks", why="the issue has no tasks")
        return out
    by_number = {t["number"]: t for t in tasks if t["number"] is not None}
    waits = lambda t: [r for b in t["blocked_by"] if (r := blocker_text(b, by_number))]
    out["awaiting_approval"] = [t["id"] for t in mine if t["status"] == "awaiting-approval" and not t["closed"]]
    out["warnings"] += [f"task {t['id']}: unknown status {t['status']!r} (the only status is {', '.join(mlissue.TASK_STATUS)})"
                        for t in mine if t["status"] and t["status"] not in mlissue.TASK_STATUS]
    out["waiting"] = [f"{t['id']} waits for {r}" for t in mine if not t["closed"] for r in waits(t)]
    if out["awaiting_approval"]:
        out.update(stage="approval", next=None, why=f"task {', '.join(out['awaiting_approval'])} awaits your approval: run `/implement` on it "
                   "and say 'approved' (the agent ticks the boxes) or give feedback")
        return out
    nxt = next_task(mine, waits)
    if nxt:
        out.update(stage="implement", next="/implement", why=f"task {nxt['id']} is the first open task with its blockers closed",
                   task=nxt["id"], open_tasks=sum(1 for t in mine if not t["closed"]), total_tasks=len(mine))
        if not nxt["question"]:
            out["blockers"].append(f"task {nxt['id']} has no physical question (fill the section before building)")
        return out
    if any(not t["closed"] for t in mine):
        unknown = [r for t in mine if not t["closed"] for r in waits(t) if "unknown" in r]
        if unknown:
            out.update(stage="implement", next=None, why="every open task waits, and a blocker names no task: fix blocked_by")
            out["blockers"] += unknown
        else:
            out.update(stage="implement", next=None, why="open tasks exist but each is blocked by another open task: the order has a cycle")
            out["blockers"].append("no task can start")
        return out
    if unconcluded:
        out.update(stage="review", next="/review-model", why="all tasks are closed and there is no conclusion yet")
        return out
    if mlissue.outcome(idir, iid)[0] == "missed" and not (idir / f"{iid}-failure.md").exists():
        out.update(stage="failure", next="/interview-failed-issue", why="the target was missed and the cause is not diagnosed yet")
        return out
    ev = Path(root) / ".modelica-skills" / "learned" / "evidence" / f"{iid}.json"
    waiting = [e for e in entries if e["issue"] == iid and e["status"] == "candidate"]
    if waiting:
        out.update(stage="approve", next="/approve-lessons", why=f"{len(waiting)} candidate(s) wait for a decision")
    elif not ev.exists():
        out.update(stage="learn", next=None, why="the conclusion exists and the learner has not run; ask for the `learn-from-issue` skill on this issue")
    else:
        out.update(stage="done", next=None, why="conclusion written, learner ran, no candidate waiting")
    return out


def state(root="."):
    root = Path(root)
    cfg = _cfg(root)
    out = {"configured": bool(cfg), "issues": [], "record_warnings": [], "work_warnings": [], "next": None}
    if not cfg:
        out["next"] = {"command": "/setup-modelica-skills", "why": "no .modelica-skills/config.yml"}
    tasks, tracker_kind = read_tasks(root, cfg)
    entries = []
    ldir = root / ".modelica-skills" / "learned" / "entries"
    for p in sorted(ldir.glob("*.json")) if ldir.is_dir() else []:
        try:
            entries.append(json.loads(p.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
    idir = root / "docs" / "issues"
    for p in sorted(idir.glob("*.md")) if idir.is_dir() else []:
        if not p.name.endswith(mlissue.SUFFIXES):
            out["issues"].append(issue_state(root, p, tasks or [], tracker_kind, entries))
    for rec in sorted((root / "records").glob("*.srmd.xml")) if (root / "records").is_dir() else []:
        try:
            stale = [m for s, m in mlrecord.check(rec, root) if m.startswith("G10")]
        except Exception as exc:  # noqa: BLE001
            stale = [f"unreadable: {str(exc)[:60]}"]
        if stale:
            out["record_warnings"].append(f"{rec.name}: {stale[0]}")
    if cfg:
        try:
            wc = mlwork.check(root)
            if not wc["configured"]:
                out["work_warnings"].append("config.yml has no `work:` key: re-run /setup-modelica-skills")
            out["work_warnings"] += [f"stray file: {f}" for f in wc["stray"][:10]]
            if len(wc["stray"]) > 10:
                out["work_warnings"].append(f"... and {len(wc['stray']) - 10} more stray files (python3 tools/mlwork.py check)")
            out["work_warnings"] += [f"script without header: {f}" for f, _ in wc["scripts_without_header"]]
        except Exception as exc:  # noqa: BLE001
            out["work_warnings"].append(f"work-area check failed: {str(exc)[:60]}")
    for n, i in enumerate(out["issues"], 1):
        i["opened"] = n  # file names start with the running number, so the file order is the opening order
    if out["next"] is None:
        active = [i for i in out["issues"] if i["stage"] != "done"]
        pick = next((i for i in active if i.get("next")), active[0] if active else None)
        if not out["issues"]:
            out["next"] = {"command": "/interview-model", "why": "no issue yet: start a new piece of work"}
        elif pick and pick.get("next"):
            out["next"] = {"command": pick["next"], "issue": pick["id"], "why": pick["why"]}
        elif pick:
            out["next"] = {"command": None, "issue": pick["id"], "why": pick["why"]}
        else:
            out["next"] = {"command": "/interview-model", "why": "every issue is done: start new work"}
    return out


def render(st):
    lines = [f"configured: {'yes' if st['configured'] else 'no'}", f"issues: {len(st['issues'])}"]
    for i in st["issues"]:
        extra = f" ({i['open_tasks']}/{i['total_tasks']} tasks open)" if "open_tasks" in i else ""
        lines.append(f"  {i['id']}  stage {i['stage']}{extra}  opened {i.get('opened', '?')}: {i['why'] or ''}")
        if i.get("goal"):
            lines.append(f"    goal: {i['goal']}")
        lines += [f"    waits: {w}" for w in i["waiting"]] + [f"    blocker: {b}" for b in i["blockers"]] + [f"    warning: {w}" for w in i["warnings"]]
    lines += [f"record: {w}" for w in st["record_warnings"]] + [f"work: {w}" for w in st["work_warnings"]]
    n = st["next"]
    lines.append(f"next: {n['command'] or '(no command)'}" + (f" for {n['issue']}" if n.get("issue") else "") + f" - {n['why']}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    st = state(a.root)
    print(json.dumps(st, indent=2) if a.json else render(st))
    return 0


if __name__ == "__main__":
    sys.exit(main())
