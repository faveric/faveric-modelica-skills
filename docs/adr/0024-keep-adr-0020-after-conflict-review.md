# 0024. Keep ADR-0020 after the review of the orchestrator proposal

- **Status**: Accepted
- **Date**: 2026-11-06

## Context
ADR-0023 proposed an orchestrator that closed tasks, drove subagents, paused issues and merged pull requests. A code review and a conflict analysis found it contradicted ADR-0020 (gates record credibility and do not block closing; the parent issue is the orchestrator), left states from which the workflow could not move, and was too heavy to use.

## Decision
- **ADR-0020 stands unchanged.** ADR-0023 is superseded (its file stays, with the status changed).
- The workflow stays small: interview, issue, tasks, `implement` per task, one `review-model` per issue. The person runs each step.
- `/startsession` is the overview: open issues with goal, stage, what each waits for and opening order, then one suggested command. It changes nothing.
- A task is closed by its Done-when boxes; the one extra state is `awaiting-approval`, for a task where a decision is left for the person.
- One branch per issue (`branch`, `base`). A spin-off or recovery issue is an ordinary issue; the interrupted task lists it in `blocked_by`.
- `review-model` reports, the person decides, then it writes the conclusion and offers a PR. The person merges.
- The skills and tools are the source of truth for this; ADRs are reference for developing the library. ADR-0019 is not edited: its stage list is older than `tools/mlstate.py`, which gives the current one.
