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

Set `branch` (`<issue-lower>-<slug>`) and `base`: `main` for standalone work, or the id of the issue this one starts from (a spin-off found while building another, or a recovery issue), in which case the branch starts from that issue's latest commit. Then run `python3 tools/mlissue.py summary <issue> --write` (generates the tables from the header; never type them) and `python3 tools/mlissue.py check <issue>`. Fix every FAIL before saving. Copy every WARN into Open items.

Save to the tracker or `docs/issues/<id>.md`. With a GitHub tracker, set the issue type to `Feature` (new model or behaviour) or `Bug` (a recovery issue, or a model known to be wrong); never `Task`, which is reserved for the sub-issues made by `/to-tasks`. If unclear, use `Feature` and list it in Open items. List open items. Suggest `/to-tasks`.

Files: see [templates/work-layout.md](../../../templates/work-layout.md).
