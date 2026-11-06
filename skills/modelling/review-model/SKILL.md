---
name: review-model
description: Review a finished issue in two independent passes (code standards, fidelity to the issue), check that the record does not claim more than the evidence, conclude the issue, run the learner and offer a PR.
disable-model-invocation: true
---

Review the whole issue once, when its last task is closed (`/startsession` suggests it then): the changes since a fixed point (the issue's branch base). With a GitHub tracker first align completion: list the issue's sub-issues with `gh`, compare each with its task file (closed but boxes unticked, or open but boxes ticked), show the mismatches and fix them once the person confirms; the boxes are the truth. Run two reviewers in parallel with clean context, then merge. This is a report: the findings go to the person, who decides to rework a task (`/implement` on it with the finding as feedback), accept the gap, or conclude as it is. After any rework, review the whole issue again. Write the conclusion after they say go.

**Standards.** Input: diff, `model-design`, `GLOSSARY.md`. Units on every `Real`, no magic numbers, one idea per model, clear interfaces, range guards, tests in the right package, names from the glossary, no commented-out equations. Report file, line, rule.

**Fidelity.** Input: diff, issue, task, record, references. Every equation traces to the issue or a source key. Each source's valid range contains the model's range. Every claim in the record is backed by a check result with engine and version. No tolerance loosened and no guard removed to pass a gate. Every `accepted_gaps` entry has an owner and a reason, and the record says "accepted with skipped gates" and does not claim "has been verified". Record matches the files. Nothing in the diff the issue did not ask for.

Merge by severity: **claim is unsupported**, **blocks merge**, **should fix**, **note**. Give evidence and a proposed fix; do not fix. Say what you could not check (for example, anything needing an engine).

**Conclusion (when the last task of an issue is closed).** You write for the parent issue, which owns Define and Conclude; the tasks' Answers are your input (`python3 tools/mlissue.py answers <id>`). Write `docs/issues/<id>-conclusion.md` from `templates/conclusion.md`, **Answer first** (at most 10 lines; the first is `Outcome: met | missed`, the measured number against the acceptance target, then the decision, the result in numbers, credibility, fit for the decision), then results, deviations (every departure from the issue's intent), hypotheses tested (recovery issues: the status of earlier hypotheses, each ruled-out or confirmed citing its evidence), accepted gaps (owner decisions only), open items, out of scope. Do not average or restate the Answers: combine them into one answer to the decision, and say where they disagree. Post it on the parent issue. Closing the issue is blocked until `python3 tools/mlissue.py can-close <id>` passes (conclusion with all six sections, every task has an Answer).

**If the Outcome is `missed`**, stop here and suggest `/interview-failed-issue`; the learner waits for the failure note.

**Learning (part of this skill, after the conclusion).** Run `learn-from-issue` for the issue. It only proposes candidates; suggest `/approve-lessons` to the person. Do not capture lessons any other way, and write nothing into the library yourself.

**Pull request.** When the Outcome is `met` and `gh` is available, ask whether to open one. On yes, push the branch and run `gh pr create` with the issue's `base` as base and the conclusion's Answer as body. Never merge: the person does. Not on `missed`. If the base is another issue's branch (this issue was a spin-off), remind the person to close this issue after merging, so the task that waits for it can go on.

Files: see [templates/work-layout.md](../../../templates/work-layout.md).
