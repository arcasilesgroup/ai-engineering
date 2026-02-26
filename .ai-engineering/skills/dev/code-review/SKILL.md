---
name: code-review
description: "Deep code review covering security, quality, performance, and maintainability; use for PR reviews, pre-merge validation, or code audits."
version: 1.0.0
category: dev
tags: [review, quality, patterns, best-practices]
metadata:
  ai-engineering:
    scope: read-only
    token_estimate: 800
---

# Code Review

## Purpose

Deep code review skill covering security, quality, performance, and maintainability. Provides structured, actionable feedback that improves code quality and prevents issues before merge.

## Trigger

- Command: agent invokes code-review skill or user requests a review.
- Context: PR review, pre-merge validation, code audit.

## When NOT to Use

- **Architecture-level analysis** (dependency graphs, coupling metrics, drift detection) — use `review:architecture` instead.
- **Dedicated security audit** (OWASP assessment, secret scanning, SAST tooling) — use `review:security` instead.
- **Quality gate enforcement** (coverage thresholds, complexity metrics, PASS/FAIL verdict) — use `quality:audit-code` instead.
- **Refactoring** (improving code structure without changing behavior) — use `dev:refactor` instead.

## Procedure

1. **Understand context** — read the PR description, linked spec/task, and changed files.
   - What problem is being solved?
   - What is the expected behavior after the change?

2. **Review security** — check for vulnerabilities.
   - No hardcoded secrets, tokens, or credentials.
   - Input validation on all external inputs.
   - No SQL injection, command injection, or path traversal risks.
   - Dependency versions are pinned and audited.

3. **Review quality** — check code structure and patterns.
   - Functions are small (<50 lines) and single-responsibility.
   - Naming is clear and consistent.
   - Type hints on all public APIs.
   - Google-style docstrings on public functions.
   - No code duplication (rule of three).
   - Error handling is explicit — no bare `except`, no silent failures.

4. **Review performance** — check for obvious bottlenecks.
   - No unnecessary I/O in loops.
   - Appropriate use of generators for large data.
   - No blocking calls in async context.

5. **Review maintainability** — check long-term health.
   - Changes are well-tested (coverage on changed code 100%).
   - API contracts are stable — breaking changes documented.
   - No unnecessary complexity (YAGNI, KISS).
   - Dependencies are minimal and justified.

6. **Provide feedback** — structured review comments.
   - Severity: blocker / critical / major / minor / info.
   - Each comment includes: what's wrong, why it matters, how to fix.
   - Positive feedback on good patterns (not only criticism).
   - **Code Suggestions**: Use exact `startLine:endLine:filepath` block quoting when referencing existing code. When suggesting edits, ALWAYS provide minimal unchanged context using `// ... existing code ...` limits. DO NOT suggest rewriting entire files.

## Output Contract

- Structured review with severity-tagged comments.
- Verdict: APPROVE / REQUEST CHANGES / COMMENT.
- Summary: key findings, risks, and recommendations.

## Governance Notes

- Blocker and critical findings must block merge.
- Security findings are always at least critical severity.
- Follow severity policy from `standards/framework/quality/core.md`.
- Never approve code with failing quality gates.

## References

- `standards/framework/quality/core.md` — severity policy, quality gates, and stack-specific checks.
- `standards/framework/stacks/python.md` — code patterns.
- `skills/review/security/SKILL.md` — detailed security review procedure.
- `skills/dev/test-strategy/SKILL.md` — test assessment criteria.
- `skills/review/performance/SKILL.md` — performance evaluation procedure.
- `agents/principal-engineer.md` — agent that performs deep reviews.
- `agents/code-simplifier.md` — agent that uses code quality criteria.
- `skills/docs/explain/SKILL.md` — explain findings and concepts to the author.
