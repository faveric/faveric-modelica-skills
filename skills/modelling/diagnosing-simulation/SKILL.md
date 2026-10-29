---
name: diagnosing-simulation
description: Step-by-step method for models that will not translate, start, or finish, or that run and give wrong results.
---

Do not change tolerances, solvers or start values at random. Read `.modelica-skills/learned/diagnosing-simulation.md` if present for library-specific failure modes.

1. **Reproduce small.** Remove components and set array/discretisation size `N=1` or `N=2` until the smallest model that still fails remains. Note the command, engine and version.
2. **Say which kind of problem it is.**
   - **Will not translate (count mismatch):** count equations and variables per sub-component; find the variable with no equation or the repeated one.
   - **Will not translate despite balanced count (`checkModel` reports `N == N`, but `buildModel` / `simulate` fails with `clockPartitioning`, `Pantelides`, or unassigned variables):** diagnose a **structural singularity**:
     - Two cancelling defects (e.g. an unreferenced constant-folded connector array masking +1 continuous equation in the DAE partition).
     - Over-constrained differential states at a boundary (e.g. coupling multiple differential state equations at a port against a single boundary potential/Lagrange multiplier, such as parallel capacitors or coupled momentum states without an algebraic boundary compliance/resistance). Ensure each independent algebraic constraint on differential states has a matching algebraic boundary unknown, or keep differential states on internal nodes `1..N-1` while coupling boundary ports algebraically.
     - External C function/record arrays failing C code generation: inline external calls or bind scalar fields explicitly.
   - **Will not start:** check start values, `fixed` flags, scaling, and algebraic consistency among initial states; read the initialisation log (`-lv=LOG_INIT`).
   - **Stops or crawls while running:** read the event log (`-lv=LOG_EVENTS`); find the condition that keeps switching (chattering zero-crossings across `f = 0` or state-limit switches); check for divisions or fractional powers near zero.
   - **Runs but wrong:** run the checks in `verify-physics`; compare with the simple limit; check units, sign conventions at ports, ranges, and **bidirectional causality** under sign reversal.
3. **One hypothesis at a time**, with a test at `N=1` or `N=2` that could prove it wrong.
4. **Fix the cause** (boundary causality, index-reduction singularity, missing equation, unguarded division, discontinuity). Loosening a tolerance, adding `noEvent` everywhere or hand-tuning a start value is not a fix.
5. **Keep the failing case** as a regression model with stored results, and add a guard or gate check if one was missing. Re-run all checks (`G1`–`G10`). If the root cause is domain-specific to the target library, record it in the **library overlay** (`.modelica-skills/learned/`); if it is a general Modelica/DAE rule, promote it to the **base skills**.

Report: how to reproduce, kind of problem, cause, fix, the check added, and what is still unexplained.
