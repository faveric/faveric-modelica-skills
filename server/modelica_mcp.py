#!/usr/bin/env python3
"""MCP server (stdio) exposing the engine contract (ADR-0002, ADR-0015) and the gate runner.

Tools: engine_status, check_model, simulate, run_gates, project_state, check_record.
Engines are chosen by the adapter: OpenModelica (evals/adapters/omc_cli.py) or Dymola (evals/adapters/dymola.py,
which calls the functions of server/dymola_mcp.py in-process; configure engine.dymola in .modelica-skills/config.yml).
All paths are relative to `root` (the Modelica library being worked on), default: the current directory.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.fastmcp import FastMCP  # noqa: E402

from evals import run_gates as gates_runner  # noqa: E402
from evals.adapters import dymola, omc_cli  # noqa: E402
from evals.mlgates import accept, static, summary  # noqa: E402
from evals.mlgates.spec import load_spec  # noqa: E402
from tools import mlrecord, mlstate  # noqa: E402

mcp = FastMCP("modelica-skills")


@mcp.tool()
def engine_status(root: str = ".") -> dict:
    """Report whether a Modelica engine is reachable and which one (engine, version, backend)."""
    backend = gates_runner.resolve_engine(root, "auto") or "omc"
    if backend == "dymola":
        ok = dymola.available(root)
        return {"available": ok, "engine": dymola.engine_info(root) if ok else None, "backend": "dymola",
                "mode": "mcp" if ok else "static-only"}
    ok = omc_cli.available(root)
    return {"available": ok, "engine": omc_cli.engine_info(root) if ok else None, "backend": "omc",
            "mode": "mcp" if ok else "static-only"}


@mcp.tool()
def check_model(files: list[str], model: str | None = None, libraries: list[str] | None = None,
                root: str = ".", build: bool = True, unit_check: bool = True) -> dict:
    """checkModel + buildModel + unit checking. `status` is pass/fail/skip (skip: no engine)."""
    return omc_cli.check_model(files, model=model, libraries=libraries, root=root, build=build, unit_check=unit_check)


@mcp.tool()
def simulate(files: list[str], model: str | None = None, stop_time: float = 1.0,
             overrides: dict[str, float] | None = None, variables: list[str] | None = None,
             libraries: list[str] | None = None, root: str = ".") -> dict:
    """Simulate a model and return the requested result series."""
    return omc_cli.simulate(files, model=model, stop_time=stop_time, overrides=overrides,
                            variables=variables, libraries=libraries, root=root)


@mcp.tool()
def run_gates(root: str = ".", spec: str = "ISSUE.md", record: str | None = None,
              engine: str | None = None, write: bool = False, question: str | None = None) -> dict:
    """Run gates G1-G10 on a project. engine='omc' or 'dymola' enables simulation-backed gates ('auto': engine.backend from
    the config); write=True refreshes the credibility record (`record`, default: the first in records/). A gate that did
    not run is 'skip', never 'pass'. `summary` is the one-page text to quote (passed / failed / skipped / needs a human
    decision); `failed` lists only gates that fail and were not accepted in the issue."""
    res = gates_runner.execute(root, spec, record, engine, write)
    gaps, _ = accept.parse(load_spec(Path(root) / spec))
    stored = static.stored_results(gates_runner._record_path(root, record))
    return {"summary": summary.render(res, gaps, stored, question),
            "gates": {g: {"status": s, "message": m, "accepted": g in gaps} for g, (s, m) in res.items()},
            "failed": accept.blocking(res, gaps)}


@mcp.tool()
def project_state(root: str = ".") -> dict:
    """Where the work stands, derived from the files: per issue the stage (header, tasks, implement, review, learn,
    approve, done), the next command, blockers and warnings, plus stale-record warnings. Read-only."""
    return mlstate.state(root)


@mcp.tool()
def check_record(record: str, root: str = ".") -> list[dict]:
    """Check a credibility record: well-formed, no claim above the evidence, hashes current."""
    return [{"severity": sev, "message": msg} for sev, msg in mlrecord.check(record, root)]


if __name__ == "__main__":
    mcp.run()
