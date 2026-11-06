# 0023. Issue orchestrator, a branch per issue, and one review per issue

- **Status**: Accepted
- **Date**: 2026-11-06

## Context
Launching `/review-model` after every task, and choosing the next command by hand, made a long issue cumbersome. Work had no branch rule, so a defect found in the base model while building a feature had no defined way to be fixed and returned.

## Decision
- **`implement` ends at the task's Answer** and names the next task, or says the issue is complete. No review is launched per task.
- **One agent-run review per issue**, when its last task closes: two fresh reviewer subagents (standards, fidelity) over the issue's diff, then the conclusion, then the learner. Blocking findings reopen only the affected tasks (one commit per task shows which); after two rounds the person decides. `/review-model` stays and does the same by hand.
- **`/issue-orchestrator`** is a new user-invoked skill. It reads `mlstate`, runs one task per subagent (given the skill file's path, not a `/skill` call, because subagents cannot run slash commands and these skills are user-invoked), and stops for the person's decisions. `/startsession` stays a read-only router (ADR-0019 holds).
- **Task status.** `ready-for-agent` releases a task to an agent; `awaiting-approval` hands it to the person. The agent closes a task alone only on clear closure (all named gates passed, credibility `verified`, no unreviewed assumption, nothing loosened or removed, no decision pending); anything else needs approval. A disapproval returns the task with the feedback.
- **One branch per issue**, one commit per task, squash-merged when the issue is done. Header keys `branch`, `base` (`main` or an issue id), `discovered_from` and `paused_for`. An issue found while building another starts from the latest commit of that issue (after a WIP commit) and the parent is paused until the fix concludes `met`; PRs are stacked, the fix's PR targeting the parent's branch.
- **Merge** (agent, with `gh`) only when `mlissue can-merge` passes: conclusion with all sections, Outcome `met`, no task awaiting approval. `missed` never merges.
- **Never delegated**: interviews, the slice plan, accepted gaps, L0 or L1, extrapolation, tolerances, the failure interview, lesson approval, the Outcome.

## Consequences
- `mlstate` gains the stages `approval` and `paused`, `ready`, `awaiting_approval`, `stack`, and a warning for a wrong current branch; `mlissue` validates the new keys and adds `can-merge`.
- A defect in an early slice is found at the end review, after later slices built on it. The closure rule (all gates passed) limits this; it does not remove it.
- Subagent behaviour, `git` and `gh` calls and the review itself are not covered by tests; they are checked by hand on a real project.
