---
name: setup-modelica-skills
description: One-time setup of a Modelica library repo for these skills: simulation engine (CLI/Docker or MCP server), where tasks, issues, references, and library overlays live.
disable-model-invocation: true
---

Look in the repo first (`AGENTS.md`, `package.mo`, `scripts/*.mos`, `docs/`, `refs/`, `Tests/`). Then ask one question at a time, with a recommended answer.

1. **Engine.** Which runner executes Modelica for this repo (local `omc`, Docker container `docker exec <container> omc`, Dymola, or an MCP server)? Map it to the four **engine** contract actions in `.modelica-skills/config.yml`: `load_library`, `check_model` (including `--unitChecking` and `buildModel`/`translateModel`), `simulate`, `read_results`. Verify which external libraries (e.g. `Modelica`) must be preloaded. For Dymola set `engine.backend: dymola` and `engine.dymola` (install path, `package.mo` files, base directory); the gate runner then drives the bundled `dymola` server. No engine: **static-only mode** (nothing can be called `"has been verified"`).
2. **Versions.** Modelica language, Modelica Standard Library, external libraries, the target library, and the engine version.
3. **Tasks.** GitHub, GitLab, or files in `docs/tasks/`.
4. **Folders.** Issues `docs/issues/`, records `records/`, references `refs/` (`refs/refs.bib`, `refs/transcriptions/`, and git-ignored `refs/pdf/`), and **library overlay** `.modelica-skills/learned/` (lessons and skills for this library, proposed by `learn-from-issue` after each issue and installed only after the person approves them; git-ignored in the public skills repo, tracked in the target library repo; approved library skills go to `.claude/skills/`).
5. **Domain & conventions.** Which physical domain(s) (electrical, mechanical, control, thermal, fluid) and **reference state** / ground conventions are used (`// reference-state: <id>`).
6. **Record owner.** Supplier, confidentiality, and a reverse-domain classification name (`org.<owner>.modelica-skills.credibility`) for the SRMD **credibility record**.
7. **Ids.** Keep the `ids` formats of the template (`[ISSUE-001][T-005] <title>`, label `issue-001`) unless the repo has its own.
8. **Tolerances.** Offer defaults (`G3_energy_balance_rel`, `G4_ideal_rel`, `G6a_reference_rel`); each issue sets its own.

Write `.modelica-skills/config.yml` from `templates/config.yml`, add `refs/pdf/` to `.gitignore`, create the required folders (`.modelica-skills/learned/`), and call `engine_status` and `run_gates` (`engine=omc`) on the `modelica` MCP server bundled with the plugin and confirm they run cleanly; map its tools in `engine.tools` (`check`: `check_model`, `simulate`: `simulate`, `results`: `simulate`). Show the result and what is still unresolved.
