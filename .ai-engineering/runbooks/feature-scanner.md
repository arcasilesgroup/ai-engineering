---
name: feature-scanner
schedule: "0 14 * * *"
environment: worktree
layer: scanner
requires: [gh]
---

# Feature Scanner

## Prompt

Detect spec-vs-code gaps: features defined in specs that are not implemented, and acceptance criteria not covered by tests.

1. Read `.ai-engineering/context/specs/_active.md` to find the active spec.
2. Read the active spec's `spec.md` — extract acceptance criteria.
3. Read the active spec's `tasks.md` — extract unchecked tasks.
4. Search the codebase for evidence of each acceptance criterion being implemented.
5. For each gap found:
   - Check if a GitHub Issue already exists.
   - If not, create one with label `feature-gap`, `needs-triage`.
   - Title format: `[gap] <spec>: <criterion or task description>`
   - Priority: `p2-high` for acceptance criteria gaps, `p3-normal` for task gaps.

Also scan archived specs:
6. Read `context/specs/archive/` for recently completed specs (last 30 days).
7. Verify their acceptance criteria still pass (no regression).
8. Create issues for regressions with label `regression`, `p1-critical`.

## Context

- Uses: feature-gap skill (spec-vs-code mode + wiring mode).
- Reads: `.ai-engineering/context/specs/` for spec definitions.

## Safety

- Read-only mode: detect and create issues only.
- Do NOT modify specs or code.
- Maximum 15 issues per run.
- Skip gaps that already have open issues.
