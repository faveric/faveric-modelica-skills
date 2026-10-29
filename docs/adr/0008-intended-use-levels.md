# 0008. Two intended-use levels, L2 out of scope

Status: accepted

- **L0 exploration**: orders of magnitude, concept comparison. Gates G1–G5 blocking; G6 only if the issue declares a reference.
- **L1 design decision**: sizing, architecture choice. Adds G6 (reference comparison) as required, G8 and G9 blocking, envelope asserts mandatory, transcription checks for principal-balance correlations.
- **L2** (consequential or safety-relevant decisions): not supported. It needs uncertainty quantification, independent review and a governance process. The README and `SCOPE.md` say so; `to-issue` refuses to declare L2.

Basis: risk-informed credibility (ASME V&V 40; NASA-STD-7009 criticality). The level is declared in the issue and scales the gates.
