#!/usr/bin/env python3
"""MCP server (stdio) driving Dymola through its Python interface (ADR-0016).

Tools: list_available_packages, translate_model, run_simulation.
Dymola is started fresh and closed after every tool call.

Environment variables:
  DYMOLA_PATH      Dymola installation directory, e.g. C:\\Program Files\\Dymola 2026x
  DYMOLA_PACKAGES  Semicolon-separated absolute package.mo paths loaded before every call.
                   Tools accept an explicit `packages` list to override it.
  DYMOLA_COMMANDS  Pipe-separated Dymola commands run after cd() (commands may contain semicolons).
  DYMOLA_BASEDIR   Base directory for relative package paths.
  DYMOLA_TEMPDIR   Parent directory for per-call working directories.
"""
import glob
import logging
import os
import shutil
import sys
import tempfile
import threading
from datetime import datetime
from typing import Annotated

from mcp.server.fastmcp import FastMCP

# STDIO servers must never write to stdout.
logging.basicConfig(stream=sys.stderr, level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("dymola_mcp")


def _env_list(name: str, separator: str) -> list[str]:
    return [i.strip() for i in os.environ.get(name, "").split(separator) if i.strip()]


_DEFAULT_DYMOLA_PATH = os.environ.get("DYMOLA_PATH", "")
_DEFAULT_BASEDIR = os.environ.get("DYMOLA_BASEDIR", "")
_SIM_TEMPDIR_BASE = os.environ.get("DYMOLA_TEMPDIR") or os.path.join(tempfile.gettempdir(), "dymola_mcp_sim")
_DEFAULT_PACKAGES = _env_list("DYMOLA_PACKAGES", ";")
_DEFAULT_COMMANDS = _env_list("DYMOLA_COMMANDS", "|")

mcp = FastMCP(
    "dymola",
    instructions=(
        "Simulate Modelica models in Dymola. A default package set from DYMOLA_PACKAGES is loaded before "
        "every call; pass `packages` only to override it. Call list_available_packages(basedir) to find paths."
    ),
)


def _find_dymola_exe(dymola_path: str) -> str | None:
    for subdir in ("bin64", "bin"):
        exe = os.path.join(dymola_path, subdir, "Dymola.exe")
        if os.path.isfile(exe):
            return exe
    return None


def _add_python_interface(dymola_path: str) -> None:
    """Put Dymola's bundled Python interface on sys.path (it is not on PyPI). Location: TO-VERIFY per Dymola version."""
    pydir = os.path.join(dymola_path, "Modelica", "Library", "python_interface")
    for pattern in ("*.whl", "*.egg"):
        for pkg in sorted(glob.glob(os.path.join(pydir, pattern))):
            if pkg not in sys.path:
                sys.path.insert(0, pkg)


def interface_importable(dymola_path: str | None = None) -> bool:
    """True when Dymola's Python interface can be imported; starts nothing."""
    path = dymola_path or _DEFAULT_DYMOLA_PATH
    if path:
        _add_python_interface(path)
    try:
        import dymola.dymola_interface  # type: ignore  # noqa: F401
        return True
    except ImportError:
        return False


def _engine_version(dymola) -> str | None:
    """Dymola's version string, for the credibility record. DymolaVersion() as a method of the interface: TO-VERIFY."""
    try:
        return str(dymola.DymolaVersion())
    except Exception as exc:
        logger.warning("Dymola version not available: %s", exc)
        return None


def _trajectory_stats(dymola, workdir: str, names: list[str]) -> dict:
    """Min and max over time of each name in the result file. readTrajectorySize/readTrajectory: TO-VERIFY against a real Dymola."""
    result_file = os.path.join(workdir, "DymolaSimResult.mat").replace("\\", "/")
    rows = dymola.readTrajectorySize(result_file)
    columns = dymola.readTrajectory(result_file, list(names), rows)
    return {n: {"min": min(col), "max": max(col)} for n, col in zip(names, columns)}


def _open_dymola(dymola_path: str | None):
    path = dymola_path or _DEFAULT_DYMOLA_PATH
    if path:
        _add_python_interface(path)
    try:
        from dymola.dymola_interface import DymolaInterface  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "Dymola Python interface not importable. Set DYMOLA_PATH to the Dymola install directory "
            "(it must contain Modelica/Library/python_interface) or install the interface in this environment."
        ) from exc
    exe = _find_dymola_exe(path) if path else None
    if exe:
        logger.info("Starting Dymola from: %s", exe)
        return DymolaInterface(dymolapath=exe)
    logger.info("Dymola.exe not found under %r; using DymolaInterface default detection", path)
    return DymolaInterface()


def _load_packages(dymola, packages: list[str], basedir: str) -> list[tuple[str, bool]]:
    """openModel every package in order. Relative paths resolve against basedir."""
    base = basedir.rstrip("/").rstrip("\\")
    results = []
    for pkg in packages:
        full = pkg.replace("\\", "/") if os.path.isabs(pkg) else base + "/" + pkg
        try:
            ok = bool(dymola.openModel(full))
        except Exception as exc:
            logger.error("openModel(%s) raised: %s", full, exc)
            ok = False
        logger.info("openModel(%s) -> %s", full, "OK" if ok else "FAIL")
        results.append((pkg, ok))
    return results


def _configure_dymola(dymola, workdir: str) -> None:
    os.makedirs(workdir, exist_ok=True)
    dymola.cd(workdir)
    for cmd in _DEFAULT_COMMANDS:
        logger.info("ExecuteCommand: %s", cmd)
        dymola.ExecuteCommand(cmd)


def _make_workdir() -> str:
    tag = f"{datetime.now():%Y%m%d_%H%M%S_%f}_pid{os.getpid()}_t{threading.get_ident()}"
    path = os.path.join(_SIM_TEMPDIR_BASE, tag).replace("\\", "/")
    os.makedirs(path, exist_ok=True)
    return path


def _close_dymola(dymola) -> None:
    try:
        dymola.close()
    except Exception as exc:
        logger.warning("Error closing Dymola: %s", exc)


def _resolve_packages(packages: list[str] | None) -> list[str]:
    resolved = packages or _DEFAULT_PACKAGES
    if not resolved:
        raise ValueError("No packages: pass `packages` or set DYMOLA_PACKAGES in the server environment.")
    return resolved


@mcp.tool()
def list_available_packages(
    basedir: Annotated[str, "Root directory of the Modelica library tree to scan"],
) -> list[str]:
    """Scan basedir recursively for Modelica package.mo files; return paths relative to basedir.
    Does not need Dymola."""
    if not os.path.isdir(basedir):
        raise ValueError(f"basedir does not exist or is not a directory: {basedir!r}")
    base = os.path.normpath(basedir)
    found = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        found += [os.path.relpath(os.path.join(root, f), base).replace("\\", "/")
                  for f in files if f.lower() == "package.mo"]
    return sorted(found)


@mcp.tool()
def translate_model(
    model_path: Annotated[str, "Full Modelica path, e.g. 'MyLib.Models.Tank'"],
    packages: Annotated[list[str] | None, "package.mo paths (absolute or relative to basedir); default: DYMOLA_PACKAGES"] = None,
    basedir: Annotated[str, "Root directory for relative package paths"] = _DEFAULT_BASEDIR,
    dymola_path: Annotated[str | None, "Dymola install directory; default: DYMOLA_PATH"] = None,
) -> dict:
    """Translate (compile) a model in Dymola. Returns {success, error, packages_status, engine_version}."""
    resolved = _resolve_packages(packages)
    dymola, workdir = None, _make_workdir()
    try:
        dymola = _open_dymola(dymola_path)
        pkg_results = _load_packages(dymola, resolved, basedir)
        status = [[p, ok] for p, ok in pkg_results]
        failed = [p for p, ok in pkg_results if not ok]
        version = _engine_version(dymola)
        if failed:
            return {"success": False, "error": f"Failed to open packages: {failed}", "packages_status": status,
                    "engine_version": version}
        _configure_dymola(dymola, workdir)
        if dymola.translateModel(model_path):
            return {"success": True, "error": None, "packages_status": status, "engine_version": version}
        return {"success": False, "error": str(dymola.getLastError()), "packages_status": status,
                "engine_version": version}
    finally:
        if dymola is not None:
            _close_dymola(dymola)
        shutil.rmtree(workdir, ignore_errors=True)


@mcp.tool()
def run_simulation(
    model_path: Annotated[str, "Model path with optional modifiers, e.g. 'MyLib.Models.Tank(level(start=0.5))'"],
    output_variables: Annotated[list[str], "Variables whose final values to return, e.g. ['tank.level']"],
    packages: Annotated[list[str] | None, "package.mo paths (absolute or relative to basedir); default: DYMOLA_PACKAGES"] = None,
    initial_names: Annotated[list[str] | None, "Parameters/variables to override at start; same length as initial_values"] = None,
    initial_values: Annotated[list[float] | None, "Values for initial_names"] = None,
    start_time: Annotated[float, "Start time [s]"] = 0.0,
    stop_time: Annotated[float, "Stop time [s]"] = 1.0,
    number_of_intervals: Annotated[int, "Number of output intervals"] = 10,
    with_stats: Annotated[bool, "Also return min and max over time of each output variable under '__stats__'"] = False,
    basedir: Annotated[str, "Root directory for relative package paths"] = _DEFAULT_BASEDIR,
    dymola_path: Annotated[str | None, "Dymola install directory; default: DYMOLA_PATH"] = None,
) -> dict:
    """Simulate a model; return the final value of each output variable.
    `__warning__` carries Dymola's message (and dslog.txt tail) if it flagged failure but still returned values.
    With with_stats, `__stats__` maps each variable to {min, max} over time; `__stats_error__` says why it is absent.
    `__engine_version__` carries Dymola's version when it reports one."""
    resolved = _resolve_packages(packages)
    initial_names, initial_values = initial_names or [], initial_values or []
    if not output_variables:
        raise ValueError("output_variables must be a non-empty list of Modelica variable names.")
    if len(initial_names) != len(initial_values):
        raise ValueError(f"initial_names ({len(initial_names)}) and initial_values ({len(initial_values)}) differ in length.")

    dymola, workdir = None, _make_workdir()
    try:
        dymola = _open_dymola(dymola_path)
        pkg_results = _load_packages(dymola, resolved, basedir)
        failed = [p for p, ok in pkg_results if not ok]
        if failed:
            raise RuntimeError(f"Simulation aborted: failed to open packages: {failed}. Check basedir and package paths.")
        _configure_dymola(dymola, workdir)
        logger.info("simulateExtendedModel(%s) start=%s stop=%s intervals=%d initialNames=%s finalNames=%s",
                    model_path, start_time, stop_time, number_of_intervals, initial_names, output_variables)
        result = dymola.simulateExtendedModel(
            problem=model_path, startTime=start_time, stopTime=stop_time,
            numberOfIntervals=number_of_intervals, resultFile="DymolaSimResult",
            initialNames=initial_names, initialValues=initial_values, finalNames=list(output_variables))
        ok = result[0]
        raw = result[1] if len(result) > 1 and result[1] else []
        values = {v: raw[i] for i, v in enumerate(output_variables) if i < len(raw)}
        if not ok:
            error = str(dymola.getLastError())
            dslog = os.path.join(workdir, "dslog.txt")
            if os.path.isfile(dslog):
                with open(dslog, encoding="utf-8", errors="replace") as f:
                    error += "\n\n=== dslog.txt (last 80 lines) ===\n" + "".join(f.readlines()[-80:])
            if not values:
                raise RuntimeError(f"Simulation failed: {error}")
            values["__warning__"] = error
        elif with_stats:
            try:
                values["__stats__"] = _trajectory_stats(dymola, workdir, list(output_variables))
            except Exception as exc:
                values["__stats_error__"] = f"{type(exc).__name__}: {exc}"
        version = _engine_version(dymola)
        if version:
            values["__engine_version__"] = version
        return values
    finally:
        if dymola is not None:
            _close_dymola(dymola)
        shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    mcp.run()
