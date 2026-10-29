---
name: model-design
description: House rules for writing Modelica components across any domain: small models, clear acausal interfaces, units everywhere, range guards, bidirectional causality, no magic numbers. Use when writing or reviewing Modelica.
---

Follow the repo's existing conventions and `.modelica-skills/learned/model-design.md` (if present) first; use these **base skills** rules for all domains.

1. One physical idea per model. If it needs a paragraph to explain, split it.
2. Small, explicit acausal interfaces. Use the library's standard connector pairs (e.g. `p`/`n` pins, `flange_a`/`flange_b`, `port_a`/`port_b`, `heatPort`). Always connect sub-component connectors with `connect(...)` rather than assigning connector potentials/flows directly in equations (which leaves default zero-flow equations active and over-determines the DAE).
3. SI units on every `Real` (`unit="1"` if dimensionless). Add `min`, `max`, `nominal` where useful. Normalize dimensional arguments (`x / x_scale`) before passing them to dimensionless helper functions so `omc --unitChecking` passes cleanly. Never put `min=0` or `max=0` on connector through-variables (`i`, `tau`, `m_flow`, `Q_flow`) when **bidirectional causality** is required.
4. No magic numbers: name them, give units and a description, cite a source if empirical (`// cite: key`).
5. A range guard (`assert`) for each variable in the issue's **envelope**, with a message saying what range was left. Use a warning where extrapolating is tolerable, an error where the model is undefined.
6. Where a denominator, Jacobian, or removable singularity can reach zero (e.g. `1 - Cr -> 0`, `v -> 0`, `f -> 0`), use a named regularization scale and smooth $C^\infty$ transition (such as `tanh`) and test the limit case in `G5`.
7. **Bidirectional causality & index-1 boundaries:** for any two-port or discretized network component:
   - Formulate constitutive and transport equations symmetrically with respect to port direction so through-flow reversal (`f > 0 <-> f < 0`) is smooth across zero.
   - Ensure boundary coupling of discretized/multi-state models does not over-constrain multiple differential states against a single boundary potential (`structural singularity`).
8. **External C compatibility:** avoid arrays of external-C state records when the compiler cannot generate array helpers; bind scalar variables or scalar helper calls directly.
9. State the **reference state** (or ground/datum convention) where applicable: `// reference-state: <id>`.
10. Use `replaceable ... constrainedby` or selectable dispatchers for exchangeable constitutive closures.
11. Tests are models: `Examples` and regression test packages, with stored reference results covering nominal, limit, and sign-reversal regimes.
12. A short documentation annotation: purpose, assumptions, envelope, source keys.

Warning signs: copied equations, parameters without units, direct equation assignment to a connector instead of `connect(...)`, `checkModel` tested without `buildModel`/`simulate`, hand-tuned constants hiding a structural error, `noEvent` sprinkled to quiet the solver.
