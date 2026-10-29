---
name: interview-model
description: Question session that fixes what a model is for, its physics, ranges and sources before any Modelica is written. Updates the glossary and records decisions.
disable-model-invocation: true
---

Follow the `interviewing` rules. Read `GLOSSARY.md`, `.modelica-skills/config.yml`, existing issues and records first. No config: suggest `/setup-modelica-skills`.

Ask in this order:

1. **Use.** What decision does the model support? L0 (rough comparison) or L1 (design decision). Refuse L2 (see `SCOPE.md`).
2. **Boundary.** What is in, what is out, what crosses the edge.
3. **Physics.** Equations in words, then symbols. Steady or dynamic. What is neglected and what would make you distrust the result.
4. **Fluid and reference state.**
5. **Ranges.** For each variable: min, max, unit, and what happens outside (warn or stop).
6. **Sources.** Where does each correlation or constant come from? Use `cite-source` as soon as one appears, and compare its valid range with step 5.
7. **Feasibility.** For every target the model must reach (an outlet temperature, a superheat, a flow), compute the physical limit first and compare. A target beyond the limit is a finding for the owner, not a tuning problem.
8. **Exact answer to compare with.** A closed form, a simple limit, or nothing (then it cannot be called verified).
9. **Data to compare with.** Which range? None means it stays unvalidated.
10. **Fragile spots.** Zero flow, reverse flow, phase change.

Fuzzy words go into `GLOSSARY.md` at once. Hard-to-undo decisions get a one-page note in `docs/adr/`.

Before finishing, check: every variable has a unit, every correlation has a source whose range contains the ranges from step 5, the level is set. Show the log, then suggest `/to-issue`.
