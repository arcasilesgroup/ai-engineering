---
name: quality
description: "Unified quality assessment: coverage, complexity, duplication, code review. Modes: code | sonar | review | docs."
metadata:
  version: 2.0.0
  tags: [quality, coverage, complexity, duplication, review, sonar]
  ai-engineering:
    scope: read-write
    token_estimate: 1000
---

# Quality

## Purpose

Unified quality assessment covering code metrics, Sonar integration, code review, and documentation quality audit. Consolidates audit, sonar, code-review, and docs-audit.

## Trigger

- Command: `/ai:scan quality` or `/ai:quality [code|sonar|review|docs]`
- Context: quality gate, code review, pre-release quality check.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"quality"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Modes

### code — Quality metrics
Coverage (>=80%), complexity (cyclomatic <=10, cognitive <=15), duplication (<=3%), lint issues.

### sonar — SonarCloud gate
Run Sonar quality gate locally. Advisory mode (non-blocking if unconfigured).

### review — Deep code review
Multi-dimension code review: security, patterns, performance, maintainability, naming, tests.

### docs — Documentation audit
Documentation health: coverage, cross-reference validity, style consistency.

## Procedure

1. **Collect metrics** -- `ai-eng gate pre-push` for deterministic checks.
2. **Analyze** -- LLM interprets findings in context.
3. **Prioritize** -- rank by impact and actionability.
4. **Report** -- uniform scan output contract with score 0-100.
