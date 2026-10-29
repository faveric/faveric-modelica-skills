# Scope

## In scope

- Component, system and calibration work in Modelica, in that dependency order (ADR-0001).
- Intended use levels **L0** and **L1** (ADR-0008).
- A deterministic gate set (G1–G10) evaluated statically and with OpenModelica (ADR-0005, ADR-0013).
- Literature handling: manifest, locators, validity ranges, transcription checks (ADR-0004).
- A credibility record in SRMD with MIC Core and one extension classification (ADR-0009).
- Engine-agnostic orchestration; OpenModelica as default runner, Dymola optional (ADR-0002).

## Out of scope on purpose

- **L2**: decisions with consequential or safety-relevant outcomes. These need independent review, uncertainty quantification and a governance process that a set of agent skills cannot supply. If a model is used that way, these skills are not enough, and the README says so.
- **Fault injection in production libraries.** Mutation testing was useful during initial bootstrap of the gates (ADR-0010), but is dangerous when invoked on real user libraries (ADR-0014); skills change only through the approved, non-destructive learner of ADR-0018.
- **Other engines.** The repo ships an OpenModelica adapter (`evals/adapters/omc_cli.py`, local or Docker) and a stdio MCP server wrapping it (`server/modelica_mcp.py`, ADR-0015). A Dymola MCP server (`server/dymola_mcp.py`, ADR-0016) translates and simulates, but a Dymola adapter for the gate runner is not built.
- **FMU / SSP export.** The record is SRMD so that export becomes possible; packaging is not built.
- **Full NASA-STD-7009 compliance.** Three ideas are adopted (use sets rigour, verification separate from validation, traceability record). The standard's requirement set is not.
- **Uncertainty quantification beyond declared tolerances.** Parameter uncertainty propagation is left for a later version.
- **Library-specific advice** (Modelica Standard Library, Buildings, AixLib, commercial libraries). `model-design` is library-agnostic; reference-state and media choices are declared per issue (ADR-0012, proposed).

## Honest limits

- Gates that need an engine (G1, G3–G6) have been verified with OpenModelica (`evals/adapters/omc_cli.py`); other engines (e.g. Dymola) require their respective adapters.
- Nothing here has been tested with an agent other than in the review loop that produced it.
