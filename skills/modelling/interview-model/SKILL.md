---
name: interview-model
description: Question session that fixes what a model is for, its physics, ranges and sources before any Modelica is written. Updates the glossary and records decisions.
disable-model-invocation: true
---

Follow the `interviewing` rules. Read `GLOSSARY.md`, `.modelica-skills/config.yml`, existing issues and records first. No config: suggest `/setup-modelica-skills`.

Ask in this order:
1. **Use.** What decision does the model support? L0 (rough comparison) or L1 (design decision). Refuse L2 (see `SCOPE.md`).
2. **Physics.** Equations in words, then symbols. Steady or dynamic. What is neglected and what would make you distrust the result.
3. **Boundary Conditions.** Conditions at the model's edges. They can be:
  (a) Dirichlet (fixed value), (b) Neumann (fixed derivative), or (c) Robin (linear combination). For each: which variable, which value, and what happens outside the range.
4. **Initial Conditions.** For dynamic models, what is the starting state? If it is not known, how will it be found?
5. **Reference state.** What is the reference state? (skip if not relevant) 
Examples: 
- For fluid dynamics what is the reference for zero enthalpy? Make IIR as default.
- For thermodynamic second law, what is the dead state? 
6. **Ranges.** For each variable: min, max, unit, and what happens outside (warn or stop).
7. **Sources.** Where does each correlation or constant come from? Use `cite-source` as soon as one appears. If ranges are outside the source range, ask for an extrapolation ADR and put its id in `extrapolation_adr`.
8. **Feasibility.** For every target the model must reach (an outlet temperature, a superheat, a flow), compute the physical ideal limit first and compare. 
9. **Reference to compare with, and acceptance.** Reference data to validate the model; if none, an exact answer (analytical solution, limiting case, or a published table row). Then the **acceptance**: metric, target, unit, and what it is measured against (for example heat flow error below 10% against data set X). Fixed now, before building: a miss later is a measured value beyond it.
10. **Fragile spots.** Zero flow, reverse flow, phase change. Part of model documentation.

Fuzzy words go into `GLOSSARY.md` at once. Hard-to-undo decisions get a one-page note in `docs/adr/`.

Before finishing, recap the problem setup and ask user confirmation then suggest `/to-issue`.

Files: see [templates/work-layout.md](../../../templates/work-layout.md).
