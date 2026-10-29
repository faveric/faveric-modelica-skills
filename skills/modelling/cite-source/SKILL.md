---
name: cite-source
description: Register a published source for an equation, correlation or constant used in a model, with where it is in the source, its valid range, and a check that it was transcribed correctly. Use the moment one appears.
---

A citation lends authority to a number. Make sure it is earned.

**Where things go**
- `refs/refs.bib`: the BibTeX entry. `refs/pdf/<key>.pdf`: the PDF (local only, git-ignored).
- `refs/transcriptions/<key>.md`: the equation as written, SI units of every symbol, the authors' conditions, and the exact **locator** in the **source**.
- `// cite: <key>` next to the Modelica function, equation, or constitutive relation that uses it.
- An entry under `sources` in the issue header (`key`, `used_for`, `locator`, `validity_verified`, `validity`, `transcription`, `check_script`, `extrapolation_adr`).

**Steps**
1. Find the **source** and add it to `refs/refs.bib`. If you cannot read the primary text, the **locator** stays `TO-VERIFY`, `validity_verified: false`, and the **transcription status** `pending`; say so. Never fill in an equation number, page or **validity range** from memory.
2. Write the transcription note in `refs/transcriptions/<key>.md`, listing each variable, unit, and assumption as stated by the authors.
3. Record the **validity range** per variable as the authors state it (from the original, not a secondary review).
4. Compare it with the model's **envelope**. If the model goes outside: narrow the envelope, find another source, or write an extrapolation ADR and put its id in `extrapolation_adr`.
5. **Check the transcription** (`check_script`) against a value or closed-form benchmark the source itself establishes (a published table row, analytical identity, or limiting value), with an independent script executed by G9 (`python3 -I <check_script>`). Match: `numeric-checked`. Only a second implementation from your own transcription: `cross-implemented`, which does not count at L1.

**What each level needs**
- L0: key, `// cite:` tag and issue entry. Locator and checks may stay `open`, keeping status `"has not been verified"`.
- L1: locator read, `validity_verified: true`, validity range recorded and containing the model's envelope, and `numeric-checked` with a passing `check_script`.

Typical slips: sign, exponent, reciprocal inversion, unit conversion factor, constitutive relation applied outside its valid regime, or a misprint copied from a secondary source.
