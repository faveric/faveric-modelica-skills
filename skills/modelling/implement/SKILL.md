---
name: implement
description: Build a task: write the failing check first, then the smallest model change that passes it, citing sources, updating the record once and closing the task with a short conclusion.
disable-model-invocation: true
---

Work from the task file alone (its header carries the conditions, ranges, sources and reference); open the issue only for the decision it informs. Read `GLOSSARY.md`, the config, and `.modelica-skills/learned/index.md` and the notes of this skill there (if present; open a library skill or note only when its cue matches the work). Use `model-design` for structure.

**Open the report with the task's physical question** (its "Physical question" section; ask the owner if it is missing). Gate output is read against that question, never instead of it.

For each task:

1. **Check first.** Write the regression/comparison case (covering nominal operation, conservation balances, and **bidirectional causality** or limit regimes) and run the checks the task names (`verify-physics`). They must fail first, and for the right reason.
2. **Smallest change that passes.** When a constitutive relation, empirical closure, or constant appears, use `cite-source` first.
3. **Verify compilation and simulation, not just `checkModel`.** Run `checkModel`, `buildModel`/`simulate` (`translateModel` in Dymola), and unit checking via the configured **engine**. If `checkModel` reports balanced equations (`N == N`) while `buildModel` or `simulate` fails (`clockPartitioning`, `Pantelides`, initialization failure), use `diagnosing-simulation` to resolve the **structural singularity** or boundary causality defect.
4. **Run the gates without writing** (`run_gates`, engine from the config; CLI: `python3 evals/run_gates.py <project> --engine auto --question "<physical question>"`). The output is a one-page summary; read raw lines only for a failure (`--raw`). Fix the cause of a failure once; if it is still open after one attempt, record it and go on. **Gates record credibility, they do not stop the work** (ADR-0020): a model that ran and was compared still gets its Answer.
   - Never loosen a tolerance. Never remove or loosen a model guard (assert, range check, saturation) to make a gate pass: ask the owner.
   - An unverified gate or an assumption goes in the Answer as "agent-recorded, unreviewed", with the reason. Promoting `partial` to `verified`, or the `accepted_gaps` entry the record reads, is the owner's decision; you may propose it.
5. **Update the record once, at the end of the task**: `run_gates` with `write=true` (CLI `--write`), then `credibility-record`. Re-read your diff once: units on every `Real`, divisions or removable singularities that can reach zero, symmetric handling of through-flow reversal at ports, numbers without a source.
6. **Commit** with the passed checks in the message.
7. **Close the task, here and nowhere else.** Write its Answer (section `## Answer`, at most 10 lines): the physical answer in numbers; what it was compared with and the deviation; credibility (`verified` | `partial` | `assumed`) with each unverified gate and assumption; what it may and may not be used for; commit hash. Post it as the closing comment. **Clear closure** means all of: every named gate passed (none skipped, partial or assumed); credibility `verified`; no assumption recorded as unreviewed; no tolerance loosened and no guard removed; none of the owner decisions pending (L0 or L1, extrapolation, loose tolerance, accepted gap). On clear closure set `status: done` and tick the Done-when boxes. With any doubt set `status: awaiting-approval` and leave the boxes: the person decides. No review is launched per task.

Without an engine, run in **static-only mode** and mark engine gates `skip`. An engine result already in the record for unchanged files stays and is reported as kept, not recomputed; never delete it and never present it as rerun. Never use a number from memory: unread source means `TO-VERIFY` and `pending`.

Finish with the summary: **passed / failed / skipped / needs a human decision**, one line of cause each, the record status, the task status; then the next step: the next released task, or, when this was the last one, "issue complete": suggest `/repo-manager` (it has the review and conclusion run by subagents) or `/review-model`. No raw gate output in the report.

**Approval** (run as `/implement approve <task>` or `/implement disapprove <task> "<feedback>"`; a coordinating agent passes the person's answer the same way). Approve: set `status: done`, tick the Done-when boxes, post the Answer. Disapprove, and a blocking finding from the issue review: write the feedback under `## Notes`, set `status: ready-for-agent`, add 1 to `review_round`, then rework the task from step 1. A task already at `review_round: 2` goes back to the person instead of to an agent.

Files: see [templates/work-layout.md](../../../templates/work-layout.md).
