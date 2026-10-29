# Flow and the Credible Simulation Process

The skills follow the phase structure of the Credible Simulation Process in SSP-LS-Traceability 1.0: analysis, requirements, design specification, implementation, execution, evaluation, fulfilment. In that process each phase has its own verification step, so errors are caught where they enter instead of after implementation.

| CSP phase | Skill | Consistency check closing the phase |
|---|---|---|
| Analysis of simulation task | `interview-model` | Units declared; envelope variables named; every correlation has a source key; intended use level set |
| Requirements | `to-issue` | Issue front matter parses; every cited validity range contains the envelope or documents an extrapolation; tolerances declared |
| Design specification | `to-tasks` | Every gate in the issue is the acceptance criterion of a task; blocking edges acyclic |
| Implementation | `implement` (+ `verify-physics`, `cite-source`, `credibility-record`, `model-design`) | Gates G1–G5, G8–G10 green; G6 run where required |
| Execution | engine, via the engine contract | Engine, version and date written into the record |
| Evaluation | `verify-physics`, `review-model` | Status does not exceed evidence |
| Fulfilment | `review-model`, record close-out | Issue's intended use is met or the shortfall is stated |

`calibrate` is a branch off Evaluation: it changes parameters, so it re-enters Implementation and Evaluation for the same model.

## Dependency order across levels (ADR-0001)

```
component  ──►  system  ──►  calibration
  records its envelope        reads component envelopes;       refuses to fit while
  and gate results            fails if used outside them        structural gates fail
```

A system issue lists the components it uses and their record versions. If a component record is stale (G10), the system cannot claim `verified`.

## Starting a session

`/startsession` derives the stage of every issue from the files (`tools/mlstate.py`, MCP tool `project_state`) and suggests one next command. It changes nothing and never invokes another user-invoked skill (ADR-0019).

## After the last task: conclusion and learning

`review-model` writes `docs/issues/<id>-conclusion.md`. Then `learn-from-issue` proposes at most three lessons or library skills from that issue's evidence, and `approve-lessons` lets a person approve, edit or reject each before it enters the library (ADR-0018).

## Accepting a gap

A gate that cannot or should not run is listed by the owner in the issue (`accepted_gaps`, level L0). The record then reads "accepted with skipped gates" and the model cannot be called verified (ADR-0017).

## Decision points that deserve a human

- Declaring L1 for a model whose output feeds something other than a design comparison.
- Extrapolating beyond a source's validity range.
- Tolerances that are loose relative to the solver tolerance.
- Choosing a reference state or medium library when two components differ (ADR-0012).
