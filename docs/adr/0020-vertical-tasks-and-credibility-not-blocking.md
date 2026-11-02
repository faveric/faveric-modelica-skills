# 0020. Vertical tasks, an orchestrating parent, and gates that record credibility

- **Status**: Accepted
- **Date**: 2026-11-02

## Context
Testing the workflow showed three problems. Issues were split into many small tasks, so no task carried the physics from problem to answer and results sat between tasks without a conclusion. Task bodies had no schema, so each agent wrote them freely. Gates blocked closing, so a model that ran and was compared could still not produce an answer.

## Decision
- A **task is a vertical slice**: one behaviour added to the model, through define, model, simulate, compare, conclude, closable by an agent that knows nothing else. `templates/task.md` has five sections (Physical question, Model, Run, Compare, Answer) and a header slice generated from the issue by `mlissue.py task`.
- **Split by behaviour, in progression**: thinnest working model first, each later slice extends the same model with one behaviour and keeps it runnable (tank with water, then simple two-phase, then HNE-DS exit flow). Every slice has its own comparison; one without is merged into its neighbour. Never split by phase. A slice extending the previous one is `builds_on` it (`blocked_by` set to match, previous Answer quoted); other `blocked_by` only when a task consumes another's result.
- **No numeric cap on slices; the plan is agreed first.** `/to-tasks` presents the progression (behaviour, physical question, comparison per slice) and creates tasks after the person agrees.
- The **parent issue is the orchestrator**: it owns Define and Conclude and never builds. `/review-model` writes the conclusion from the tasks' Answers (`mlissue.py answers`). `can-close` needs the conclusion with an **Answer** section and an Answer in every task.
- **Gates record credibility; they do not block.** The Answer states `verified`, `partial` or `assumed`, with each unverified gate and assumption, written by the agent as "agent-recorded, unreviewed". Loosening a tolerance, removing a guard, and promoting `partial` to `verified` stay with the owner. At L1, `partial` closes as usable at L0 only.

## Consequences
- ADR-0017 `accepted_gaps` keeps its meaning (the owner's recorded decision the record reads); the agent's own gap notes live in the Answer and do not change what the record may claim.
- The gate code is unchanged. It already reports `open` and `skip`; what changed is that `implement` no longer loops on failures and closing does not depend on them.
- Slices share model files, so `builds_on` carries the previous Answer; a slice that was `partial` is visible to the next one.
- An issue always has at least one task, so `mlstate` derives the stage as before.
