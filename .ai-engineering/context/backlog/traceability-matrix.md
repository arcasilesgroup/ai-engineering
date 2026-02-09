# Traceability Matrix

## Document Metadata

- Doc ID: BL-TRACE
- Owner: project-managed (backlog)
- Status: active
- Last reviewed: 2026-02-09
- Source of truth: `.ai-engineering/context/backlog/traceability-matrix.md`

## Purpose

Single mapping source from product intent to executable work and validation evidence.

## ID Convention

- Epic: `EPIC-*`
- Feature: `F-*`
- Story: `US-*`
- Task: `T-*`
- Implementation evidence: phase entries in `.ai-engineering/context/delivery/implementation.md`
- Verification/testing evidence: `.ai-engineering/context/delivery/verification.md` and `.ai-engineering/context/delivery/testing.md`

## End-to-End Mapping

| Epic | Feature | Story | Tasks | Delivery Evidence | Verification/Testing Evidence |
|---|---|---|---|---|---|
| EPIC-1 Ownership and State Foundation | F-1 Installer/Updater Ownership Safety | US-3 Ownership-Safe Updates | T-001, T-002 | Phase B, H, I entries in `delivery/implementation.md` | `delivery/verification.md` ownership safety matrix, `delivery/testing.md` integration layers |
| EPIC-2 Mandatory Local Enforcement | F-5 Mandatory Local Security and Quality Gates | US-1 Commanded Commit Flow | T-004, T-005, T-006 | Phase C entries in `delivery/implementation.md` | `delivery/verification.md` security failure scenarios, `delivery/testing.md` mandatory checks |
| EPIC-3 Command Contract Runtime | F-3 Command Flow Engine; F-4 /pr --only Continuation Policy | US-1, US-2 | T-007, T-008 | Phase D, K, N entries in `delivery/implementation.md` | `delivery/verification.md` command flow matrix, `delivery/testing.md` regression targets |
| EPIC-4 Remote Skills Trust Model | F-6 Remote Skills Lock and Cache | US-5 Readiness Assurance (partial) | T-012 | Phase E entries in `delivery/implementation.md` | `delivery/verification.md` connectivity/offline cases, `delivery/testing.md` security tests |
| EPIC-5 Decision and Audit Governance | F-7 Risk Decision Store and Audit Trail | US-4 Risk Decision Reuse | T-009, T-010 | Phase D, M entries in `delivery/implementation.md` | `delivery/verification.md` decision reuse criteria, `delivery/testing.md` regression targets |
| EPIC-6 Context Compaction and Maintenance | F-8 Maintenance Agent Reporting | (TBD story expansion) | T-013, T-014, T-015 | Phase E entries in `delivery/implementation.md` | `delivery/iteration.md` cadence and KPI contract |

## Drift Checks

- Every `US-*` must map to at least one `T-*`.
- Every completed `T-*` must map to at least one implementation entry.
- Every merged feature must map to verification/testing evidence.
