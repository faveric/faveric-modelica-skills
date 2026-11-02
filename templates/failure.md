# <ISSUE-000> failure note

Written by `/interview-failed-issue` for a closed issue whose conclusion says `Outcome: missed`. One page. The closed issue is never edited; this file and the recovery issue are the follow-up.

## Benchmark
Measured vs target, with the reference and range, as the conclusion states it (for example error 30% vs required 10%, against data set X over range Y).

## Cause bucket
One of: **model** (a neglected effect, a correlation outside its source's validity), **reference** (data uncertainty, mismatched conditions), **target** (the acceptance was not justified for this data), **setup** (boundary conditions, numerics). Say why, in one or two lines; `suspected` or `confirmed`.

## Hypotheses
One line each, ranked, cheapest discriminating test first: `H1 [open] <hypothesis>; test: <what to run>; shows: <what result confirms or rules it out>`. Status is `open`, `ruled-out` or `confirmed`. A later issue changes a status in its own conclusion, never here.

## Evidence
What was read, with locations (conclusion, task Answers, gate results, record). Facts only.

## Decision
**recover** | **accept** | **stop**, who decided, why.
- recover: the recovery issue's header gets `follows: <this issue>` and `baseline`; suggest `/to-issue`.
- accept: the owner revises the acceptance; the ADR is `docs/adr/<n>-...md` and is linked here.
- stop: the reason, and what is known to be ruled out.
