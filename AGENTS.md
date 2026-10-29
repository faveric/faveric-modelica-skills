# AGENTS.md

Guidance for working **on this repository** (the skills themselves). For using the skills in a Modelica library, see `README.md`.

## Principles

- Skills are small and composable. If a skill grows past roughly 120 lines, split it or move reference material into a sibling file.
- A skill states **what to do and what it may claim**, never how to feel about it. No filler, no motivational text.
- Domain words come from `GLOSSARY.md`. If you need a new term, add it there first.
- Every non-obvious decision has an ADR in `docs/adr/`. Reverse an ADR with a new ADR, never by editing history.
- Claims about literature go in `docs/literature.md` with a URL. Do not state a page number, equation number or validity range from memory in a skill; use placeholders marked `TO-VERIFY`.

## Skill file rules

- Path: `skills/<category>/<name>/SKILL.md`. Categories: `modelling`, `productivity`.
- Frontmatter: `name` (matches the folder) and `description` (one sentence saying **when** to use it). User-invoked skills also set `disable-model-invocation: true`.
- A user-invoked skill may call model-invoked skills. It must never call another user-invoked skill.
- Shared formats (issue front matter, record entries, gate ids) are defined once, in `templates/` and in `verify-physics`, and referenced from elsewhere.

## Before every commit

1. `python3 tools/lint_skills.py` (frontmatter, names, links, user/model-invoked rule).
2. `python3 -m unittest discover -s evals/tests -t .` (the test suite and gates; needs `pyyaml` and `mcp>=1.2,<2`, otherwise the Dymola tests are skipped).
3. After touching `.claude-plugin/` or `.mcp.json`: `claude plugin validate .` (Stream A base skill verification and line budgets).

## Tuning the skills

Skills are domain-agnostic. Universal improvements are committed to `skills/` (Stream A) by a person, through the checks above; the learner only writes text proposals for them. Library-specific lessons and skills stay in `.modelica-skills/learned/` and `.claude/skills/` of the target library (Stream B), installed only after approval (ADR-0018). `tools/lint_skills.py` keeps the 120-line budget and the domain-agnostic invariant terms. Fault injection and domain-specific examples were retired from public skills to prevent unsafe mutations and context pollution (ADR-0014).

## Known gaps (do not paper over)

- G6b, G7 and the solution-verification sweep are not implemented as gates; at L1 `has been verified` needs a hand-written `solution-verification: done: ...` record entry, which nothing checks beyond its presence.
- A `// cite:` tag counts anywhere in the model files, not next to the code that uses the source.
- The record's gate results are bound to file digests and re-derived on every run (RECORD), but a CI job that runs `evals/run_gates.py` is what enforces it; nothing runs it automatically yet.
- G2 is a static regex check; full dimensional consistency is validated by `omc --unitChecking` via the engine adapter.
- G1 static is a syntax check; full equation balance and structural solvability are validated by `buildModel` via the engine adapter.
- OpenModelica adapter `evals/adapters/omc_cli.py` has been verified end-to-end. The Dymola adapter `evals/adapters/dymola.py` and the Dymola MCP server (`server/dymola_mcp.py`, ADR-0016, ADR-0017) are tested only against a fake `DymolaInterface`, never against a real Dymola; `readTrajectorySize`, `readTrajectory` and `DymolaVersion` are TO-VERIFY.
- Static checks are text matching, not parsers (G1, G2, G5, G8). They report file and line and `skip` when they cannot decide; they can still miss a defect. Two reported false positives (`Real` in records or non-declarations) could not be reproduced without an input and have no test.
- The bundled MCP server (`server/modelica_mcp.py`) is tested for tool listing and engine-free calls only; its OpenModelica-backed calls were not run through MCP. The plugin install was checked with `claude plugin validate` and a local install, not from a published GitHub marketplace.
- The plugin manifest in `.claude-plugin/` is minimal and has not been validated against an installer.
- The SRMD records are well-formed XML and are checked by `tools/mlrecord.py`; they have not been validated against the published XSD or the MIC Core Schematron. The element and namespace names (`Classification`/`Entry`, `urn:placeholder:srmd`) are placeholders: a reviewer recalled `ClassificationEntry` in the SSC namespace, which I could not confirm (the specification text was only partly read). Treat the record format as unconfirmed until it is validated against the real XSD.
