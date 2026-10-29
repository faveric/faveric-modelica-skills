---
name: approve-lessons
description: Review the learner's candidates for the library overlay one by one and approve, edit or reject each. Nothing enters the library without this step.
disable-model-invocation: true
---

Only a person approves. Do not approve on your own judgement, and never in the same turn that proposed.

1. `python3 tools/mllearn.py list --status candidate`. None: say so and stop.
2. For each candidate: `python3 tools/mllearn.py show <id>`; read its evidence in `.modelica-skills/learned/evidence/<issue>.json`. Tell the person what it would change: a line added to a base skill's notes, a new library skill, or (proposal) text to carry to the public skills repository.
3. Ask the person, one candidate at a time: **approve**, **edit first**, or **reject** (with a reason). Check also that nothing in it names something private if it is a proposal.
4. Act on the answer: `approve <id> --by "<name>"` (name from `git config user.name`, else ask), `edit <id> --body-file -` then ask again, or `reject <id> --by "<name>" --reason "<why>"`. A proposal is not installed: show its text so the person can open a pull request on the skills repository.
5. `python3 tools/mllearn.py verify`. Report what entered the library, what was rejected, and any mismatch.

A lesson later found wrong is retired, not deleted: `retire <id> --by "<name>" --reason "<why>"`.
