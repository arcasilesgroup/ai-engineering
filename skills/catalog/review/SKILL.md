---
name: review
description: Use when code changes need human-quality judgment — PR reviews, file reviews, diff analysis, architecture feedback. For evidence-backed gates use /ai-verify instead.
effort: high
tier: core
capabilities: [tool_use]
---

# /ai-review

Code review with parallel specialist agents. Default mode runs the full
specialist roster through 3 macro-agents; `--full` runs one agent per
specialist with maximum context isolation.

## Specialist roster

- `reviewer-architecture` — solution-intent alignment, layer violations
- `reviewer-correctness` — does the code actually do what the PR claims
- `reviewer-security` — vulnerabilities, exploits, hardening (OWASP/CWE)
- `reviewer-performance` — bottlenecks, N+1, complexity hot spots
- `reviewer-maintainability` — readability, naming, SOLID, duplication
- `reviewer-testing` — test coverage, mocking patterns, regression risk
- `reviewer-frontend` — React, hooks, a11y (conditional)
- `reviewer-backend` — APIs, persistence, background processing
- `reviewer-compatibility` — breaking changes vs default branch

## Process

1. Pre-review context exploration (read beyond the diff).
2. Specialists run in parallel, isolated contexts.
3. Findings validated by an adversarial validator (read-only attempt to
   disprove each finding).
4. Aggregated report with severity + actionable suggestions.

## Difference vs `/ai-verify`

- `review` = human-quality judgment (will this break in 3 months?)
- `verify` = deterministic evidence (do the gates pass right now?)

## Common mistakes

- Approving without reading the production code path
- Bikeshedding style when the architecture has a real problem
- Treating all findings equal regardless of severity
