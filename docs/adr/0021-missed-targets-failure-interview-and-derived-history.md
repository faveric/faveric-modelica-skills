# 0021. A missed target is a normal close; a failure interview and a derived history keep what was learned

- **Status**: Accepted
- **Date**: 2026-11-02
- **Extends**: ADR-0020 (gates record credibility, they do not block), ADR-0018 (issue-end learner).

## Context
With ADR-0020 a model that misses its accuracy target still closes. Nothing then separated "poorly verified" from "verified and still missed", nothing declared the target before building, and the follow-up work had no schema. The learner discarded "unresolved dead ends", so what a failed attempt ruled out was lost.

## Decision
- The header declares an **`acceptance`** list (`metric, target, unit, against`) during the interview, before building. The conclusion's Answer starts with **`Outcome: met | missed`** and the measured number against the target. Outcome is separate from credibility. `can-close` requires it, with a number. A `## Deviations` section holds the agent's own notes; `Accepted gaps` keeps only owner decisions.
- **`/interview-failed-issue`** (user-invoked, read-only) runs on a closed `missed` issue, before the learner. It starts from the evidence, classifies the cause (model, reference, target, setup), ranks hypotheses by cheapest discriminating test, and ends in exactly one of **recover**, **accept** (the owner revises the acceptance, with an ADR) or **stop**. It writes `docs/issues/<id>-failure.md` and never edits a closed issue. The agent never changes a target.
- A **recovery issue** has `follows: <id>` and `baseline: {metric, value, target}`. `mlissue check` requires `follows` to name an existing issue whose conclusion says `missed`, and a complete baseline. Every recovery issue's generated block carries the **history** of all its ancestors (`mlissue.py history`), derived from the files on every run, so it cannot disagree with them. There is no limit on the length of a chain.
- Hypotheses (`H1 [open]` in a failure note) change status only in a **later issue's conclusion** (`## Hypotheses tested`, `ISSUE-001:H2 ruled-out, evidence: ...`). `ruled-out` and `confirmed` must cite evidence, or `check` warns. The history shows the latest status per hypothesis.
- The **learner** keeps tested negatives: rule 3 now excludes *untested* dead ends and suspicions. `mllearn collect` adds the failure note and the history as citable items, and refuses a `missed` issue that has no failure note. The learner also runs at the end of a chain. The cap of three candidates and `/approve-lessons` stay.
- `mlstate` routes a closed `missed` issue without a failure note to `/interview-failed-issue`.

## Consequences
- The history lists earlier attempts only; an issue's own tests of hypotheses appear in the history of the next issue. The "attempt" column is the issue title, so titles of recovery issues should say what changed.
- Outcome is read from one line of the conclusion with a regular expression; an Answer that words it differently is refused by `can-close` and has to be fixed, not worked around.
- A failure note whose decision is accept or stop ends the chain. Nothing checks that an accept has its ADR; the note links it by hand.
