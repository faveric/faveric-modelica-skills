# 0017. Accepted gaps per gate, a Dymola adapter for the gates, engine results that stay visible

- **Status**: Accepted
- **Date**: 2026-10-29
- **Amends**: ADR-0005 (gates), ADR-0008 (levels), ADR-0016 (Dymola); `AGENTS.md` known gaps

## Context
The first full use of the workflow (21 tasks, Dymola as the real engine) showed four problems: static gates blocked work on parser limits; a gate result computed in the engine was reported as an error when a later run had no engine; a legitimate owner decision to go without a check could only be expressed by weakening the model or the check; and the gate runner could not use Dymola.

## Decision
- **Severity stays physical.** G5, G8, G10 and the engine gates remain blocking. A static check that cannot decide from text returns `skip` with the reason (for example G5 on an assert that uses `or`, `not` or a boolean constant), never `fail`. Static messages carry file and line and say when they may be false positives. The class header is no longer glued to the first declaration in G2.
- **Accepted gaps, per gate.** The issue header may list `accepted_gaps: [{gate, owner, date, reason}]`. It requires `level: L0`. The gate keeps its raw result; it stops failing the run. G10 and the record check cannot be accepted. The record gets `accepted-gap` entries and `acceptance: accepted with skipped gates: ...`, and cannot claim "has been verified". Only the owner writes the entry; an agent may propose it.
- **No `partial` status.** Gate statuses stay `pass|fail|open|skip`. Free text goes after `;` or in `note.<key>` entries. The checker's message says so.
- **Engine results stay visible.** When a run cannot recompute a gate (`skip`) and the record holds a `pass` or `fail` for the same file hashes, `--write` keeps the stored entry, RECORD does not report a mismatch, and the summary says "record keeps its earlier pass". A changed covered file voids it (G10).
- **Dymola adapter.** `evals/adapters/dymola.py` runs `translate_model` and `run_simulation` of `server/dymola_mcp.py` in-process (configuration `engine.dymola`). G1 comes from translation; G3, G4, G5 and G6a from `verification.simulations`, judged on the min and max over time (`run_simulation(with_stats=True)`); G2 stays a text check because translation returns no unit check. `run_gates --engine auto` takes the backend from the config. No evidence file path is accepted in place of a run.
- **Shorter loop.** `run_gates` prints a one-page summary (passed / failed / skipped / needs a human decision, one cause line each); `--raw` prints everything. The record is written once per task. Every task states its physical question, and closes with a 3 to 5 line comment.
- **Issue hygiene.** Task titles `[ISSUE-001][T-005] <title>` and label `issue-001` come from `ids` in the config. The at-a-glance tables of an issue are generated from its header (`tools/mlissue.py summary`). Closing an issue needs `docs/issues/<id>-conclusion.md` (`mlissue can-close`).
- **Lessons.** Superseded by ADR-0018: lessons are proposed once per issue, after its conclusion, by a learner, and installed only after a person approves them.

## Consequences
- A model with accepted gaps is L0 with a stated shortfall; it cannot be promoted by editing the record.
- The Dymola calls `readTrajectorySize`, `readTrajectory` and `DymolaVersion` are TO-VERIFY against a real Dymola. The adapter is tested only against a fake interface. If the trajectory cannot be read, the affected gates are `skip`, not `pass`.
- Not done, by decision: an `integrate` step that opens a pull request, and a separate `conclude` skill (the conclusion is a section of `review-model`).
