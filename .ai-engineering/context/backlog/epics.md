# Epics

## Update Metadata

- Rationale: rebase epics to final governance architecture.
- Expected gain: delivery focus on MVP-critical controls.
- Potential impact: older epics and sequencing are superseded.

## EPIC-1: Ownership and State Foundation (P0)

- ownership map and system state files.
- installer/updater ownership-safe behavior.
- migration/versioning support.

## EPIC-2: Mandatory Local Enforcement (P0)

- non-bypassable hooks.
- mandatory checks: `gitleaks`, `semgrep`, dep vulnerability and stack checks.
- protected branch and main/master protection.

## EPIC-3: Command Contract Runtime (P0)

- `/commit`, `/commit --only`, `/pr`, `/pr --only`, `/acho`, `/acho pr`.
- `/pr --only` warning + optional auto-push + continuation modes.

## EPIC-4: Remote Skills Trust Model (P0)

- remote ON with cache and lock.
- checksums + signature metadata scaffolding.
- offline fallback logic.

## EPIC-5: Decision and Audit Governance (P0)

- decision-store persistence and reuse.
- append-only audit trail.

## EPIC-6: Context Compaction and Maintenance (P1)

- redundancy audits.
- weekly local maintenance report.
- PR creation only after approval.
