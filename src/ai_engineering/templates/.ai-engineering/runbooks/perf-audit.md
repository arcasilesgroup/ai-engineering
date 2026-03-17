# Runbook: Performance Audit

## Purpose

Weekly code quality scan: duplication analysis, cyclomatic complexity check, and artifact generation for trend tracking.

## Schedule

Weekly (Sunday 3AM UTC) via `ai-eng-perf-audit` agentic workflow.

## Procedure

1. **Duplication analysis**: Run `python -m ai_engineering.policy.duplication --path src/ai_engineering --threshold 3` to find duplicated code blocks exceeding 3%.
2. **Complexity check**: Run `ruff check src/ --select C901 --output-format json` to find functions with cyclomatic complexity > 10.
3. **Generate reports**: Save complexity findings to `complexity-report.json`.
4. **Upload artifacts**: Store reports as workflow artifacts with 30-day retention.
5. **Trend comparison**: Compare current findings against previous run (if available).

## Metrics Tracked

| Metric | Threshold | Tool |
|--------|-----------|------|
| Code duplication | <=3% | `ai_engineering.policy.duplication` |
| Cyclomatic complexity | <=10 per function | `ruff --select C901` |
| Cognitive complexity | <=15 per function | `ruff --select C901` |

## Output

Workflow artifacts (JSON reports) for trend analysis. No issue created unless thresholds are exceeded.
