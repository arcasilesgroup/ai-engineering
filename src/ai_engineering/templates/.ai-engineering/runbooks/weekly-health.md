# Runbook: Weekly Health

## Purpose

Comprehensive weekly framework health check: tool availability, content integrity, and operational readiness.

## Schedule

Weekly (Monday 9AM UTC) via `ai-eng-weekly-health` agentic workflow.

## Procedure

1. **Framework health**: Run `ai-eng doctor --json` to verify all tools, hooks, and dependencies are operational.
2. **Content integrity**: Run `ai-eng validate --json` to check all 7 validation categories (skills, agents, specs, state, mirrors, standards, contracts).
3. **DORA metrics**: Collect deployment frequency, lead time, change failure rate, and MTTR from git history and audit log.
4. **Report**: Create a GitHub issue summarizing the health status.

## Health Categories

| Category | Tool | What it checks |
|----------|------|----------------|
| Tool availability | `ai-eng doctor` | ruff, gitleaks, uv, gh, semgrep, pip-audit |
| Content integrity | `ai-eng validate` | File existence, frontmatter, cross-references |
| Hook installation | `ai-eng doctor` | Pre-commit, pre-push hooks in place |
| Mirror sync | `ai-eng validate` | .claude/, .github/, .agents/ match canonical |

## Output

GitHub issue with:
- Title: `chore(health): weekly health report YYYY-MM-DD`
- Body: health status summary, any failures, recommendations
- Labels: `automation`, `health-report`
