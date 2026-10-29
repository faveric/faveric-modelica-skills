---
name: to-tasks
description: Split an issue into small tasks that each deliver something you can run end to end, with the checks that must pass and what blocks what.
disable-model-invocation: true
---

1. **Task 1 is the thinnest working model**: one equation, one range guard, one comparison case, a record. Everything else depends on it.
2. Each later task is one component or correlation, with its source work and record update inside it. No "update the record" tasks.
3. Every task lists the checks that must pass (ids from `verify-physics`) and their tolerances. No check, no task.
4. State what blocks what; no cycles.
5. Mark tasks that need a person: leaving a source's valid range, loose tolerances, fluid choices.
6. Skip anything the issue lists as out of scope.
7. Every task states its **physical question** in one sentence (template field).
8. **Split earlier than feels necessary.** If a task needs engine runs the environment may cut short, or more than one working session, make it two.

Use `templates/task.md`; write to the tracker or `docs/tasks/NNN-slug.md`.

**Names and links.** Id formats are defined once in `ids` of `.modelica-skills/config.yml`. Every task is titled `[ISSUE-001][T-005] <title>` (`python3 tools/mlissue.py title <issue> <task> "<title>"`). With a GitHub tracker, also: add the label from `python3 tools/mlissue.py label <issue>` (create it if missing), and link the task as a sub-issue of the parent issue (`sub_issue_write` of the GitHub MCP server). Before finishing: every check in the issue appears in some task, task 1 has no blockers, none is bigger than one working session. Show the order and suggest `/implement`.
