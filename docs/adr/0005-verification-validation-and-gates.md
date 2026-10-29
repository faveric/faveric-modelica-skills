# 0005. Verification is separate from validation; eleven gates

Status: accepted

Gates G1–G10 (G6 split into G6a and G6b, so eleven in all) are defined in `verify-physics`. They are split into **coherence** (compile, units, conservation, second law, limit cases), **verification** (exact or manufactured solution comparison), **validation** (independent data or literature benchmark), and **integrity** (reference-state consistency, citation integrity, record freshness).

Passing coherence gates never earns `has been verified`. Balance and second-law checks prove internal consistency, not correctness: a wrong effectiveness relation can close the energy balance exactly.

Basis: ASME V&V terminology; Roy et al. on code-to-code and benchmark comparisons being confidence-building, not verification.

Regression (G7) is informational; it shows reproducibility, not correctness. A changed reference result is accepted only with a written explanation.
