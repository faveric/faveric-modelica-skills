#!/usr/bin/env python3
"""The work area: where files produced while resolving an issue or task go (ADR-0022, templates/work-layout.md).

  python3 tools/mlwork.py path ISSUE-001 [T-002] [--sub data|reports|scripts|out]   # create the folder, print its path
  python3 tools/mlwork.py manifest ISSUE-001                                        # scratch files with sizes, for the cleanup step
  python3 tools/mlwork.py check [--json]                                            # untracked files outside the allowed roots, scripts without header

Report only: nothing here moves or deletes a file. `check` looks at untracked files (git, honouring .gitignore), never at tracked ones.
"""
import argparse, json, re, subprocess, sys
from pathlib import Path

import yaml

DEFAULT_ROOT = ".modelica-skills/work"
DEFAULT_SUBDIRS = ["data", "reports", "scripts", "out"]
ROOT_FILES = {"readme", "license", "licence", "agents.md", "claude.md", "glossary.md", "scope.md", ".gitignore", ".gitattributes", ".mcp.json"}
FIXED_ROOTS = ["scripts", "tools", ".modelica-skills", ".claude", ".github", "docs/adr"]
SCRIPT_LABELS = ["purpose", "inputs", "outputs", "issue", "run"]


def _cfg(root):
    try:
        return yaml.safe_load((Path(root) / ".modelica-skills" / "config.yml").read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def work_settings(root="."):
    w = _cfg(root).get("work") or {}
    return {"root": w.get("root") or DEFAULT_ROOT, "subdirs": w.get("subdirs") or DEFAULT_SUBDIRS, "engine_cwd": w.get("engine_cwd")}


def path_for(root, issue, task=None, sub=None, create=True):
    s = work_settings(root)
    if sub is not None and sub not in s["subdirs"]:
        raise ValueError(f"unknown subfolder {sub!r}; use one of {s['subdirs']}")
    base = Path(root) / s["root"] / issue / (task or "")
    target = base / sub if sub else base
    if create:
        for d in (s["subdirs"] if not sub else [sub]):
            (base / d).mkdir(parents=True, exist_ok=True)
    return target


def manifest(root, issue):
    base = Path(root) / work_settings(root)["root"] / issue
    return [(p.relative_to(base).as_posix(), p.stat().st_size) for p in sorted(base.rglob("*")) if p.is_file()] if base.is_dir() else []


def allowed_roots(root):
    cfg = _cfg(root)
    docs = cfg.get("docs") or {}
    refs = cfg.get("references") or {}
    tr = (cfg.get("tracker") or {}).get("path") or "docs/tasks"
    roots = list(FIXED_ROOTS) + [work_settings(root)["root"], docs.get("issues", "docs/issues"), docs.get("adr", "docs/adr"),
                                 docs.get("records", "records"), tr]
    roots += [str(Path(v).parts[0]) for v in refs.values() if isinstance(v, str)] or ["refs"]
    return sorted({r.strip("/").replace("\\", "/") for r in roots})


def _git_untracked(root):
    try:
        r = subprocess.run(["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"], capture_output=True, text=True,
                           stdin=subprocess.DEVNULL, encoding="utf-8", errors="replace", timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.splitlines() if r.returncode == 0 else None


def _is_modelica(root, rel):
    if rel.endswith((".mo", ".order")):
        return True
    p = (Path(root) / rel).parent
    root = Path(root).resolve()
    while True:
        if (p / "package.mo").exists():
            return True
        if p.resolve() == root or p.parent == p:
            return False
        p = p.parent


def stray_files(root):
    """Untracked files outside the allowed roots; None when git cannot tell."""
    files = _git_untracked(root)
    if files is None:
        return None
    roots = allowed_roots(root)
    out = []
    for f in files:
        f = f.replace("\\", "/")
        if any(f == r or f.startswith(r + "/") for r in roots):
            continue
        if "/" not in f and (f.lower() in ROOT_FILES or f.lower().split(".")[0] in ROOT_FILES):
            continue
        if _is_modelica(root, f):
            continue
        out.append(f)
    return out


def scripts_missing_header(root):
    d = Path(root) / "scripts"
    bad = []
    for p in sorted(d.rglob("*")) if d.is_dir() else []:
        if not p.is_file() or p.suffix in (".pyc",):
            continue
        try:
            head = "\n".join(p.read_text(encoding="utf-8", errors="replace").splitlines()[:30]).lower()
        except OSError:
            continue
        missing = [lab for lab in SCRIPT_LABELS if not re.search(rf"\b{lab}\s*:", head)]
        if missing:
            bad.append((p.relative_to(root).as_posix(), missing))
    return bad


def check(root="."):
    stray = stray_files(root)
    return {"stray": stray or [], "git": stray is not None, "scripts_without_header": scripts_missing_header(root),
            "configured": "work" in _cfg(root)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", default=".")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("path")
    p.add_argument("issue")
    p.add_argument("task", nargs="?")
    p.add_argument("--sub")
    m = sp.add_parser("manifest")
    m.add_argument("issue")
    c = sp.add_parser("check")
    c.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "path":
        try:
            print(path_for(a.root, a.issue, a.task, a.sub))
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 2
    elif a.cmd == "manifest":
        for rel, size in manifest(a.root, a.issue):
            print(f"{size:>10}  {rel}")
    else:
        r = check(a.root)
        if a.json:
            print(json.dumps(r, indent=2))
        else:
            if not r["git"]:
                print("note: not a git repository (or git unavailable); stray files cannot be listed")
            if not r["configured"]:
                print("note: config.yml has no `work:` key; re-run /setup-modelica-skills")
            for f in r["stray"]:
                print(f"stray: {f}  (move into the work area, or promote it: templates/work-layout.md)")
            for f, miss in r["scripts_without_header"]:
                print(f"script without header: {f}  (missing {', '.join(miss)})")
            if not (r["stray"] or r["scripts_without_header"]):
                print("work area clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
