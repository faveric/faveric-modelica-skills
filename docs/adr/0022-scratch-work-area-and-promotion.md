# 0022. Files produced while resolving work go in a git-ignored work area; only promoted files enter the repository

- **Status**: Accepted
- **Date**: 2026-11-05
- **Extends**: ADR-0003 (per-repo setup), ADR-0018 (issue-end learner).

## Context
Agents resolving an issue or task saved auxiliary data, reports and scripts wherever they happened to be working. The target library's repository filled with files nobody could place or trust, and engine runs left generated files in the working directory.

## Decision
- One **work area** per library: `work.root` in `.modelica-skills/config.yml` (default `.modelica-skills/work/<ISSUE>/[<TASK>/]{data,reports,scripts,out}`), git-ignored by `/setup-modelica-skills`. Nothing in it is a deliverable. `tools/mlwork.py path` is the single answer to "where do I save this".
- **Promotion** is the only way into git: a committed artefact cites the file, it is needed to reproduce a number in the record, or it is a reusable script. Fixed destinations: `docs/issues/` (conclusion, failure note), `records/`, `refs/`, `scripts/` (with a header: Purpose, Inputs, Outputs, Issue, Run). Ad-hoc reports are never committed. Committed data is text, about 1 MB at most, with source and licence recorded. A regression model of a failed case goes in the library's test package without stored results; it is re-run.
- **Cleanup**: at issue end the scratch manifest is printed and files are deleted only after the person confirms. A failed or paused issue keeps its folder until the recovery issue closes or the person deletes it. No expiry.
- **Engine** runs use the task's `out/` as working directory unless `work.engine_cwd` or the person's own temp rules or wrapper say otherwise. The bundled adapters already run the engine in a disposable temporary directory and are unchanged; `DYMOLA_TEMPDIR` still overrides the Dymola one.
- **Enforcement** is light: one fixed line in every `SKILL.md` (`tools/lint_skills.py` requires it), `tools/mlwork.py check` (untracked files outside the allowed roots, scripts without header) and a warning in `/startsession`. Tracked files are never judged, so existing libraries do not light up. A stricter CI check is left for a later ADR.

## Consequences
- The rules are defined once, in `templates/work-layout.md`; skills carry only the line that points to it.
- `check` is text and path matching: it reports a file outside the allowed roots even if it is deliberate, and cannot tell a useful script from a useless one.
- Nothing stops an agent from writing outside the work area; the check finds the file afterwards.
