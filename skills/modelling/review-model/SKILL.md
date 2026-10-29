---
name: review-model
description: Review a Modelica change in two independent passes (code standards, fidelity to the issue), check that the record does not claim more than the evidence, and conclude the issue when its last task is done, then hand over to the learner.
disable-model-invocation: true
---

Review the changes since a fixed point (task start, commit, or branch base). Run two reviewers in parallel with clean context, then merge.

**Standards.** Input: diff, `model-design`, `GLOSSARY.md`. Units on every `Real`, no magic numbers, one idea per model, clear interfaces, range guards, tests in the right package, names from the glossary, no commented-out equations. Report file, line, rule.

**Fidelity.** Input: diff, issue, task, record, references. Every equation traces to the issue or a source key. Each source's valid range contains the model's range. Every claim in the record is backed by a check result with engine and version. No tolerance loosened and no guard removed to pass a gate. Every `accepted_gaps` entry has an owner and a reason, and the record says "accepted with skipped gates" and does not claim "has been verified". Record matches the files. Nothing in the diff the issue did not ask for.

Merge by severity: **claim is unsupported**, **blocks merge**, **should fix**, **note**. Give evidence and a proposed fix; do not fix. Say what you could not check (for example, anything needing an engine).

**Conclusion (when the last task of an issue is closed).** Write `docs/issues/<id>-conclusion.md` from `templates/conclusion.md`: results, accepted gaps, open items, out of scope. Post it on the parent issue. Closing the issue is blocked until `python3 tools/mlissue.py can-close <id>` passes.

**Learning (after the conclusion).** Once the conclusion exists, run `learn-from-issue` for the issue in a subagent. It only proposes candidates; suggest `/approve-lessons` to the person. Do not capture lessons any other way, and write nothing into the library yourself.
