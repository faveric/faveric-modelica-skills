# 0018. An issue-end learner with approval replaces the Harness² evaluator

- **Status**: Accepted
- **Date**: 2026-10-29
- **Supersedes**: the Harness² evaluator and the `experience.json` read of ADR-0013, and the lessons bullet of ADR-0017. Keeps ADR-0013's two streams.

## Context
`evals/harness2.py` was run by hand, carried three constant "reflections", read an `experience.json` that nothing wrote, and its target-library path raised `TypeError` on every real project. Nothing in the first real use of the workflow produced a lesson. Research on learning loops (notes kept outside the repository) found: Harness² improves an agent harness by re-running the same task with variants, which session logs do not provide and which is heavy for the goal here; Hermes Agent learns by a counter-triggered background review of the conversation, with no test before adoption and approval off by default; skills the model writes from its own knowledge scored 21.0% against 24.3% with no skills and 40.6% with curated skills (SkillsBench, arXiv 2602.12670, preprint).

## Decision
- **Remove `evals/harness2.py`.** Its line budget (120) and domain-agnostic invariant terms move to `tools/lint_skills.py`.
- **A learner runs once per issue, not per task,** after `docs/issues/<id>-conclusion.md` exists (`tools/mllearn.py collect` refuses otherwise). `review-model` hands over to the model-invoked skill `learn-from-issue`, which runs in a subagent with a clean context, as the Hermes review runs in a fork.
- **It only proposes.** At most three candidates per issue; the default answer is "no entry". A candidate is a `note` (one paragraph for a base skill), a `skill` (a new library skill, at most 120 lines, front matter `name` and `description` only) or a `proposal` (a universal lesson in generic words, for a human to carry to this repository).
- **Evidence is deterministic.** The bundle holds the conclusion, the issue's commits, accepted gaps and owner flags (asserts removed or rewritten, tolerances changed or loosened, found in the diffs of the issue's commits). A candidate must cite bundle items; a flag cannot be cited. Text matching refuses candidates that tell the agent to loosen a tolerance, remove a guard, skip or accept a gate, edit the record, contain a URL, or read as overriding instructions. This is best effort, not a sandbox.
- **A person approves before anything enters the library** (`approve-lessons`, user-invoked): approve, edit or reject each candidate. Approved notes go to `.modelica-skills/learned/<skill>.md`, approved skills to `.claude/skills/<name>/SKILL.md` of the library, and a generated `index.md` lists them. Nothing is overwritten or deleted: a retired skill moves to `learned/archive/`. Every step is an append-only ledger line with who, when and the artifact hash; `mllearn.py verify` finds an artifact edited after approval.
- **Stream A is never written by the learner.** A proposal is checked against the library's package names and `learning.deny_terms`, and a person opens the pull request.

## Consequences
- Approval stands in for a recurrence threshold and for replay of the agent. If lessons turn out to be noisy, add recurrence across issues before adding replay.
- The rule that only `approve-lessons` calls `approve` is a workflow rule visible in the ledger, not an enforced permission. Hooks, a background run outside the session and a path-fenced writer are not used; they can be added later.
- The learner is as good as the evidence of one issue. Library facts are not scanned deterministically yet (a generated map of the library is a possible next step).
- Not decided here: an entry-point skill that guides a whole session through interview, issue, tasks, implement, review and learning.
