# ADR 0015: Plugin distribution and bundled MCP server

- **Status**: Accepted
- **Date**: 2026-10-28
- **Amends**: ADR-0002 (engine contract), SCOPE.md ("Engine adapters / MCP servers")

## Context
Skills were installed by copying `skills/` into a target library. Two problems:
1. The skills call `python3 evals/run_gates.py`, a path that exists in this repo, not in the library where the skills run. A copy install therefore carries the skills but not the gates, the engine adapter or the record checker.
2. ADR-0002 left the MCP server out of scope, so every user had to supply one.

## Decision
- The repo is a Claude Code plugin (`modelica-skills`) and its own single-plugin marketplace (`faveric-modelica-skills`): `claude plugin marketplace add faveric/faveric-modelica-skills`, then `claude plugin install modelica-skills@faveric-modelica-skills`. `claude-plugins-official` is a reserved name, so listing there means submitting to Anthropic's directory, not editing this repo.
- `.mcp.json` declares a stdio server `modelica` (`server/modelica_mcp.py`) started with `uv run --with mcp<2 --with pyyaml`. It wraps the existing adapter and gate runner: `engine_status`, `check_model`, `simulate`, `run_gates`, `check_record`. The folder is not called `mcp/` because it would shadow the `mcp` package.
- Skills name the MCP tools first and the CLI as fallback inside this repo.
- Dymola: a second adapter exposing the same functions as `omc_cli` (`available`, `engine_info`, `check_model`, `simulate`, `evaluate_model_gates`), selected by `engine.backend` in the config. Not implemented; tools report `skip` without an engine.

## Consequences
- `uv` becomes a prerequisite for the bundled server. OpenModelica (or a Docker container) is still the user's to install.
- The server runs `omc`/Docker with the user's rights on files under `root`; it ships with the plugin, so review it like any code you install.
- Skills in the plugin are namespaced: `/modelica-skills:implement`.
