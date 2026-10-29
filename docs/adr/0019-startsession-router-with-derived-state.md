# 0019. `startsession` is a router over derived state

- **Status**: Accepted
- **Date**: 2026-10-29

## Context
The workflow has seven user-invoked skills and, since ADR-0018, a learner and an approval step. A person starting a session has to remember which comes next. The lint rule forbids a user-invoked skill from invoking another one (AGENTS.md); it may only suggest it.

## Decision
- `/startsession` is a user-invoked **router**: it reads the state, asks one question (resume or new work), suggests exactly one next command with the checks for the step, and lists the decisions that stay with the person. It writes nothing.
- The state is **derived from files on every call** by `tools/mlstate.py` (also the MCP tool `project_state`): config present, issues in `docs/issues/`, tasks in the files tracker (a task is closed when its "Done when" boxes are ticked), conclusion, learner evidence and candidates, stale record (G10), stale at-a-glance block. Stage of an issue: header, tasks, implement, review, learn, approve, done. With a tracker other than files, tasks cannot be read and the stage is `tracker`.
- No state file is kept, so it cannot disagree with the files.

## Consequences
- The router never drives the conversation through the steps; each step is a command the person runs. A driver would need an ADR relaxing the lint rule.
- The interview leaves no file, so "interview done" is not derivable: a missing issue means "start with the interview". Fields the issue header does not hold (such as the interview log) are not checked.
- With a non-files tracker the state is less useful; reading task status through the tracker is not implemented.
