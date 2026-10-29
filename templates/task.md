---
id: T-000
issue: ISSUE-000
type: AFK                    # AFK = an agent can do it alone; HITL = needs a human decision
blocked_by: []
title: "[ISSUE-000][T-000] <title>"   # id format: `ids` in .modelica-skills/config.yml; helper: tools/mlissue.py title
---

# <vertical slice, one behaviour end to end>

## Physical question
One sentence: what physical fact must this task establish? The report opens with it, and the gate results are read against it.

## Behaviour
What can be observed when this is done (inputs, outputs, envelope part).

## Red first
The check that fails now: gate id, reference, tolerance.

## Done when
- [ ] the red check is green
- [ ] all gates required at the issue level pass or are honestly `open`/`skip`
- [ ] record updated (gate results, hashes, sources)
- [ ] no tolerance changed to pass

## Closing comment (3 to 5 lines, posted on the task when it closes)
What was done; result of the named checks; deviations accepted with the owner's decision (who, why); commit hash.

## Notes
