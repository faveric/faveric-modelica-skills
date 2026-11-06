---
name: repo-manager
description: Keep order across open issues and drive them with one subagent per task, one branch per issue and stacked PRs, stopping where a person must decide.
disable-model-invocation: true
---

You coordinate; you never build, close, review or conclude. Every phase is a subagent told to read and follow a skill file **by path** (a subagent cannot run `/skill`, and these skills are user-invoked); take the skills folder from this skill's base directory. Closure is done inside the build skill the subagent follows: it sets `done` or `awaiting-approval`.

**1. Read the state and order the work.** `project_state` on the `modelica` server (CLI `python3 tools/mlstate.py --json`). Files tracker only: with a GitHub tracker say that task labels are not read yet and stop. Order the open issues: a spin-off before the parent it pauses, a base before what is stacked on it, then by stage. Show at most six lines and the order, and wait for the person to confirm or change it.

**2. One branch per issue** (`branch` and `base` in the header). Check it out before a task; create it from `base` if missing. One commit per task, made by the task subagent. If `mlstate` warns about the current branch, switch first.

**3. Run a released task.** Take the first task in `ready` (agent) whose blockers are closed. Spawn a subagent: "Read `<skills>/implement/SKILL.md` and follow it for task <id> of <issue> on branch <branch>; return the Answer, the task status and any decision you could not take". A `builds_on` chain never runs in parallel; other tasks may only if the person asks and their `model_files` differ. If `ready` is empty, say what waits: `ready_human` tasks (the person's), `awaiting_approval` (the person's), or no released task (suggest `/to-tasks`).

**4. Hand over.** A task returned `awaiting-approval`: show its Answer and stop. Pass the person's answer to a new subagent: "Read `<skills>/implement/SKILL.md` and run approve <task>", or "disapprove <task> with this feedback: ...".

**5. Issue review.** When every task is `done` or `cancelled`: two fresh subagents in parallel, "Read `<skills>/review-model/SKILL.md` and do only the Standards pass" and "only the Fidelity pass", over the diff since the issue's base. For a blocking finding, a subagent reopens the task whose commit introduced it by the `implement` disapproval rule; a task already at `review_round: 2` goes to the person. With no blocking finding, a subagent writes the conclusion (`review-model`, Conclusion), another runs `learn-from-issue`. Suggest `/approve-lessons`. Outcome `missed`: stop and suggest `/interview-failed-issue`.

**6. A broken base found while building.** The subagent stops and returns it. Propose a spin-off issue and wait. On yes: commit the parent's work as `WIP: paused for <new id>`, create the spin-off branch from that commit, and suggest the interview and `/to-issue` to the person (`base: <parent>`, `discovered_from: <parent>`); those decisions are theirs. `mlstate` then shows the parent as paused. When the spin-off concludes `met`, merge its PR into the parent's branch first, then tell the person the parent can resume. When it concludes `missed`, put the choice to the person: (a) proceed on the parent anyway (they record `proceeds_without` with owner and reason), or (b) declare the parent failed: cancel its open tasks (`status: cancelled`), conclude `missed` naming them.

**7. Pull requests**, when `gh` is available: push, open a PR whose base is the issue's `base` branch, squash-merge only when `python3 tools/mlissue.py can-merge <issue>` passes, then pull the target. Merge children before parents and keep a branch while a PR targets it. A recovery issue starts from the failed issue's branch: close the failed PR unmerged, and the recovery PR targets `main`. Without `gh`, give the exact commands. Never merge on `missed`.

**Never delegate to a subagent, or decide yourself:** `/interview-model`, the `/to-tasks` slice plan, accepted gaps, L0 or L1, extrapolating beyond a source's range, loosening a tolerance, the choice in step 6, `/interview-failed-issue`, `/approve-lessons`, the Outcome. A subagent that reaches one stops and returns the question; put it to the person. Do not invoke another user-invoked skill: suggest it.

Files: see [templates/work-layout.md](../../../templates/work-layout.md).
