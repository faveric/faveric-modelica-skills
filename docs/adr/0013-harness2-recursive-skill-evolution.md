# ADR 0013: Two-Stream Harness² Recursive Skill Evolution — Domain-Agnostic Base Skills vs. Target Library Overlays

- **Status**: Accepted; the Harness² evaluator and the read of `experience.json` are superseded by ADR-0018 (the two streams stay)
- **Date**: 2026-10-28

## Context
`modelica-skills` is a public, domain-agnostic skill library designed to be installed on any Modelica repository across **any physical domain** (electrical, mechanical, multibody, control, thermal, fluid). When an agent uses **Harness²** (arXiv:2610.14224 — *Task-level Propose–Probe–Compose* + *Harnessing-level Experience Reflector*) while developing models in a target library, the resulting lessons belong to two distinct scopes:
1. **Universal Modelica & DAE truths** (applicable to electrical circuits, mechanical drivetrains, control blocks, and fluid networks alike):
   - A model can pass `checkModel()` with equal equation and variable counts (`N == N`) and still fail `buildModel` / `simulate` due to a **structural singularity** (`Pantelides` / `clockPartitioning` failure, e.g., parallel capacitors or coupled differential states constrained against a single boundary potential).
   - Assigning sub-component connector potentials/flows via raw equations instead of `connect(...)` leaves default zero-flow equations active and over-determines the DAE by $N$ equations.
   - Passing dimensional variables (`A`, `V`, `N`, `kg/s`, `W`) into dimensionless $C^\infty$ regularization functions (`smoothStep`/`tanh`) triggers unit errors under `omc --unitChecking` that static declaration checks miss.
   - Components that experience through-flow sign reversal (`i`, `tau`, `m_flow`, `Q_flow` crossing zero) require **bidirectional causality** and smooth $C^\infty$ transitions across zero.
2. **Target-library and domain-specific knowledge**:
   - Constitutive closures, domain-specific discretization schemes, medium/property library conventions, and container/solver staging specific to the library where the skills are installed.

## Decision
We divide Harness² skill evolution into **two explicit streams**:

1. **Stream A — Public Base Skills (`skills/`, `GLOSSARY.md`, `evals/`, version-controlled in `modelica-skills`)**:
   - Strictly **domain- and library-agnostic**: no references to any specific user library, company, or domain-narrow workflow appear in `modelica-skills`.
   - Incorporates universal Harness² upgrades: `buildModel` structural-singularity detection in `G1` (`E5-balanced-count-singular-dae`), `omc --unitChecking` in `G2` (`E1-dimension-mismatch`), `connect(...)` vs. raw equation rules (`E2-overdetermined`), passive dissipation / Second-Law checks in `G4` (`E6-second-law-violation-in-model`), and **bidirectional causality** / removable-singularity checks in `G5` (`E7-cr1-singularity-in-model`).

2. **Stream B — Target Library Overlay (`.modelica-skills/learned/` inside the target library, git-ignored in `modelica-skills`)**:
   - When the skills are installed on a target library (electrical, thermal, fluid, mechanical), `evals/harness2.py` reads and syncs `<target-repo>/.modelica-skills/learned/` (`diagnosing-simulation.md`, `model-design.md`, `verify-physics.md`, `experience.json`).
   - In `modelica-skills`, `**/.modelica-skills/learned/` and `skills/local/` are in `.gitignore` so target-library knowledge never pollutes the public skills repository.
   - In the target library itself, `.modelica-skills/` (including `.modelica-skills/config.yml` and `.modelica-skills/learned/`) can be versioned as part of that library's own evolution.

## Consequences
- `modelica-skills` remains 100% generic, clean, and reusable on any public or private Modelica project in any domain.
- Target libraries evolve their own `.modelica-skills/learned/` domain knowledge via `evals/harness2.py --target-repo <path>` while benefiting from the universal Stream A gates (`G1`–`G10`).
