# Audit Code

## Purpose

Execute a SonarQube-like quality gate assessment on the codebase. Evaluates coverage, duplication, reliability, security, maintainability, and complexity against defined thresholds. Produces a PASS/FAIL verdict with actionable findings.

## Trigger

- Command: agent invokes audit-code skill or user requests a quality audit.
- Context: pre-release review, quality gate check, periodic codebase health assessment.

## Procedure

1. **Run quality checks** — execute all mandatory gates.
   - `ruff format --check src/` → formatting compliance.
   - `ruff check src/` → lint violations.
   - `ty check src/` → type safety.
   - `pytest tests/ -v --cov=ai_engineering --cov-report=term-missing` → test results and coverage.
   - `pip-audit` → dependency vulnerabilities.
   - `gitleaks detect --no-banner` → secret detection.
   - `semgrep scan --config auto src/` → SAST findings.

2. **Evaluate thresholds** — compare results with quality contract.

   | Metric | Threshold | Severity if violated |
   |--------|-----------|---------------------|
   | Coverage (overall) | ≥80% | Blocker |
   | Coverage (governance-critical) | ≥90% | Blocker |
   | Duplicated lines | ≤3% | Critical |
   | Reliability issues (blocker/critical) | 0 | Blocker |
   | Security issues (blocker/critical) | 0 | Blocker |
   | Maintainability (critical debt) | 0 on changed code | Critical |
   | Cyclomatic complexity per function | ≤10 | Major |
   | Cognitive complexity per function | ≤15 | Major |
   | Function length | <50 lines | Major |

3. **Classify findings** — assign severity to each issue.
   - Blocker: merge blocked. Must fix.
   - Critical: merge blocked unless explicit risk acceptance.
   - Major: fix before merge unless owner approves.
   - Minor/Info: track, fix incrementally.

4. **Generate verdict** — PASS or FAIL.
   - **PASS**: no blocker or critical findings.
   - **FAIL**: one or more blocker or critical findings.

## Output Contract

- Quality report following `skills/quality/audit-report.md` template.
- PASS/FAIL verdict with summary.
- Metric values vs. thresholds.
- Finding list with severity, location, description, and remediation.
- Tool output evidence.

## Governance Notes

- Quality gate cannot be bypassed. FAIL verdict blocks merge.
- Thresholds come from `standards/framework/quality/core.md` — this skill IMPLEMENTS that contract.
- Risk acceptance for critical findings requires explicit entry in `state/decision-store.json`.
- All tools must be installed and operational. If missing, auto-remediate before proceeding.

## References

- `standards/framework/quality/core.md` — quality contract (thresholds and gates).
- `standards/framework/quality/python.md` — Python-specific checks.
- `skills/quality/audit-report.md` — report template.
- `agents/quality-auditor.md` — agent that executes this skill.
