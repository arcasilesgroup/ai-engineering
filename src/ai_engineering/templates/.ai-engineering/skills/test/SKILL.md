---
name: test
description: "Unified testing skill: plan test strategy, write and run tests, detect coverage gaps. Modes: plan | run | gap."
metadata:
  version: 2.0.0
  tags: [testing, coverage, strategy, test-plan, test-run, test-gap]
  ai-engineering:
    scope: read-write
    token_estimate: 1000
---

# Test

## Purpose

Unified testing skill covering test strategy design, test execution, and coverage gap detection. Consolidates test-plan, test-run, and test-gap into a single skill with modes.

## Trigger

- Command: `/ai:test [plan|run|gap]`
- Context: need to plan testing strategy, write/run tests, or find coverage gaps.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"test"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Modes

### plan — Design test strategy
Design test strategy with tier assignments (unit, integration, E2E), coverage targets, acceptance criteria, and risk-based prioritization.

### run — Write and execute tests
Write tests following stack standards and execute them. Supports all test frameworks across supported stacks.

### gap — Detect coverage gaps
Map untested critical paths. For each capability/requirement, verify corresponding test exists. Classify as covered, partial, or uncovered.

## Procedure

### Mode: plan
1. Read spec/requirements and existing test suite.
2. Classify test needs by tier (unit >= 80%, integration >= 15%, E2E critical paths).
3. Design test matrix with scope, inputs, expected outputs.
4. Identify risk-based priorities (security-critical paths first).
5. Output: test strategy document.

### Mode: run
1. Detect test framework from stack (pytest, vitest, jest, dotnet test, cargo test).
2. Write tests following stack standards and patterns.
3. Execute tests: `uv run pytest` / `vitest run` / `dotnet test` / etc.
4. Report results with pass/fail counts and coverage.

### Mode: gap
1. Read spec requirements and acceptance criteria.
2. Map each requirement to existing tests.
3. Classify: covered / partial / uncovered.
4. Prioritize uncovered items by risk.
5. Output: coverage gap report with remediation priorities.
