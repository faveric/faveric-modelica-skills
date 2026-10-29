# 0009. Credibility record: SRMD with MIC Core and one extension classification

Status: accepted

The record is an SRMD file (SSP-LS-Traceability 1.0) placed beside the model. It carries the MIC Core classification (`org.mic-core.mic-core`, exact keywords from the MIC Core appendix) and one extension classification for what MIC Core does not define: intended-use level, envelope, sources, gate results, model file hashes, tolerances.

We stay inside the standard because deviating needs a substantial advantage, and none was found: the extension mechanism (classifications with reverse-domain types) covers our fields. YAML would give nicer diffs; that is not a substantial advantage.

**Unconfirmed**: element and namespace names in the template are placeholders and may differ from the published schema (a reviewer recalled `ssc:ClassificationEntry`; not verified). The claim "stay inside the standard" holds for the structure (classifications, keyword-value entries, MIC Core keywords) but not yet for the serialisation. First task once the XSD is in hand: validate the template and adapt `tools/mlrecord.py`.

Placeholders and cautions:
- The extension type defaults to `org.example.modelica-skills.credibility`. Replace with a domain you control (config key `credibility.classification_type`).
- The SRMD `checksum` attribute's algorithm was not confirmed from the specification text read; model file hashes are stored as classification entries (`model.file`, SHA-256) instead.
- Version values in parts of the 1.0 specification still read as pre-release; pin the schema version and isolate the template.
- Life-cycle states in the standard apply to phases and steps; verification and validation status live in MIC Core entries.
