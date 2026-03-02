---
id: "029"
slug: "selective-test-execution-v1"
status: "in-progress"
created: "2026-03-02"
---

# Spec 029 — Selective Test Execution v1

## Problem

Current pre-push and CI test execution is effectively full-suite for most pushes, causing high latency and unnecessary compute for low-risk changes.

## Solution

Introduce a single source of truth test-scoping engine (`ai_engineering.policy.test_scope`) shared by local pre-push gates and CI tier jobs, with strict fail-closed fallbacks.

## Scope

### In Scope

- New `test_scope` policy engine + CLI.
- Git operations helpers for merge-base and changed file discovery.
- Pre-push gate scoped execution integration with shadow/enforce/off modes.
- CI scoped execution integration for unit/integration/e2e jobs.
- Mapping integrity checker script.
- Rule matrix and safety-net enforcement.
- Tests for scope engine and gate integration.
- Governance updates and decision/audit persistence.

### Out of Scope

- Dynamic ML-based test impact analysis.
- External exclusion-policy files.
- Coverage-gate behavior changes.

## Acceptance Criteria

1. `python -m ai_engineering.policy.test_scope` supports `--tier`, `--base-ref`, `--format` with deterministic output.
2. Pre-push supports shadow/enforce/off with fail-closed fallback and diagnostics.
3. CI tier jobs use scoped args while preserving full-suite safety triggers.
4. `scripts/check_test_mapping.py` blocks merge on mapping drift in either direction.
5. Docs-only changes never invoke pytest with empty args.
6. Main branch and high-risk triggers force full tier execution.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D029-001 | Rollout mode starts in shadow (`AI_ENG_TEST_SCOPE_MODE=shadow`) | De-risk migration while collecting scope diagnostics. |
| D029-002 | Module-level mapping rules | Lower maintenance with adequate precision. |
| D029-003 | Base-ref failures fail closed to full tier | Safety over speed when git ancestry is uncertain. |
