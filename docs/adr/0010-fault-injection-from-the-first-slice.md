# 0010. Evaluate with fault injection, harness present from the first slice

Status: accepted

Correct reference artifacts get known defects planted (a parallel-flow effectiveness in a counterflow model, a cold-side sign flip, a missing unit, a citation key absent from the manifest, an envelope wider than the source's validity range, a stale record hash, a record claiming more than its evidence). The gates are scored on detection.

Scope of what the score means: seeds in the Python mirror (`layer: mirror`) test the numeric checks, not the Modelica file. Seeds in the `.mo`, issue, manifest or record are judged by the static gates. Seeds that only an engine can see are `needs_engine` and reported as skipped. A **blind spot** (N5, a coherent exponent slip in a correlation) is kept on purpose: the harness checks that the system does not claim more than it knows (G9 stays `open`), and the only real defence is a transcription check against published values.

Two layers:
1. **Deterministic** (`evals/run_faults.py`): static and numeric gates over mutated artifacts; runs without an engine.
2. **Agentic** (`evals/agentic/`): a protocol for giving an agent faulty artifacts with and without the skills and scoring what it finds.

Why from the start: without a score, tuning the skill text is guesswork. Tuning means raising detection without raising false fails on the baseline.

Findings are expected to be uncomfortable: coherence gates (G3, G4) will miss faults that only a reference comparison (G6) catches. That is the point of the harness.
