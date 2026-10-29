# Glossary

The shared language of these skills. Use these words exactly.

**Intended use** — the decision the model will support. Declared in the issue as a level: **L0** exploration (orders of magnitude, concept comparison) or **L1** design decision (sizing, choosing between architectures). L2 (consequential or safety-relevant decisions) is out of scope.

**Context of use** — the intended use plus the conditions it applies to. It fixes how much rigour is required.

**Envelope** — the declared operating domain of a model: for each variable, the range in which the model is meant to be used. Also called operational domain or applicability range in the literature. Guarded in the code by asserts.

**Source** — a literature item (paper, book, standard) from which an equation or number enters a model. Always has a key in the reference manifest, a **locator** (equation, table or page) and a **validity range**.

**Locator** — where in the source the equation lives. Never filled from memory; `TO-VERIFY` until read.

**Validity range** — the variable ranges for which the source's authors claim the relation holds. The model envelope must sit inside it or carry a documented extrapolation.

**Transcription status** — `pending` (equation copied, not checked), `cross-implemented` (a second implementation from the same transcription agrees; weaker, catches coding errors not transcription errors) or `numeric-checked` (re-computed independently and matched a value published by the source). Only `numeric-checked` supports a `verified` claim at L1.

**Gate** — an executable check with an id (G1–G10, see `verify-physics`). Each is **blocking**, **required-at-L1** or **informational**.

**Coherence** — passing balance, unit and second-law gates. Proves internal consistency, not correctness.

**Verification** — evidence that the model implements its stated equations correctly (exact or manufactured solutions, limit cases, order of accuracy and numerical-error estimates where relevant; translation without errors is a prerequisite, not verification).

**Validation** — evidence that the equations represent reality for the intended use (comparison with independent data or literature benchmarks over a declared sub-range).

**Status** — the claim a model's record makes: `has not been verified` / `has been verified`; `has not been validated` / `has been validated` / `validated with limitations`. Values follow the MIC Core examples. A status can never exceed its evidence.

**Open** — evidence honestly declared as still pending. Not a failure. Distinct from **fail**, which means a claim exceeds its evidence or a check is violated.

**Credibility record** — the SRMD file next to a model, carrying MIC Core attributes and the `credibility` classification (intended use, envelope, sources, gate results, file hashes).

**Stale record** — a record whose stored hash no longer matches the model files. Its status is void until the gates are re-run.

**Reference state** — the zero of enthalpy and entropy (or domain reference potential) used by a medium or constitutive model. Components joined at an interface must share it or declare a conversion.

**Structural singularity** — a DAE whose equation-variable matching or index reduction (`Pantelides` / `clockPartitioning`) fails even when global equation and variable counts match (`checkModel` reports `N == N`). Caught only by full translation/build (`buildModel` / `translateModel`).

**Bidirectional causality** — an acausal two-port or multi-port model whose connectors, boundary evaluations, and constitutive laws remain well-posed across zero through-flow (`f = 0`, e.g. zero current, zero torque, zero mass flow) and under sign reversal (`f > 0` and `f < 0`).

**Engine** — the tool that translates and simulates: OpenModelica (`omc`) by default, Dymola optionally. **Engine contract**: `load_library`, `check_model`, `simulate`, `read_results`.

**Static-only mode** — no engine available. Static and numeric-on-supplied-results gates run; the model can never be called `verified`.

**Tracer task** — the thinnest vertical slice through all layers (model, gate, record). The first task of every issue.

**Fault seed** — a known defect planted in a correct reference to test whether the gates catch it.

**Baseline** — the unmutated reference artifacts; must produce zero fails.

**Detection** — a fault seed is detected when at least one of its expected gates reports fail.

**Learner** — the process that runs after an issue's conclusion is written (`learn-from-issue`): it collects evidence and proposes at most three *candidates*; it never installs anything. A person approves each candidate (`approve-lessons`) before it enters the library (ADR-0018).

**Base skills** — the domain-agnostic public skills in `skills/` applicable to any Modelica domain (electrical, mechanical, control, thermal, fluid).

**Library overlay** — domain- and library-specific lessons and skills for the library the plugin is used on: notes in `.modelica-skills/learned/<skill>.md` and approved skills in `.claude/skills/`, with an append-only ledger and a generated index. Tracked in the library's repository, git-ignored in the public skills repository.
