---
id: T-000
issue: ISSUE-000
type: AFK                    # AFK = an agent can do it alone; HITL = needs a human decision
builds_on: null              # previous slice this one extends (same component, one more behaviour); set by mlissue.py task --builds-on
status: null                 # null | awaiting-approval: the person decides on this task before it closes. A task is closed when its Done-when boxes are ticked
blocked_by: []               # #N: the number (file name, or GitHub issue) of a task or issue whose RESULT this task consumes, or a spin-off it waits for; never for ordering
title: "[ISSUE-000][T-000] <title>"
---
<!-- Header slice (level, conditions, envelope, tolerances, sources, reference) is copied from the issue by
     `python3 tools/mlissue.py task <issue> <T-id> "<title>" --write`. Do not retype it; do not open the issue to build this. -->

# <one physical question, answered end to end>

## Physical question
One sentence: what must be established, over which ranges, for which decision. Boundary and initial conditions and the reference state are in the header.

## Model
What is written (components, equations in words, sources by key). Check written first, failing for the right reason.

## Run
The case: model name, inputs, stop time, solver, engine and version.

## Compare
Against what (data, exact answer, ideal bound), with which tolerance. Result and deviation.

## Answer
At most 10 lines, written last. First line: **Outcome: met | missed**, measured <value> vs the acceptance target (and, in a recovery issue, vs the baseline). Then the physical answer in numbers; what it was compared with; **credibility: verified | partial | assumed**; each unverified gate and each assumption (agent-recorded, unreviewed); what the result may and may not be used for; commit hash.

## Done when
- [ ] the model ran and a result exists
- [ ] the comparison is made and its deviation is stated
- [ ] the Answer is written, with credibility and gaps
- [ ] record updated once (gate results, hashes, sources)
- [ ] no tolerance changed and no guard removed to pass

## Notes
