---
name: audit-code
description: "SonarQube-like quality gate assessment; use before merge or release to evaluate coverage, duplication, complexity, and security."
version: 1.0.0
category: quality
tags: [quality, coverage, complexity, duplication, gate]
metadata:
  ai-engineering:
    requires:
      bins: [ruff, ty]
    scope: read-only
    token_estimate: 1145
---

# Audit Code

## Purpose

Execute a SonarQube-like quality gate assessment on the codebase. Evaluates coverage, duplication, reliability, security, maintainability, and complexity against defined thresholds. Produces a PASS/FAIL verdict with actionable findings.

## Trigger

- Command: agent invokes audit-code skill or user requests a quality audit.
- Context: pre-release review, quality gate check, periodic codebase health assessment.

## When NOT to Use

- **Security-focused assessment** (OWASP, secrets, injection analysis) — use `review:security` instead. Audit-code runs basic security gates but does not perform deep security review.
- **PR-level code review** (actionable feedback per file/function) — use `dev:code-review` instead.
- **Governance content validation** (cross-references, mirrors, counters) — use `govern:integrity-check` instead.
- **Test coverage strategy** (what to test, how to test) — use `dev:test-strategy` instead. Audit-code measures coverage; test-strategy designs it.

## Procedure

1. **Detect active stacks** — read `install-manifest.json` for installed stacks.
   - Determine which quality checks to run based on active stacks.
   - Always run common security checks (gitleaks, semgrep).

2. **Run quality checks** — execute mandatory gates per active stack.

   **Common (all stacks)**:
   - `gitleaks detect --no-banner` → secret detection.
   - `semgrep scan --config auto` → SAST findings.

   **Python** (when active):
   - `ruff format --check src/` → formatting compliance.
   - `ruff check src/` → lint violations.
   - `ty check src/` → type safety.
   - `pytest tests/ -v --cov --cov-report=term-missing` → test results and coverage.
   - `pip-audit` → dependency vulnerabilities.

   **`.NET`** (when active):
   - `dotnet format --verify-no-changes` → formatting compliance.
   - `dotnet build --no-restore` → compilation.
   - `dotnet test --no-build` → test results with coverage.
   - `dotnet list package --vulnerable` → dependency vulnerabilities.

   **Next.js/TypeScript** (when active):
   - `prettier --check .` → formatting compliance.
   - `eslint .` → lint violations.
   - `tsc --noEmit` → type safety.
   - `vitest run --coverage` → test results and coverage.
   - `npm audit` → dependency vulnerabilities.

   **Optional: Sonar gate** (when configured):
   - Invoke `dev/sonar-gate/SKILL.md` procedure.
   - Silent skip if `SONAR_TOKEN` not configured — never blocks audit.
   - If configured: run `sonar-scanner` with `qualitygate.wait=true`.
   - Report Sonar gate as PASS/FAIL/SKIP alongside other tool evidence.

3. **Evaluate thresholds** — compare results with quality contract.

   | Metric                                | Threshold         | Severity if violated |
   | ------------------------------------- | ----------------- | -------------------- |
   | Coverage (overall)                    | 90%               | Blocker              |
   | Coverage (governance-critical)        | 100%              | Blocker              |
   | Duplicated lines                      | ≤3%               | Critical             |
   | Reliability issues (blocker/critical) | 0                 | Blocker              |
   | Security issues (blocker/critical)    | 0                 | Blocker              |
   | Maintainability (critical debt)       | 0 on changed code | Critical             |
   | Cyclomatic complexity per function    | ≤10               | Major                |
   | Cognitive complexity per function     | ≤15               | Major                |
   | Function length                       | <50 lines         | Major                |

4. **Classify findings** — assign severity to each issue.
   - Blocker: merge blocked. Must fix.
   - Critical: merge blocked unless explicit risk acceptance.
   - Major: fix before merge unless owner approves.
   - Minor/Info: track, fix incrementally.

5. **Generate verdict** — PASS or FAIL.
   - **PASS**: no blocker or critical findings.
   - **FAIL**: one or more blocker or critical findings.

## Output Contract

Produce this markdown structure directly as audit output:

```markdown
# Quality Audit Report

## Summary

| Field   | Value                   |
| ------- | ----------------------- |
| Date    | YYYY-MM-DD              |
| Spec    | spec-NNN                |
| Scope   | <files/modules audited> |
| Verdict | **PASS** / **FAIL**     |

## Metrics

| Metric                         | Value | Threshold | Status |
| ------------------------------ | ----- | --------- | ------ |
| Coverage (overall)             | XX%   | 90%       | ✓ / ✗  |
| Coverage (governance-critical) | XX%   | 100%      | ✓ / ✗  |
| Duplicated lines               | XX%   | ≤3%       | ✓ / ✗  |
| Blocker issues                 | N     | 0         | ✓ / ✗  |
| Critical issues                | N     | 0         | ✓ / ✗  |
| Major issues                   | N     | —         | ⚠      |
| Cyclomatic complexity (max)    | N     | ≤10       | ✓ / ✗  |
| Cognitive complexity (max)     | N     | ≤15       | ✓ / ✗  |

## Findings

### Blockers (N)

| #   | File | Line | Description | Remediation |
| --- | ---- | ---- | ----------- | ----------- |

### Critical (N)

| #   | File | Line | Description | Remediation |
| --- | ---- | ---- | ----------- | ----------- |

### Major (N)

| #   | File | Line | Description | Remediation |
| --- | ---- | ---- | ----------- | ----------- |

### Minor/Info (N)

<summary or count>

## Tool Evidence

- ruff format: PASS/FAIL
- ruff check: PASS/FAIL
- ty check: PASS/FAIL
- pytest: PASS/FAIL
- pip-audit: PASS/FAIL
- gitleaks: PASS/FAIL
- semgrep: PASS/FAIL

## Recommendations

1. Priority actions.
2. Improvement opportunities.
3. Tech debt notes.
```

## Governance Notes

- Quality gate cannot be bypassed. FAIL verdict blocks merge.
- Thresholds come from `standards/framework/quality/core.md` — this skill IMPLEMENTS that contract.
- Risk acceptance for critical findings requires explicit entry in `state/decision-store.json`.
- All tools must be installed and operational. If missing, auto-remediate before proceeding.

## References

- `standards/framework/quality/core.md` — quality contract (thresholds, gates, and stack-specific checks).
- `skills/dev/sonar-gate/SKILL.md` — optional Sonar quality gate (invoked when configured).
- `agents/quality-auditor.md` — agent that executes this skill.
