# Runbook Index

Runbooks are framework-managed operational procedures that live under
[`.ai-engineering/runbooks/`](../runbooks/). Each runs on a fixed cadence
(daily or weekly) on the registered scheduler hosts; `intake` runbooks feed the
issue/spec pipeline, `operational` runbooks keep the repo healthy (deps, docs,
security, drift). This index ties every runbook to its type, cadence, and
purpose so none is operationally orphaned; the runbook files remain the single
source of truth, and this table is a rebuildable discovery aid.

## Intake runbooks

| Runbook | Cadence | What it does |
| --- | --- | --- |
| [`triage`](../runbooks/triage.md) | daily | Scan open issues and backlog, classify by type and priority, detect duplicates, discard noise, label triaged items for refinement. |
| [`refine`](../runbooks/refine.md) | daily | Take triaged issues, gather codebase and provider context, draft acceptance criteria, and propose a spec outline, marking handoff-ai-eng when ready. |

## Operational runbooks

| Runbook | Cadence | What it does |
| --- | --- | --- |
| [`feature-scanner`](../runbooks/feature-scanner.md) | daily | Scan the last 24h of commits and PRs against spec history for unimplemented features, uncovered acceptance criteria, and spec-vs-code regressions. |
| [`stale-issues`](../runbooks/stale-issues.md) | daily | Label issues idle for 14+ days and auto-close after 21 days with a grace period. |
| [`dependency-health`](../runbooks/dependency-health.md) | weekly | Scan dependencies for outdated versions, known CVEs, and license issues; owns all dependency-graph vulnerability findings. |
| [`code-quality`](../runbooks/code-quality.md) | weekly | Detect complexity hotspots, duplication above threshold, cognitive-complexity violations, and tech-debt accumulation. |
| [`consolidate`](../runbooks/consolidate.md) | weekly | Group related work items into consolidated tasks ready for brainstorm. |
| [`security-scan`](../runbooks/security-scan.md) | weekly | Scan for secrets, OWASP/SAST code patterns, and compliance gaps; dependency CVEs are owned by dependency-health. |
| [`docs-freshness`](../runbooks/docs-freshness.md) | weekly | Detect stale documentation, missing coverage for recent features, and doc-vs-code drift. |
| [`performance`](../runbooks/performance.md) | weekly | Detect performance regressions, test-suite slowdowns, build-time increases, and bundle-size growth. |
| [`governance-drift`](../runbooks/governance-drift.md) | weekly | Verify mirror sync, quality-gate config, hook integrity, manifest consistency, and template-vs-installed drift. |
| [`architecture-drift`](../runbooks/architecture-drift.md) | weekly | Compare the codebase against solution-intent and the constitution for layer violations and undocumented structural changes. |
| [`wiring-scanner`](../runbooks/wiring-scanner.md) | weekly | Detect implemented but disconnected code: functions, modules, or exports wired to no entry point, route, command, or consumer. |
| [`work-item-audit`](../runbooks/work-item-audit.md) | weekly | Audit non-functional work items against repo reality, close invalid noise, and rewrite mixed items before consolidation. |
