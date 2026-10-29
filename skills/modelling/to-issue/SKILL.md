---
name: to-issue
description: Turn the conversation into a model issue with a machine-readable header (use, ranges, sources, tolerances). Does not interview.
disable-model-invocation: true
---

Do not ask questions. Use what is already in the conversation, the glossary and the notes. Anything missing goes in "open items", never invented.

Start from `templates/issue.md`. Keep the header keys exactly: the checks read them.

Contents: intended use (L0 or L1) and the decision; what is modelled and what is not; numbered equations (derived here, or tagged with a source key); assumptions and what each costs; ranges with units; fluid and reference state; sources with where in the source (`TO-VERIFY` until read), valid ranges, and whether the transcription was checked; how it will be checked (which checks, which reference, which tolerance and why); what data it will be validated against, or none; what is out of scope.

A temperature, pressure or flow **target** is checked for feasibility against the physical limit (for example the isentropic outlet state) before any controller or tolerance is set around it. If the target cannot be reached, say so in "open items" and ask.

Fill the **At a glance** section: one paragraph written by a person, then `python3 tools/mlissue.py summary <issue> --write`, which generates the tables of ranges, checks with tolerances, and sources from the header. Never type those tables by hand.

Before saving, confirm: the header parses, every source's valid range contains the model's range (or an extrapolation note exists), every required check has a tolerance.

Save to the tracker or `docs/issues/<id>.md`. List open items. Suggest `/to-tasks`.
