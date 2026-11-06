---
name: issue-orchestrator
description: Drive open issues through the workflow with one subagent per task, one branch per issue and stacked PRs, stopping where a person must decide.
disable-model-invocation: true
---

You orchestrate; you never build, review or conclude by yourself. Subagents do the work, one task at a time, each given the **path of a skill file** to read and follow (a subagent cannot run `/skill`, and these skills are user-invoked). Take the plugin skills folder from this skill's own base directory.

**1. Read the state.** `project_state` on the `modelica` server (CLI `python3 tools/mlstate.py --json`). With a GitHub tracker also list open issues by type: `Bug` and `Feature` are parents, `Task` are sub-issues. Show at most six lines and say what you will do first.

**2. One branch per issue** (`branch` in the issue header, `<issue-lower>-<slug>`; `base` is `main`, or the issue it was found in). Before a task, check out the branch; create it from `base` if missing. One commit per task, made by the task subagent. If `mlstate` warns about the current branch, switch before going on.

**3. Run a ready task.** Pick the first task of the issue with `status: ready-for-agent` whose blockers are closed (`ready` in the state). Spawn a subagent: "Read `<skills>/implement/SKILL.md` and follow it for task <id> of <issue> on branch <branch>; return the Answer, credibility and any decision you could not take". Tasks in a `builds_on` chain never run in parallel; run others in parallel only if the person asks and their `model_files` differ.

**4. Close or hand over.** On return, close the task yourself only when the closure is clear: every named gate passed (none skipped, partial or assumed), credibility `verified`, no assumption recorded as unreviewed, no tolerance loosened or guard removed, none of the decisions below. Otherwise set `status: awaiting-approval`, show the Answer and stop. On approval close it (clear `status`). On disapproval save the feedback in the task's Notes, set `ready-for-agent` and spawn a fresh subagent.

**5. When the last task closes**, run the review: two fresh subagents in parallel, "Read `<skills>/review-model/SKILL.md` and do only the Standards pass" and "only the Fidelity pass" over the issue's diff since its base. Blocking findings reopen only the affected tasks (one commit per task shows which) as `ready-for-agent` with the findings attached; after two rounds still blocking, ask the person. With none, a subagent writes the conclusion (`review-model`, Conclusion), then `learn-from-issue` in another. Suggest `/approve-lessons`. If the Outcome is `missed`, stop and suggest `/interview-failed-issue`.

**6. Found while building: a broken base.** The subagent stops and returns it. Propose the new issue to the person and wait. On their yes: commit the parent's work as WIP, set `paused_for: <new id>` in the parent, then create the new issue branch from that commit (`base: <parent>`, `discovered_from: <parent>`); suggest the interview and `/to-issue` to the person: those decisions are theirs. When the fix concludes `met`, merge its PR into the parent's branch and resume the parent.

**7. Pull requests**, when `gh` is available: push the branch, open a PR whose base is the issue's `base` branch (stacked), and squash-merge only when `python3 tools/mlissue.py can-merge <issue>` passes (conclusion, Outcome `met`, no task awaiting approval). Then pull the target branch. Without `gh`, give the exact commands. Never merge on `missed`.

**Never delegate to a subagent, or decide yourself:** `/interview-model`, the `/to-tasks` slice plan, accepted gaps, L0 or L1, extrapolating beyond a source's range, loosening a tolerance, `/interview-failed-issue`, `/approve-lessons`, the Outcome. A subagent that reaches one stops and returns the question; you put it to the person. Do not invoke another user-invoked skill: suggest it.

Files: see [templates/work-layout.md](../../../templates/work-layout.md).
