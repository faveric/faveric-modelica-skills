# ADR 0016: Separate Dymola MCP server

- **Status**: Accepted
- **Date**: 2026-10-28
- **Amends**: ADR-0015 (the Dymola bullet), SCOPE.md ("Other engines")

## Context
ADR-0015 planned Dymola as a second adapter behind the `modelica` server (same functions as `omc_cli`, selected by `engine.backend`). Dymola is driven differently from `omc`: through its Python interface (`DymolaInterface`), which ships inside the Dymola install and is not on PyPI, on a licence-bound Windows install, with one fresh Dymola process per call.

## Decision
- A second stdio server `dymola` (`server/dymola_mcp.py`), declared in `.mcp.json` next to `modelica`. Tools: `list_available_packages`, `translate_model`, `run_simulation`.
- It uses the same `mcp` SDK as `modelica` (`mcp.server.fastmcp`); no extra dependency. Tool errors are raised as exceptions, which the SDK returns as `isError` results.
- `DymolaInterface` is imported lazily, so the server starts and lists tools on machines without Dymola; engine calls then fail with an explicit message.
- Configuration is by environment variables of the server process: `DYMOLA_PATH`, `DYMOLA_PACKAGES`, `DYMOLA_COMMANDS`, `DYMOLA_BASEDIR`, `DYMOLA_TEMPDIR`.
- Each call starts Dymola, loads the packages in order, works in a unique temporary directory, then closes Dymola and deletes the directory.

## Consequences
- The gate runner (G1, G3-G6) does not use Dymola. The `evals/adapters` contract is still not implemented for Dymola; the ADR-0015 adapter plan stays open.
- `translate_model` and `run_simulation` are not equivalent to `check_model` and `simulate`: no unit checking, no equation-count parsing, final values only (no time series). Do not report gate results from them.
- The location of the Python interface inside the install (`Modelica/Library/python_interface/*.whl|*.egg`) is TO-VERIFY per Dymola version.
- Tests use a fake `DymolaInterface`. Nothing has been run against a real Dymola.
- The server runs Dymola, and the commands in `DYMOLA_COMMANDS`, with the user's rights. Review it like any code you install.
