---
name: to-issue
description: Turn the conversation into a model issue whose machine-readable header holds the facts (use, ranges, sources, tolerances, deliverables). Does not interview.
disable-model-invocation: true
---

Do not ask questions. Use what is already in the conversation, the glossary and the notes. Anything missing goes in "Open items", never invented.

Start from `templates/issue.md`. Keep the header keys exactly: the checks read them.

**The header carries the facts; the body does not repeat them.** Fill every header key from the interview: use and decision, acceptance (metric, target, unit, against), boundary and initial conditions, reference state, feasibility, ranges, sources (`TO-VERIFY` until read), tolerances, validation data, fragile spots, deliverables (each tied to the gate that proves it).

The body holds only: the Overview (one paragraph written by a person: what is modelled, the decision, what it must not be used for), Assumptions (one line each, with what it costs), Out of scope, Open items.

**A recovery issue** (from `docs/issues/<id>-failure.md` with decision recover) sets `follows: <id>` and `baseline: {metric, value, target}` from the failed conclusion, reuses its `model_files`, and seeds its Overview and first slice from the failure note's open hypotheses. The generated block then carries the history of every earlier attempt. It starts from the failed work: `base: <failed id>`.

A target is checked for feasibility against the physical limit (for example the isentropic outlet state) before any tolerance is set around it. If it cannot be reached, set `reachable: false` and say so in Open items.

Name the file with `python3 "${CLAUDE_PLUGIN_ROOT}/tools/mlissue.py" new issue "<title>"` (it prints `00001 [ISSUE-001] - <title>.md`). Set `branch` (`<issue-lower>-<slug>`) and `base`: `main` for standalone work, or the id of the issue this one starts from (a spin-off: its parent; a recovery issue: the failed issue), whose `branch` it starts from. **With a GitHub tracker** create the GitHub issue first and pass its number (`new issue ... --number N`), then create the branch with `git switch -c <branch> <base>` and commit the issue file as its first commit. Without GitHub you work one issue at a time: no branch, no spin-off.

**A spin-off** (the build found a defect in the model this issue builds on, and made a `WIP:` commit on the parent's branch): the interrupted task is named in the conversation (ask once if not). Create the new GitHub issue (#N), write its file, add `blocked_by: [#N]` to the interrupted task's header and set "blocked by #N" on its sub-issue, commit both on the parent's branch ("Open #N, block T-x"), then create the new branch from that commit with `base` = the parent's issue id.

Save to the tracker or to the file `mlissue new issue` printed. With a GitHub tracker, set the issue type to `Feature` (new model or behaviour) or `Bug` (a recovery issue, or a model known to be wrong); never `Task`, which is reserved for the sub-issues made by `/to-tasks`. If unclear, use `Feature` and list it in Open items. List open items. Suggest `/to-tasks`.

Files: see [templates/work-layout.md](../../../templates/work-layout.md).
