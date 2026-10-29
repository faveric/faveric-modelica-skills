# 0002. Engine-agnostic orchestration over a four-tool contract

Status: accepted

Skills never name an engine. `setup-modelica-skills` records which engine runs the gates (OpenModelica `omc` by default, Dymola optional) and how it is reached (an MCP server or a command). The contract is four operations: `load_library`, `check_model`, `simulate`, `read_results`.

Adapters are out of scope for v1 (see `SCOPE.md`). If no engine is configured, the skills run in **static-only mode** and no model can be called verified.

Why: the same test on two engines can differ (solver, initialisation, library version), so every recorded result carries engine and version. Tying skills to one engine would block use without a licence or in CI.

Open risk: tolerances must be wider than solver tolerance plus engine differences; the issue declares them per comparison.


Update: the contract is reached through an MCP server. The config maps the four actions (`load`, `check`, `simulate`, `results`) to whatever tool names the chosen server exposes, so any server that offers them works. `/setup-modelica-skills` does the mapping.
