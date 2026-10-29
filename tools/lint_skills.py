#!/usr/bin/env python3
"""Lint skills: frontmatter, name = directory, description length, user-invoked rule, relative links, README coverage."""
import re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
USER_INVOKED = {"startsession", "setup-modelica-skills", "interview-model", "to-issue", "to-tasks", "implement",
                "review-model", "calibrate", "approve-lessons"}
MODEL_INVOKED = {"verify-physics", "cite-source", "credibility-record", "model-design",
                 "diagnosing-simulation", "interviewing", "learn-from-issue"}
LINE_BUDGET = 120
# Domain-agnostic terms the public skills must keep (moved from the retired evals/harness2.py, ADR-0018).
INVARIANTS = {
    "diagnosing-simulation": ["structural singularity", "clockPartitioning", "Pantelides", "N=1", "bidirectional causality"],
    "model-design": ["bidirectional causality", "structural singularity", "connect(", "--unitChecking"],
    "verify-physics": ["buildModel", "--unitChecking", "structural singularity", "bidirectional causality"],
    "cite-source": ["check_script", "numeric-checked", "validity range", "locator"],
    "implement": ["bidirectional causality", "buildModel", "structural singularity"],
    "setup-modelica-skills": ["load_library", "check_model", "simulate", "read_results", ".modelica-skills/learned/"],
}


def frontmatter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, flags=re.S)
    if not m:
        return None
    d = {}
    for ln in m.group(1).splitlines():
        k, _, v = ln.partition(":")
        d[k.strip()] = v.strip()
    return d


def main():
    errs = []
    skills = sorted(ROOT.glob("skills/*/*/SKILL.md"))
    names = set()
    for p in skills:
        fm = frontmatter(p.read_text(encoding="utf-8"))
        d = p.parent.name
        if fm is None:
            errs.append(f"{p}: no frontmatter"); continue
        if fm.get("name") != d:
            errs.append(f"{p}: name {fm.get('name')!r} != directory {d!r}")
        names.add(d)
        desc = fm.get("description", "")
        if not desc or len(desc) > 300:
            errs.append(f"{p}: description missing or over 300 chars ({len(desc)})")
        uf = fm.get("disable-model-invocation") == "true"
        if d in USER_INVOKED and not uf:
            errs.append(f"{p}: user-invoked skill must set disable-model-invocation: true")
        if d in MODEL_INVOKED and uf:
            errs.append(f"{p}: model-invoked skill must not disable model invocation")
        if d not in USER_INVOKED | MODEL_INVOKED:
            errs.append(f"{p}: skill not classified in tools/lint_skills.py")
    for n in (USER_INVOKED | MODEL_INVOKED) - names:
        errs.append(f"expected skill missing: {n}")
    for p in list(ROOT.glob("*.md")) + list(ROOT.glob("docs/**/*.md")) + list(ROOT.glob("skills/*/*/SKILL.md")) + list(ROOT.glob("templates/*.md")) + list(ROOT.glob("examples/**/*.md")):
        for target in re.findall(r"\]\(([^)#\s]+)\)", p.read_text(encoding="utf-8")):
            if re.match(r"^[a-z]+://", target) or target.startswith("mailto:"):
                continue
            if not (p.parent / target).resolve().exists():
                errs.append(f"{p.relative_to(ROOT)}: broken link {target}")
    for p in skills:
        d = p.parent.name
        if d not in USER_INVOKED:
            continue
        for ln in p.read_text(encoding="utf-8").splitlines():
            if re.search(r"suggest|ask the person|do not invoke", ln, flags=re.I):
                continue
            for other in USER_INVOKED - {d}:
                if re.search(rf"(?:`/?{other}`|/{other}\b)", ln):
                    errs.append(f"{p.relative_to(ROOT)}: user-invoked skill refers to user-invoked '{other}' without 'suggest': {ln.strip()[:70]}")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for n in names:
        if f"skills/modelling/{n}/SKILL.md" not in readme and n != "interviewing":
            errs.append(f"README does not link skill {n}")
    for p in skills:
        n = len(p.read_text(encoding="utf-8").splitlines())
        if n > LINE_BUDGET:
            errs.append(f"{p.relative_to(ROOT)}: {n} lines, over the budget of {LINE_BUDGET}")
    for skill, terms in INVARIANTS.items():
        f = ROOT / "skills" / "modelling" / skill / "SKILL.md"
        text = f.read_text(encoding="utf-8").lower() if f.exists() else ""
        errs += [f"skills/modelling/{skill}/SKILL.md: invariant term {t!r} missing" for t in terms if t.lower() not in text]
    for e in errs:
        print("ERROR:", e)
    print(f"{len(skills)} skills checked, {len(errs)} error(s)")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
