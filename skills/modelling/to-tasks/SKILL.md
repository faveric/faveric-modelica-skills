---
name: to-tasks
description: Split an issue into vertical slices, each adding one behaviour to the model as a complete mini-issue (problem, model, run, compare, answer) that one agent can open and close alone.
disable-model-invocation: true
---

1. **A task is a vertical slice**: one behaviour added to the model, taken through the whole workflow (define, model, simulate, compare, conclude) with its own comparison case. An agent that has not seen the issue must be able to do it from the task file alone.
2. **Split by behaviour, in progression.** The first slice is the thinnest working model (simple physics, enough to check feasibility). Each later slice extends the same model with one more behaviour (a correlation, a phase change, ice formation, flow reversal) and stays runnable. Example: tank with water, then simple two-phase, then HNE-DS exit flow.
3. **Every slice has its own comparison** (data, exact answer, limit case, ideal bound). A candidate that has none, or cannot run on its own, is not a slice: merge it into its neighbour.
4. **Never split by phase** ("write the model", "run it", "write the conclusion").
5. **No fixed cap, but the plan is agreed first.** Before creating any task, present the progression to the person: for each slice the behaviour added, its physical question and its comparison, in order. Create tasks only after they agree or adjust it.
6. `blocked_by` only when a slice needs another's **result**; a slice that extends the previous one is `builds_on` it. Never block for ordering. No cycles.
7. Mark slices that need a person (`--human`): leaving a source's valid range, loosening a tolerance, fluid choices.
8. Skip anything the issue lists as out of scope.

**Create each task from the issue**, never by hand: `python3 tools/mlissue.py task <issue> <T-id> "<title>" [--builds-on <T-id>] [--human] --write` copies the header slice (model files, conditions, envelope, tolerances, sources, reference) and the five-section body from `templates/task.md`. With `--builds-on` it also sets `builds_on` and `blocked_by` and quotes the previous slice's Answer, credibility included, in the Model section. Then fill the Physical question and leave the other sections empty; the person runs the build later (suggest `/implement`). The title is `[ISSUE-001][T-005] <title>`.

With a GitHub tracker, also add the label from `python3 tools/mlissue.py label <issue>` (create it if missing) and link the task as a sub-issue of the parent (`sub_issue_write` of the GitHub MCP server). Set the GitHub issue type of every task to `Task` (`issue_types.task`), so a sub-issue is never mistaken for a parent Bug or Feature.

**Creating a task releases it**, so create tasks only after the person agrees the plan. A task for an agent gets `type: AFK` and `status: ready-for-agent`; with `--human` it gets `type: HITL` and `status: ready-for-human`, and no agent will pick it up. Suggest `/repo-manager`.

The parent issue keeps Define and Conclude and never builds. Before finishing: every check in the issue appears in some slice, every slice has a physical question and a comparison, no slice is bigger than one working session. Show the order.

Files: see [templates/work-layout.md](../../../templates/work-layout.md).
