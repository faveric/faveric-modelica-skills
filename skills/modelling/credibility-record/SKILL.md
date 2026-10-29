---
name: credibility-record
description: Create and update the record that travels with a model: what it is for, its limits, which checks passed, and what status it may claim. Detects when the record is out of date.
---

The record is an XML file in `records/` (template: `templates/credibility-record.srmd.xml`). The element names in the template are placeholders until checked against the official schema. Check it with the `check_record` MCP tool (CLI: `python3 tools/mlrecord.py check <record> --root <project>`).

**Required fields** (model name, supplier, confidentiality, release) plus: what the model is for, its limits in words, and the two status fields. Statuses use exact strings: "has not been verified" / "has been verified"; "has not been validated" / "has been validated" / "validated with limitations".

**Extra fields** (under your own reverse-domain name from the config): level (L0/L1), issue id, sources with transcription status, each check result with engine, version, date and file hash, covered files with hashes, tolerances, and "solution-verification: done: ..." at L1.

**Where free text goes.** A gate entry is `<status>; engine=..; date=..; hash=..` and the status is exactly `pass`, `fail`, `open` or `skip`. There is no `partial`: say what was and was not established in a `note.<key>` entry (for example `note.G3`) and set the gate to `open` or `skip`. A gate the owner decided to go without is an `accepted_gaps` entry in the issue; `run_gates --write` then adds `accepted-gap` entries and `acceptance: accepted with skipped gates: ...`, and the status cannot be "has been verified".

**Rules**
- The status never exceeds the check results in the same record.
- Results are written by `run_gates` with `write=true` (CLI: `python3 evals/run_gates.py <project> --write`), which also records file hashes. Do not edit hashes or results by hand; the checker recomputes the checks and rejects mismatches.
- If any covered file changed since the results, the record is out of date: reset the status to "not verified" and re-run.
- A result from another engine or version is a different result.

Create the record with the first task, update it after every run, and raise a status only when `verify-physics` allows it.
