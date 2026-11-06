# 0024. Keep ADR-0020 after the conflict review of the orchestrator proposal

- **Status**: Accepted
- **Date**: 2026-11-06

## Context
ADR-0023 proposed an orchestrator skill, a branch per issue, task approval and one review per issue. A code review and a conflict analysis of that work found it contradicted the rules already in force: it let the orchestrator close tasks while `implement` also closed them, it reused the word "orchestrator" that ADR-0020 gives to the parent issue, it made closing depend on gates where ADR-0020 says gates record credibility and do not block, and it left states from which the workflow could not move (an approved task whose boxes nobody ticked, a reopened task still read as closed, a parent paused for good after a failed spin-off).

## Decision
- **ADR-0020 stands unchanged.** The parent issue is the orchestrator in its sense: it owns Define and Conclude. Gates record credibility. Loosening a tolerance, removing a guard and promoting `partial` to `verified` stay with the owner.
- **ADR-0023 is superseded.** Its file stays, with the status changed.
- **The skills are the source of truth** for the workflow built on top of ADR-0020: `repo-manager` (coordinates, never closes), `implement` (the only place a task is closed or approved), the task `status` lifecycle, the branch per issue and the spin-off rules. ADRs are reference for developing this library.
- An agent closing a task alone on clear closure, and a person approving otherwise, decides who closes; it does not make gates block, so it does not change ADR-0020.
- ADR-0019 is not edited. Its stage list is older than the code; `tools/mlstate.py` and `startsession` give the current stages (approval, paused, failure, tracker added).

## Consequences
- No new rule contradicts ADR-0020, ADR-0019 or ADR-0005 (task credibility `verified` means the named gates passed, not the record status `has been verified`).
- The workflow can change by editing skills and tools, with tests, without a new ADR, as long as it keeps ADR-0020.
