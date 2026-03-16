---
description: "Use this skill for operational automation: execute runbooks on demand,"
mode: "agent"
---


# Ops

## Purpose

Operational automation for the ai-engineering framework. Execute runbooks on demand, respond to incidents (gate failures, CI breaks, security findings), and produce operational health dashboards. The single entry point for all operational concerns that are not code delivery (handled by ship) or code analysis (handled by verify).

## Trigger

- Command: `/ai:ops [run <runbook>|incident|status]`
- Context: runbook execution, incident response, operational health check, or toil reduction.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"ops"}'` at skill start. Fail-open -- skip if ai-eng unavailable.

## Modes

### run -- Execute a runbook on demand

What: Execute a specific runbook from `.ai-engineering/runbooks/`, following its prompt and delegating to appropriate agents.
When: User requests a runbook execution, or a scheduled trigger fires.

### incident -- Respond to operational failures

What: Diagnose a failure (gate failure, CI break, security finding), classify severity, execute recovery runbook.
When: A gate fails, CI breaks, or a security finding surfaces.

### status -- Operational health dashboard

What: Aggregate operational signals into a health summary with actionable recommendations.
When: User wants visibility into operational health, or as part of a periodic check.

## Shared Rules (Canonical)

Use these rules as the single source of truth for operational behavior shared by skill and agent.

- **OPS-R1 (Runbook-first execution):** Every operational action maps to a runbook. If no runbook exists for the requested action, report the gap -- do not improvise.
- **OPS-R2 (Delegation discipline):** Never perform work outside operational scope. Delegate analysis to verify, code fixes to build, delivery to ship. The operate agent orchestrates; it does not implement.
- **OPS-R3 (Safety limit enforcement):** Respect every per-runbook safety constraint (max-issues, max-lines, max-attempts, no-bypass). Never override safety limits.
- **OPS-R4 (Audit trail):** Record every runbook execution and incident response in `state/audit-log.ndjson` with structured fields: `type`, `runbook`, `status`, `timestamp`, `detail`.
- **OPS-R5 (Blameless incident management):** Incident reports focus on what happened, why, and how to prevent recurrence. Never assign blame to individuals or agents.
- **OPS-B1 (Operational boundary):** Never modify source code, standards, skills, or agent definitions. Read-write scope is limited to GitHub Issues, labels, comments, and `state/audit-log.ndjson`.

## Procedure

### Mode: run

1. **Identify target runbook** -- match the user's request to a runbook in `.ai-engineering/runbooks/` (5 runbooks: `code-simplifier`, `dependency-upgrade`, `governance-drift-repair`, `incident-response`, `security-incident`).
2. **Read runbook frontmatter** -- extract `schedule`, `layer`, `requires`, `environment`.
3. **Verify required tools** -- for each entry in `requires`, confirm available on PATH. If missing, abort with `ai-eng doctor --fix-tools` guidance.
4. **Execute runbook prompt** -- read the `## Prompt` section and follow each numbered step in order.
5. **Delegate to agents** -- when the runbook requires work outside operational scope:
   - Scanning/analysis -> invoke verify agent (via `/ai:verify`)
   - Code fixes -> invoke build agent (via `/ai:build`)
   - Commits/PRs/releases -> invoke ship agent (via `/ai:commit`, `/ai:pr`)
   - Metrics/dashboards -> invoke observe agent (via `/ai:observe`)
6. **Record execution** -- emit to `state/audit-log.ndjson`:
   ```json
   {"type": "runbook-execution", "runbook": "<name>", "status": "success|failure|partial", "findings": <N>, "actions": <N>, "timestamp": "<ISO-8601>"}
   ```
7. **Enforce safety limits** -- per-runbook constraints (max-issues, max-lines, max-attempts) are non-negotiable. Never use `--no-verify`.

### Mode: incident

1. **Classify the incident** -- determine type from the error context:

   | Type | Indicators | Applicable Runbook |
   |------|-----------|-------------------|
   | Gate failure | Pre-commit/pre-push hook error (ruff, ty, gitleaks, pytest) | `incident-response.md` |
   | CI break | GitHub Actions workflow failure | `incident-response.md` |
   | Security finding | Vulnerability, secret leak, CVE | `security-incident.md` + build |
   | Dependency vuln | pip-audit finding, outdated package with CVE | `dependency-upgrade.md` |

2. **Gather context** -- error output, recent changes (`git log -5 --oneline`), affected files (`git diff --name-only`), existing scan reports.
3. **Determine severity**:
   - **P1 Critical**: security vulnerability actively exploitable, secret leaked to public.
   - **P2 High**: CI blocked on main/default branch, gate failure blocking all commits.
   - **P3 Normal**: CI failure on feature branch, non-critical gate warning.
4. **Execute recovery** -- run the applicable runbook from the classification table. Delegate fixes to build agent, never fix code directly.
5. **Track attempts** -- log each attempt in audit-log, adjust strategy per attempt. After 3 failed attempts: STOP and escalate.
6. **Escalate if unresolved** -- produce an incident report:
   ```markdown
   ## Incident Report
   - **Type**: <classification>
   - **Severity**: <P1|P2|P3>
   - **Attempts**: 3/3 exhausted
   - **What was tried**: <summary of each attempt>
   - **Root cause (suspected)**: <analysis>
   - **Affected scope**: <files, PRs, issues>
   - **Recommended action**: <what the human should do>
   ```
7. **Post-incident record** -- emit to audit-log:
   ```json
   {"type": "incident", "classification": "<type>", "severity": "<P1|P2|P3>", "resolution": "resolved|escalated", "attempts": <N>, "timestamp": "<ISO-8601>"}
   ```

### Mode: status

1. **Runbook execution health** -- read `state/audit-log.ndjson`, filter for `type: "runbook-execution"` events in the last 7 days:
   - Compute success rate (successes / total).
   - Identify most-failed runbook.
   - Flag runbooks that have not run within their expected schedule.
2. **Decision store health** -- read `state/decision-store.json`:
   - Count expired decisions (where `expires` < current date).
   - Count decisions pending renewal (expiring within 7 days).
   - Count unresolved risk acceptances.
3. **CI pipeline status** -- if `gh` is available:
   - `gh run list --limit 10 --json status,conclusion,name,createdAt`
   - Compute pass rate from recent runs.
   - Identify failing workflows.
4. **Issue backlog health** -- if `gh` is available:
   - Count `needs-triage` issues (backlog debt).
   - Count `agent-blocked` issues (stalled automation).
   - Count stale issues (no activity in 30+ days).
5. **Produce operational health summary** -- render markdown dashboard with semaphore (GREEN/YELLOW/RED) and top 3 recommended operational actions ranked by impact.

## Preconditions

- **Required**: `gh` on PATH. Abort with `ai-eng doctor --fix-tools` if missing.
- **Optional**: `uv`, `ruff`, `ty`, `gitleaks`, `semgrep` -- verified per-runbook at execution time.

## Post-condition

- Runbook result recorded in audit-log. Incident documented. Status dashboard rendered.
- All safety limits respected, no source code modified.

## References

- `.github/agents/operate.agent.md` -- operate agent behavioral contract
- `.github/prompts/ai-cleanup.prompt.md` -- repository hygiene (shared with plan)
- `standards/framework/core.md` -- governance structure and lifecycle
