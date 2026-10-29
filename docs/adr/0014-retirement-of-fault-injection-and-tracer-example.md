# ADR 0014: Retirement of Fault-Injection Skill and Heat Exchanger Tracer Example

- **Status**: Accepted
- **Date**: 2026-10-28
- **Supersedes / Amends**: ADR-0010 (Fault injection from the first slice), ADR-0011 (First tracer slice: counterflow heat exchanger)

## Context
During the initial bootstrap of `modelica-skills`, ADR-0010 introduced deterministic fault injection (`evals/faults/faults.yml`, `evals/run_faults.py`) and ADR-0011 introduced a heat exchanger model (`examples/counterflow-hx`) as the tracer slice to calibrate static and numeric gates.

When deploying `modelica-skills` into production libraries across varied engineering domains (electrical, mechanical, control, hydraulic), two major problems emerged:
1. **Safety hazard in production libraries**:
   Exposing a user-invocable `fault-injection` skill (`/fault-injection`) in production repos presents a serious hazard: an AI agent or user could invoke it on a real library, modifying files or injecting deliberate faults into production code.
2. **Context pollution across physical domains**:
   Having `examples/counterflow-hx` in the repository dragged heat exchanger physics, thermal resistance formulas, and empirical fluid correlations (Gnielinski, Kays & London) into the LLM context window. When an agent works on an electrical, mechanical, or control library, this domain-specific thermo-fluid context is irrelevant and misleads the agent's attention.

## Decision
1. **Remove `fault-injection` from public skills**:
   Delete `skills/modelling/fault-injection/` from the skill distribution. Skill quality and gate invariants are maintained non-destructively through **Harness²** (ADR-0013) via `evals/harness2.py` and domain-agnostic unit tests.
2. **Retire the domain-specific `examples/counterflow-hx` tracer**:
   Remove the heat exchanger example from the repository root. Tests now use synthetic, domain-agnostic Modelica test fixtures (minimal linear DAEs and first-order systems) directly in `evals/tests/test_gates.py`.
3. **Keep `omc_cli.py` and gates generic**:
   Remove all hardcoded references to heat exchangers from engine adapters and verification runners. `evals/adapters/omc_cli.py` evaluates models generically via `checkModel`, `buildModel`, `--unitChecking`, and simulation outputs configured in `ISSUE.md` or `.modelica-skills/config.yml`.

## Consequences
- The skills distribution is safe to install on any production repository without risk of accidental fault mutation.
- The repository is 100% domain-agnostic and free of heat-transfer context leakage.
- Unit tests run fast (sub-7s) and verify both static gates and OpenModelica engine translation/simulation on minimal DAE fixtures.
