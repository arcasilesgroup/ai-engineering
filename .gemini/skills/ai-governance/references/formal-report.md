# `--report` Formal Report Format

The `--report` flag can combine with any mode (e.g., `/ai-governance integrity --report`). Without a mode, it defaults to `compliance`.

## Output skeleton

```markdown
# Governance Report: [mode]

## Score: N/100

## Verdict: PASS (>=90) | WARN (>=70) | FAIL (<70)

## Findings

| # | Severity | Category | Description | Location | Remediation |

## Gate Check

- Blocker: N (threshold: 0)
- Critical: N (threshold: 0)
```

## Scoring

Start at 100. Deduct: blocker -25, critical -15, major -5, minor -1. Floor at 0.
