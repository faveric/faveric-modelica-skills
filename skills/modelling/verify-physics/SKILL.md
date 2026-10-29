---
name: verify-physics
description: Run the model checks G1-G10, decide which status the evidence allows, and write results to the record. Use after any model change and before claiming a status.
---

Tolerances come from the issue. Never loosen one to pass, and never remove or loosen a model guard to pass. Read `.modelica-skills/learned/verify-physics.md` if present for library-specific checks.

| Id | Check |
|---|---|
| G1 | It translates and builds (`checkModel` + `buildModel`/`translateModel`), equation count balances, no **structural singularity** (`clockPartitioning`/`Pantelides`), no ignored warnings |
| G2 | Equations are dimensionally consistent (`omc --unitChecking`); a `Real` without a unit is only a warning (parameters and percentages can be dimensionless) |
| G3 | Conserved quantities (charge, momentum, mass, energy) balance across the operating grid and transients |
| G5 | Range guards exist and use the declared bounds; edge cases (zero through-flow, removable singularities, **bidirectional causality** sign reversal) give finite, sensible values |
| G6a | Results stay within the ideal bound: efficiency < 1, entropy generated > 0 (passive resistor $v \cdot i \ge 0$, damper $f \cdot v \ge 0$), COP below Carnot, and the like. Which bound applies is stated in the issue; `G6a_reference_rel` is the margin for solver and rounding error. Checks that need a library's own definitions go in `.modelica-skills/learned/verify-physics.md` |
| G6b | Matches independent data or a published benchmark, over a stated range |
| G7 | Same as the last accepted results (not yet implemented) |
| G8 | Reference potentials, media, or **reference state** conventions agree across connections |
| G9 | Every **source** is registered, tagged in the code, and its **validity range** contains the model's **envelope** |
| G10 | The record's results were computed on the current files |

**Status rules**
- Default: `"has not been verified"`.
- `"has been verified"` needs G1-G5, G6a, G8, G9, G10 all passing on the engine (`--engine omc` or `dymola`). At L1 also sources `numeric-checked` against published values, and a `solution-verification: done: ...` tolerance/grid sweep entry in the record.
- `"has been validated"` needs G6b over a stated range, on data not used for fitting.
- Balances alone (G3) never earn `"has been verified"`. G6a is a one-sided bound, not a match: a wrong constitutive law that stays inside the ideal limit passes it, so only G6b (data or benchmark) establishes accuracy.
- `checkModel` alone never earns G1: a model with `N == N` equations and variables can still have a **structural singularity** caught only by `buildModel` / `simulate`.
- A check that passed in an engine stays visible when a later run cannot recompute it (no engine in that session): the record keeps it while the files are unchanged, and the report says "kept, not recomputed". It is dropped as soon as a covered file changes.
- A check that did not run is `skip`, not `pass`. A static check that cannot decide from text (for example an assert written with `or`) is `skip` with the reason, not `fail`.
- **Accepted gap.** The owner may go without one gate by listing it in the issue (`accepted_gaps`: gate, owner, date, reason), which requires level L0. The gate keeps its raw result, stops failing the run, and the record reads "accepted with skipped gates". Such a model never claims `"has been verified"`. G10 and the record check cannot be accepted.
- Unread sources are `open` at L0 and `fail` at L1. A claim above the evidence is `fail`.

**Steps**
1. Read the issue header and the **credibility record**.
2. Run the checks through the `modelica` MCP server (`run_gates`, `engine=omc|dymola|auto`, optional `write`); CLI fallback inside the skills repo: `python3 evals/run_gates.py <project> --engine auto [--write]` (`auto` reads `engine.backend` from the config). The default output is the one-page summary; `--raw` prints every gate. Dymola gates come from `evals/adapters/dymola.py`: G1 from translation, G3, G5 and G6a from `verification.simulations`, G2 stays a text check. Without an engine, run in **static-only mode**; G1, G3, G5 (limits), G6a are then `skip`.
3. Write each result with engine, version, date, and file hash (`--write`). Never edit `gate.*`, `mirror.*`, `model.file`, or hashes by hand.
4. Work out the **status** the evidence allows. If the record claims more, correct it and report.
5. On a failure, find the cause (model, issue, or check) before changing anything. Simulation or translation problems go to `diagnosing-simulation`.

A hand-written Python mirror of the equations can be run too. Record its results separately (`mirror.*`): they test the equations and checks, not the Modelica file.
