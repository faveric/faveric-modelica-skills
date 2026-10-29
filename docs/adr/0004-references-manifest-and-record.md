# 0004. References: versioned manifest, local PDFs, evidence per equation

Status: accepted

Sources are PDFs. They are not committed (copyright). The repo carries a BibTeX manifest (`refs/refs.bib`) and transcription notes (`refs/transcriptions/<key>.md`); PDFs live in `refs/pdf/`, git-ignored.

For every equation or correlation entering a model the minimum record is key + locator + validity range (level b). For correlations in principal balances a **transcription check** is required (level c): re-compute a published numeric value, and record `numeric-checked`. A second implementation from the same transcription is `cross-implemented` and does not count at L1: it cannot reveal a transcription error.

Why: extracting equations from PDFs is the fragile step; a citation lends authority to a number nobody checked. The check is the only thing that catches transcription errors.

Consequence: `verified` at L1 requires every principal-balance source to be `numeric-checked`.
