# Literature behind the design

What each source is used for here. URLs were read during authoring (October 2026). Where only a summary page was available rather than the full text, it says so. Nothing in the skills quotes a page, equation number or validity range from these sources; those are `TO-VERIFY` until someone reads the originals.

## Verification, validation, credibility

| Source | Used for | Read |
|---|---|---|
| ASME VVUQ standards overview, <https://www.asme.org/Codes-Standards/publications-information/Verification-Validation-Uncertainty> | Definitions: verification asks whether the computational model fits its mathematical description; validation asks whether it represents the real application. The split behind `verify-physics`. | Summary page only (standards are paywalled) |
| ASME V&V 40 framework as summarised in <https://link.springer.com/chapter/10.1007/978-3-031-48284-7_4> | Risk-informed credibility: the overall model risk sets the required degree of verification, validation, uncertainty quantification and applicability. Basis for intended-use levels (ADR-0008). | Chapter summary |
| NASA-STD-7009 credibility factors, <https://ntrs.nasa.gov/citations/20160000202> | Eight credibility factors (verification, validation, input pedigree, results uncertainty, results robustness, use history, M&S management, people qualifications); a credibility scale is a way to *communicate* credibility, not to measure it. | Abstract / presentation |
| NASA-STD-7009A full text, <https://ntrs.nasa.gov/api/citations/20160011121/downloads/20160011121.pdf> | Structure of the standard; 7009B (2024) is the latest revision per <https://www.validas.de/resources/glossary/nasa-std-7009b> | Table of contents |
| Oberkampf & Roy, *Verification and Validation in Scientific Computing* (Cambridge, 2010; 2nd ed. 2025) | Code verification via exact solutions and manufactured solutions; solution verification; why scientific system-level testing is hard (output depends on algorithm, tolerances, time step). | Table of contents and chapter abstracts |
| Roy et al., *Verification of Euler/Navier-Stokes codes using the method of manufactured solutions*, <https://www.aoe.vt.edu/content/dam/aoe_vt_edu/people/faculty/cjroy/Publications-Articles/IJNMF.final.2004.pdf> | Benchmark and code-to-code comparisons build confidence but do not replace rigorous code verification. Basis for treating G6 reference comparison as distinct from coherence gates. | Excerpt |

## Modelica practice

| Source | Used for | Read |
|---|---|---|
| BuildingsPy regression testing, <https://simulationresearch.lbl.gov/modelica/buildingspy/development.html> | Regression tests compare example-model results against stored reference points; works with Dymola, OPTIMICA, OpenModelica. Informs G7. | Docs excerpt |
| AixLib test management, <https://github.com/RWTH-EBC/AixLib/wiki/Test-Management> | Accept changed reference results only if the change is explained and documented in the pull request. Basis for G7's rule. | Wiki excerpt |
| MoPyRegtest, <https://pypi.org/project/mopyregtest/> and its Modelica Conference paper | Lightweight CI-friendly regression testing on OpenModelica; observation that developers use other test strategies before regression tests. | Package page and abstract |
| MSL regression setup, <https://github.com/modelica/ModelicaStandardLibrary/files/4270977/SetupForMSLRegressionTesting_2014-01-13.pdf> | Reference results kept per example, compared across tools. | Excerpt |
| Gall et al., *Continuous development and management of credible Modelica models*, <https://ecp.ep.liu.se/index.php/modelica/article/download/214/174> | Model requirements, validation and data management in a traceable development process for Modelica models. | Abstract |

## Traceability and metadata standards

| Source | Used for | Read |
|---|---|---|
| SSP Layered Standard Traceability 1.0 (2025-08-29), <https://ssp-standard.org/ssp-ls-traceability/1.0.0> | Credible Simulation Process phases; SRMD format; classifications (keyword-value pairs, reverse-domain types) as the extension mechanism; documentation quality does not guarantee process quality. Basis for ADR-0009 and `docs/flow.md`. | Specification text (SRMD chapter truncated in the fetch) |
| MIC Core specification, <https://mic-core.github.io/MIC-Core/main/> | Attribute list (mandatory: model name, supplier, confidentiality level, release) and the SRMD mapping with `org.mic-core.mic-core` classification and exact keywords. | Full text including Appendix A |
| Heinkel & Steinkirchner et al., Credible Simulation Process, <https://ecp.ep.liu.se/index.php/modelica/article/download/572/542> | Framework: simulation request, credible modelling process, continuous credibility assessment. | Excerpt |
| Hällqvist et al., uncertainty quantification across Modelica / FMI / SSP, <https://ecp.ep.liu.se/index.php/modelica/article/download/1354/1168/1617> | Operational domain as part of model credibility information. | Excerpt |
| Lenord, Brück, Lobner, credible system simulation for heat pump systems with Modelica, FMI, SSP, <https://fmi-standard.org/assets/literature/Modelica_and_FMI_Conference_2025/Bosch_Dassault-Systems_eXXcellent.pdf> | Existence proof that this traceability stack is being applied to heat pump systems. | Abstract |
| Dymola SRMD support, <https://ecp.ep.liu.se/index.php/modelica/article/download/982/890/1003> | Dymola converts SRMD metadata to model annotations. | Excerpt |
| OMSimulator SRMD validation, <https://github.com/OpenModelica/OMSimulator/pull/1417/files> | OpenModelica tooling validates SRMD. | Pull request excerpt |

## Scientific computing practice

| Source | Used for |
|---|---|
| Wilson et al., *Best Practices for Scientific Computing*, PLoS Biology 2014, <https://doi.org/10.1371/journal.pbio.1001745> | Version control, modular code, keep raw data: the baseline for `setup-modelica-skills` conventions. |
| Wilson et al., *Good Enough Practices in Scientific Computing*, PLoS Comput Biol 2017, <https://doi.org/10.1371/journal.pcbi.1005510> | Same, reduced to a minimum set. |

## Workflow

| Source | Used for |
|---|---|
| Pocock, *Skills For Real Engineers* (MIT), <https://github.com/mattpocock/skills> | Reference for the interview, issue and task workflow. The skills here are written for Modelica. |
