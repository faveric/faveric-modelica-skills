# Work area: where files go

Files produced while resolving an issue or task (auxiliary data, reports, scripts, engine output) go in the work area, never loose in the repo. Find the folder with `python3 tools/mlwork.py path <ISSUE> [<TASK>] [--sub data|reports|scripts|out]`; it creates it. Root and subfolders come from `work:` in `.modelica-skills/config.yml` (default `.modelica-skills/work/<ISSUE>/[<TASK>/]`). The work area is git-ignored and holds no deliverable.

| Subfolder | Holds |
|---|---|
| `data/` | auxiliary data, extracted or digitised values |
| `reports/` | ad-hoc reports and notes |
| `scripts/` | one-off scripts |
| `out/` | engine output; run the engine with this as its working directory unless `work.engine_cwd` or the person's own temp rules say otherwise |

## Promotion: the only way into git

Promote a file only if a committed artefact cites it, it is needed to reproduce a number in the record, or it is a reusable script. Everything else stays here or is deleted.

| Kind | Destination |
|---|---|
| conclusion, failure note | `docs/issues/` |
| credibility record | `records/` |
| reference data and transcriptions | `refs/` |
| reusable script | `scripts/` (library root), with a header in its first 30 lines: `Purpose:`, `Inputs:`, `Outputs:`, `Issue:`, `Run:` |
| regression model of a failed case | the library's test package; no stored results (re-run it) |

- Ad-hoc reports are never committed. Only the conclusion and the record are.
- Committed data is text (csv, json, yaml), under about 1 MB, with its source and licence recorded next to it. Larger or binary data stays in `out/`, with a pointer in the record.

## Cleanup

At issue end print `python3 tools/mlwork.py manifest <ISSUE>` and delete only after the person confirms. Keep the folder while the issue is failed or paused, until its recovery issue closes or the person deletes it. Never delete without asking.

`python3 tools/mlwork.py check` lists untracked files outside the allowed roots (docs, tracker, records, refs, `scripts/`, `tools/`, `.modelica-skills/`, Modelica sources) and scripts without a header. It reports; it never moves or deletes. `/startsession` shows its result.
