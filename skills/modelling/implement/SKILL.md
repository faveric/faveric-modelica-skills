---
name: implement
description: Build a task: write the failing check first, then the smallest model change that passes it, citing sources, updating the record once and closing the task with a short conclusion.
disable-model-invocation: true
---

Read the issue, the task, `GLOSSARY.md`, the config, and `.modelica-skills/learned/index.md` and the notes of this skill there (if present; open a library skill or note only when its cue matches the work). Use `model-design` for structure.

**Open the report with the task's physical question** (its "Physical question" section; ask the owner if it is missing). Gate output is read against that question, never instead of it.

For each task:

1. **Check first.** Write the regression/comparison case (covering nominal operation, conservation balances, and **bidirectional causality** or limit regimes) and run the checks the task names (`verify-physics`). They must fail first, and for the right reason.
2. **Smallest change that passes.** When a constitutive relation, empirical closure, or constant appears, use `cite-source` first.
3. **Verify compilation and simulation, not just `checkModel`.** Run `checkModel`, `buildModel`/`simulate` (`translateModel` in Dymola), and unit checking via the configured **engine**. If `checkModel` reports balanced equations (`N == N`) while `buildModel` or `simulate` fails (`clockPartitioning`, `Pantelides`, initialization failure), use `diagnosing-simulation` to resolve the **structural singularity** or boundary causality defect.
4. **Run the gates without writing** (`run_gates`, engine from the config; CLI: `python3 evals/run_gates.py <project> --engine auto --question "<physical question>"`). The output is a one-page summary; read raw lines only for a failure (`--raw`). Fix the cause of any failure.
   - Never loosen a tolerance. Never remove or loosen a model guard (assert, range check, saturation) to make a gate pass: ask the owner.
   - Going without a gate is the owner's decision, written in the issue as `accepted_gaps` (gate, owner, reason; level L0). You may propose it, never write it.
5. **Update the record once, at the end of the task**: `run_gates` with `write=true` (CLI `--write`), then `credibility-record`. Re-read your diff once: units on every `Real`, divisions or removable singularities that can reach zero, symmetric handling of through-flow reversal at ports, numbers without a source.
6. **Commit** with the passed checks in the message.
7. **Close the task with a comment of 3 to 5 lines**: what was done; result of the named checks; deviations accepted, with who decided; commit hash. If this was the last task of the issue, suggest `/review-model`, which writes the conclusion.

Without an engine, run in **static-only mode** and mark engine gates `skip`. An engine result already in the record for unchanged files stays and is reported as kept, not recomputed; never delete it and never present it as rerun. Never use a number from memory: unread source means `TO-VERIFY` and `pending`.

Finish with the summary: **passed / failed / skipped / needs a human decision**, one line of cause each, the record status; suggest `/review-model`. No raw gate output in the report.
