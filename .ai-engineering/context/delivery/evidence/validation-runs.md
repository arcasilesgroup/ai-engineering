# Validation Runs

## Document Metadata

- Doc ID: DEL-EVID-VALIDATION
- Owner: project-managed (delivery/evidence)
- Status: active
- Last reviewed: 2026-02-09
- Source of truth: `.ai-engineering/context/delivery/evidence/validation-runs.md`

## Purpose

Record concrete validation evidence with links or command outputs for auditable delivery quality.

## Required Gate Set

- `unit`
- `integration`
- `e2e`
- `ruff`
- `ty`
- `gitleaks`
- `semgrep`
- `pip-audit`

## Entry Template

```text
Date:
Scope:
Environment:
Commands:
Results:
Evidence links:
Notes:
```

## Latest Entries

### 2026-02-09 - Docs Reorganization (Phase O/P)

- Scope: backlog/delivery documentation hardening and structure reorganization.
- Environment: local repository documentation-only update.
- Commands: documentation consistency review and traceability linkage checks.
- Results: pass (no code/runtime behavior changes in this block).
- Evidence links:
  - `.ai-engineering/context/backlog/traceability-matrix.md`
  - `.ai-engineering/context/backlog/tasks.md`
  - `.ai-engineering/context/delivery/planning.md`
- Notes: full runtime quality/security gates continue to be required for code-changing phases.
