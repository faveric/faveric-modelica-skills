---
name: startsession
description: Entry point for a working session: shows where each issue stands, asks what to do now, and suggests exactly one next command. Changes nothing.
disable-model-invocation: true
---

This is a router, not a driver. It reads the state of the work from the files and says what comes next. The state is derived every time; nothing is stored.

1. **Read the state.** Call `project_state` on the `modelica` MCP server (CLI: `python3 tools/mlstate.py`). It gives, per issue, the stage, the next command, blockers and warnings, and any stale record.
2. **Show it in at most six lines:** configured or not; each issue with its stage and open tasks; blockers; warnings (stale record, stale at-a-glance block); what is waiting for the person (candidates to approve).
3. **Ask one question.** Resume the open work, or start something new: a new model, a change to an existing one, a calibration, or a model that does not run. Ask nothing else yet.
4. **Suggest exactly one next command, with why**, and what to check when it ends:
   - Suggest `/setup-modelica-skills` when there is no config.
   - Suggest `/interview-model` for new work, then `/to-issue` when the interview ends with the level (L0 or L1) and the ranges and sources set, then `/to-tasks` when the issue header parses and its at-a-glance block is current.
   - Suggest `/implement` for the next open task whose blockers are closed, once that task states its physical question.
   - Suggest `/review-model` when every task is closed; it writes the conclusion. Suggest `/approve-lessons` when candidates wait.
   - Suggest `/calibrate` for a calibration. For a model that does not run, use `diagnosing-simulation`. When the conclusion exists and the learner has not run, offer `learn-from-issue`.
5. **List the decisions that stay with the person at this step:** L0 or L1, an accepted gap, an extrapolation beyond a source's range, a tolerance loose against the solver tolerance.

Never create or edit an issue, task, record or config, never run a gate, and never invoke a user-invoked skill: suggest it and stop. If the state tool is unavailable, read `docs/issues/`, the tasks folder and `records/` by hand and say that the state is a reading, not a computation.
