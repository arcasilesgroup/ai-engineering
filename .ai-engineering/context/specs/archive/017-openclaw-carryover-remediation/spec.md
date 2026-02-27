---
id: "017"
slug: "openclaw-carryover-remediation"
status: "completed"
created: "2026-02-23"
---

# Spec-017: OpenClaw Adoption + Carryover Remediation (014/015)

## Problem

The repository has three related gaps that now need a single execution track:

1. OpenClaw-inspired operational patterns identified in audit are not yet implemented in ai-engineering runtime/CI.
2. Spec-015 still has unresolved blocking remediation work (tasks 5.6 to 5.10) around cross-OS CI, bypass resistance, and hook integrity.
3. Spec-014 has closure inconsistencies (unchecked verification tasks and in-progress status in `spec.md`) that must be reconciled before governance can claim end-to-end completion.

Keeping these as disconnected leftovers increases governance drift and weakens the framework contract (mandatory local enforcement, tamper resistance, and reproducible quality gates).

## Solution

Deliver one consolidated remediation spec with four tracks:

1. **OpenClaw operational adoption** (selected, framework-fit subset):
   - richer skill requirements model (`bins`, `anyBins`, `env`, `config`, `os`)
   - skill eligibility/status diagnostics with actionable missing requirements
   - CI workflow sanity checks and docs-only scope optimization
2. **Spec-015 carryover completion**:
   - implement tasks 5.6-5.10 (cross-OS CI matrix, coverage/duplication gate wiring, `--no-verify` bypass detection, hook hash verification, hook execution integration test)
3. **Spec-014 closure reconciliation**:
   - resolve skipped verification items where feasible
   - align `spec.md`/tasks/done state so closure is internally consistent
4. **Verification and contract alignment**:
   - keep content integrity green
   - preserve backward compatibility for Python-only consumers

## Scope

### In Scope

- Extend skill metadata schema and validation for multi-dimensional requirement gating.
- Add/extend CLI-visible skill status diagnostics in ai-engineering runtime.
- Add CI security parity and workflow sanity checks.
- Add docs-only scoping for expensive CI lanes without skipping baseline security checks.
- Implement and test Spec-015 tasks 5.6-5.10.
- Reconcile Spec-014 closure artifacts (`spec.md`, tasks, verification notes).
- Update related governance docs and references.

### Out of Scope

- Adopting OpenClaw Node/Bun/macOS/Android ecosystem-specific CI complexity.
- Replacing ai-engineering hook manager architecture with pre-commit framework model.
- Adding new VCS providers beyond GitHub/Azure DevOps already introduced in Spec-014.
- Any policy weakening via temporary gate disablement.

## Acceptance Criteria

1. Skill metadata supports `requires.bins`, `requires.anyBins`, `requires.env`, `requires.config`, and `os` with backward compatibility.
2. Skill diagnostics report eligibility and concrete missing requirements (tool/env/config/os) in a single command flow.
3. CI executes `gitleaks`, `semgrep`, and `pip-audit` for governed PR/push paths.
4. CI includes a workflow sanity lane (`actionlint` plus policy checks).
5. Docs-only changes skip heavyweight lanes while still running baseline security and integrity checks.
6. All Spec-015 tasks 5.6-5.10 are completed or formally risk-accepted with decision-store entries.
7. Spec-014 artifacts are reconciled: status, unchecked verification tasks, and closure notes are consistent.
8. `ai-eng validate` passes after all content updates.
9. Existing Python-only behavior remains stable for users not opting into new requirement fields.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| S017-001 | Bundle OpenClaw adoption with 014/015 carryovers in one remediation spec | Avoids fragmented governance and resolves related operational debt together |
| S017-002 | Adopt OpenClaw by pattern, not by direct copy | Preserve ai-engineering architecture and framework contract boundaries |
| S017-003 | Security and tamper-resistance carryovers take precedence over UX enhancements | Contract non-negotiables require enforcement reliability first |
