# Audit Report

## Purpose

Standardized report template for quality audit results. Produces a structured, machine-readable report with PASS/FAIL verdict, metric values, and actionable findings.

## Trigger

- Command: generated as output of `skills/quality/audit-code.md` execution.
- Context: quality gate check completion, quality review summary.

## Procedure

1. **Populate header** — fill report metadata.
2. **Record metrics** — tool output values vs. thresholds.
3. **List findings** — severity-tagged issues with remediation.
4. **Determine verdict** — PASS if no blocker/critical, FAIL otherwise.
5. **Generate report** — following the template below.

## Report Template

```markdown
# Quality Audit Report

## Summary

| Field | Value |
|-------|-------|
| Date | YYYY-MM-DD |
| Spec | spec-NNN |
| Scope | <files or modules audited> |
| Verdict | **PASS** / **FAIL** |

## Metrics

| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|
| Coverage (overall) | XX% | ≥80% | ✓ / ✗ |
| Coverage (governance-critical) | XX% | ≥90% | ✓ / ✗ |
| Duplicated lines | XX% | ≤3% | ✓ / ✗ |
| Blocker issues | N | 0 | ✓ / ✗ |
| Critical issues | N | 0 | ✓ / ✗ |
| Major issues | N | — | ⚠ |
| Cyclomatic complexity (max) | N | ≤10 | ✓ / ✗ |
| Cognitive complexity (max) | N | ≤15 | ✓ / ✗ |

## Findings

### Blockers (N)

| # | File | Line | Description | Remediation |
|---|------|------|-------------|-------------|
| 1 | path/file.py | LN | description | how to fix |

### Critical (N)

| # | File | Line | Description | Remediation |
|---|------|------|-------------|-------------|

### Major (N)

| # | File | Line | Description | Remediation |
|---|------|------|-------------|-------------|

### Minor/Info (N)

<summary or count only>

## Tool Evidence

- ruff format: PASS/FAIL
- ruff check: PASS/FAIL (N issues)
- ty check: PASS/FAIL (N errors)
- pytest: PASS/FAIL (N passed, N failed)
- pip-audit: PASS/FAIL (N vulnerabilities)
- gitleaks: PASS/FAIL (N findings)
- semgrep: PASS/FAIL (N findings)

## Recommendations

1. Priority action items.
2. Improvement opportunities.
3. Tech debt notes.
```

## Output Contract

- Markdown report following the template above.
- Verdict clearly stated (PASS/FAIL).
- All metrics populated with actual values.
- Findings include file, line, description, and remediation for blocker/critical/major.
- Tool evidence section shows raw pass/fail for each mandatory check.

## Governance Notes

- Reports must be factual — no optimistic interpretation of borderline results.
- FAIL verdict means merge is blocked. No negotiation in the report itself.
- Risk acceptance for specific findings must be documented separately in `state/decision-store.json`, not in the report.
- Reports are ephemeral artifacts — not persisted in governance content unless explicitly requested.

## References

- `skills/quality/audit-code.md` — the skill that produces this report.
- `standards/framework/quality/core.md` — quality contract and thresholds.
- `agents/quality-auditor.md` — agent that generates these reports.
