---
name: interview-failed-issue
description: Question session for a closed issue whose Outcome is missed: diagnose why from the existing evidence, rank the hypotheses, and end in recover, accept or stop. Writes the failure note, never code.
disable-model-invocation: true
---

Follow the `interviewing` rules. Read-only on the work: write no model code, run no simulation, edit no closed issue. Only the failure note is written.

**Start from the failure, not from zero.** Read `docs/issues/<id>-conclusion.md`, the tasks' Answers (`python3 tools/mlissue.py answers <id>`), the record, the gate results and, for a recovery issue, the earlier attempts (`python3 tools/mlissue.py history <id>`). Facts that need searching go to a subagent; do not ask the person for what the files hold.

Ask in this order:

1. **Benchmark.** Confirm the measured value against the target, the reference and the range, as the conclusion states them. Anything the person remembers differently is a correction to the conclusion, noted in the failure note.
2. **Cause bucket.** Which one, with the evidence: **model** (a neglected effect, a correlation outside its source's validity), **reference** (data uncertainty, mismatched conditions), **target** (was this acceptance justified for this data?), **setup** (boundary conditions, numerics; use `diagnosing-simulation` for solver trouble). Mark it `suspected` or `confirmed`.
3. **Hypotheses.** List them, ranked, cheapest discriminating test first: the test, and what result confirms or rules it out. Number them `H1..`, status `open`. Skip any already `ruled-out` in the history.
4. **Which tests need a new simulation.** Those become the first slice of the recovery issue; do not run them here.
5. **Decision.** Recommend one of three, with the evidence, and ask the person:
   - **recover**: a recovery issue with `follows: <id>` and `baseline`. Suggest `/to-issue`.
   - **accept**: the owner revises the acceptance, or accepts the benchmark. The agent never changes a target; write the ADR with the person and link it.
   - **stop**: record the reason and what is ruled out.

Write `docs/issues/<id>-failure.md` from `templates/failure.md`, at most one page. Never edit the closed issue or its conclusion. Say what you could not check.

Finish by suggesting `/to-issue` (recover) or stating that no new issue is needed, then suggest `learn-from-issue` so the diagnosed cause and any tested negatives become candidates.

Files: see [templates/work-layout.md](../../../templates/work-layout.md).
