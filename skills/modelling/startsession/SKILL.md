---
name: startsession
description: Entry point for a working session: shows where each issue stands, asks what to do now, and suggests exactly one next command. Changes nothing.
disable-model-invocation: true
---

This is a router, not a driver. It reads the state of the work from the files and says what comes next. The state is derived every time; nothing is stored.

1. **Read the state.** Call `project_state` on the `modelica` MCP server (CLI: `python3 tools/mlstate.py`). It gives, per issue, the stage, the next command, blockers and warnings, and any stale record. With a GitHub tracker the stage is `tracker`: read the open issues with `gh issue list`, their sub-issues and "blocked by" links with `gh api`, and show the same blocks below; a blocker clears when the issue blocking it is closed.
2. **Show the state.** One block per open issue, in opening order: id and title, stage, its goal (the `decision` line), what it waits for (`waiting`: a task blocked by another task or issue, named `#N`; a blocker that names nothing is an error), blockers and warnings. Then: configured or not, a stale record or at-a-glance block, stray files outside the work area, and what waits for the person (candidates to approve, tasks awaiting approval). Keep each issue to three lines.
3. **Ask one question.** Which issue or task to start, or something new: a new model, a change to an existing one, a calibration, or a model that does not run. Ask nothing else yet.
4. **Suggest exactly one next command, with why**, and what to check when it ends:
   - Suggest `/setup-modelica-skills` when there is no config.
   - Suggest `/interview-model` for new work, then `/to-issue` when the interview ends with the level (L0 or L1) and the ranges and sources set, then `/to-tasks` when the issue header parses and its at-a-glance block is current.
   - Suggest `/implement` for the next open task whose blockers are closed, once that task states its physical question.
   - A stage `approval` waits for the person: suggest `/implement` on that task, where they say "approved" or give feedback. A task that waits for another is listed, not started.
   - Suggest `/review-model` when every task is closed; it writes the conclusion and offers a PR. Suggest `/approve-lessons` when candidates wait.
   - Suggest `/interview-failed-issue` when a closed issue's Outcome is `missed` and it has no failure note; then `/to-issue` if the decision is recover.
   - Suggest `/calibrate` for a calibration. For a model that does not run, use `diagnosing-simulation`. When the conclusion exists and the learner has not run, offer `learn-from-issue`.
5. **List the decisions that stay with the person at this step:** L0 or L1, an accepted gap, an extrapolation beyond a source's range, a tolerance loose against the solver tolerance.

Never create or edit an issue, task, record or config, never run a gate, and never invoke a user-invoked skill: suggest it and stop. If the state tool is unavailable, read `docs/issues/`, the tasks folder and `records/` by hand and say that the state is a reading, not a computation.

Files: see [templates/work-layout.md](../../../templates/work-layout.md).
