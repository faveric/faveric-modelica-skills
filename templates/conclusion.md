# <ISSUE-000> conclusion

Written by `review-model` for the parent issue when the last task of the issue closes. `python3 tools/mlissue.py answers <ISSUE-000>` lists the tasks' Answers to build from. `python3 tools/mlissue.py can-close <ISSUE-000>` blocks closing the issue until this file has all six sections, the Answer carries an Outcome line with the measured number, and every task has written its Answer.

## Answer
At most 10 lines. First line: **Outcome: met | missed**, measured <value> vs target <value>, against <reference and range>. Then the decision from the issue; the result in numbers; **credibility: verified | partial | assumed**; whether the model may be used for the decision (at L1, `partial` means usable at L0 only until a person signs it off). A `missed` close is normal and honest; the next step is `/interview-failed-issue`.

## Results
Per check: gate, tolerance, result, engine and version. Status the record allows. One line each. Evidence for the Answer, not the Answer.

## Deviations
Every place the result departs from the issue's intent: the miss, assumptions made, ranges left, tolerances not met, gates not verified. One line each, "agent-recorded, unreviewed". "none" if there are none.

## Hypotheses tested
Recovery issues only (an issue with `follows`). One line per hypothesis from the earlier failure notes that this issue tested, for example `ISSUE-001:H2 ruled-out, evidence: T-003 Answer, swapping the correlation moved the error by 1%`. Status is `open`, `ruled-out` or `confirmed`; the last two must cite the result. "none" otherwise.

## Accepted gaps
Each gate accepted without passing, by the owner: who, date, reason. "none" if there are none.

## Open items
Numbers or sources still `TO-VERIFY`, work not done, what the next owner must decide.

## Out of scope
What the issue excluded, so nobody reads the model as covering it.
