---
name: ai-evolve
version: 1.0.0
description: Use this skill to analyze framework telemetry and propose improvements. Reads audit-log, decision-store, and health-history to identify patterns, friction points, and optimization opportunities. Produces a self-improvement report with ranked proposals for human review.
mode: agent
tags: [self-improvement, telemetry, analysis, optimization, proposals]
---


# Evolve

## Purpose

Analyze framework telemetry across all event sources to identify patterns, friction points, and optimization opportunities. Produces a ranked self-improvement report for human review. This is the framework's introspection mechanism -- it looks at its own operational data and proposes changes, but never applies them autonomously.

Owned by the **observe agent**. Extends observe's dashboard capabilities with longitudinal pattern detection and improvement proposals.

## Trigger

- Command: `/ai:evolve`
- Context: periodic framework health review, post-spec retrospective, or when observe dashboards show declining trends.
- Recommended cadence: after every 3-5 completed specs, or when health score drops to YELLOW.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"evolve"}'` at skill start. Fail-open -- skip if ai-eng unavailable.

## Scope

**READ-ONLY.** This skill analyzes data and produces a markdown report with proposals. It never modifies code, configuration, governance artifacts, or state files. All proposals require human approval through the standard plan-then-execute workflow.

## Procedure

### Step 1 -- Load Data Sources

Collect telemetry from all framework event sources:

| Source | Collection Method | What It Provides |
|--------|-------------------|------------------|
| `state/audit-log.ndjson` | `ai-eng signals query` | Gate results, skill invocations, agent dispatches, scan scores, guard advisories, standard violations |
| `state/decision-store.json` | Direct read | Active/expired/resolved decisions, renewal chains, categories |
| `state/health-history.json` | Direct read | Weekly health scores, dimension breakdowns, trend direction |
| `git log` | `git log --oneline --since="60 days ago"` | Commit frequency, branch lifetimes, merge patterns, lead times |

If any source is unavailable or empty, note it as a data gap and continue with available sources. Never block the full analysis on a single missing source.

### Step 2 -- Apply Analysis Rules

Run each of the 12 pattern-detection rules against the collected data. Skip rules whose required data source is unavailable.

| # | Pattern | Data Source | Confidence |
|---|---------|-------------|------------|
| 1 | Gate check X fails >40% of runs | `gate_result` events in audit-log | HIGH |
| 2 | Skill X invoked <5 times while skill Y invoked >50 times | `skill_invoked` events in audit-log | HIGH |
| 3 | Same decision category appears 3+ times | decision-store categories | HIGH |
| 4 | Decision expired without review (TTL elapsed, no renewal) | decision-store expiry dates | HIGH |
| 5 | Health score declining for 3+ consecutive weeks | health-history weekly scores | MEDIUM |
| 6 | Noise ratio >50% (false positives / total findings) | observe team dashboard data | HIGH |
| 7 | Guard advisory ignored >60% of the time | `guard_advisory` events in audit-log | MEDIUM |
| 8 | Skill effectiveness score <50% | `skill_effectiveness` events in audit-log | MEDIUM |
| 9 | Agent escalates >30% of dispatched tasks to human | `agent_dispatched` events in audit-log | MEDIUM |
| 10 | DORA lead time increasing for 3+ consecutive weeks | `git log` merge timestamps | HIGH |
| 11 | Test coverage dropping for 3+ consecutive weeks | `scan_complete` events in audit-log | HIGH |
| 12 | Same standard violated >10 times in 30 days | `standard_violation` events in audit-log | HIGH |

For each triggered rule, record:
- **Pattern**: which rule fired
- **Evidence**: specific data points (counts, percentages, date ranges)
- **Severity**: HIGH (blocks delivery or degrades quality) or MEDIUM (friction or inefficiency)

### Step 3 -- Rank Findings

Sort triggered rules by **confidence x impact**:

1. **HIGH confidence + HIGH severity** -- address first (gate failures, coverage drops, standard violations)
2. **HIGH confidence + MEDIUM severity** -- address second (unused skills, repeated decisions)
3. **MEDIUM confidence + HIGH severity** -- investigate further before acting (health decline, escalation rate)
4. **MEDIUM confidence + MEDIUM severity** -- backlog candidates (advisory ignores, low effectiveness)

Within each tier, order by frequency (more frequent pattern = higher priority).

### Step 4 -- Generate Report

Write the self-improvement report to `state/self-improvement-report.md` with this structure:

```markdown
# Self-Improvement Report

**Generated**: <ISO-8601 timestamp>
**Data quality**: HIGH | MEDIUM | LOW
**Analysis window**: <start date> to <end date>
**Event count**: <total events analyzed>

## Data Gaps

- [List any unavailable sources or insufficient data]

## High Priority

### Finding 1: <pattern name>

- **Pattern**: <rule description>
- **Evidence**: <specific data — counts, percentages, examples>
- **Root cause**: <analysis of why this pattern exists>
- **Proposal**: <specific change to address the pattern>
- **Expected impact**: <what improves and by how much>
- **Effort**: LOW | MEDIUM | HIGH

[Repeat for each HIGH priority finding]

## Medium Priority

[Same structure as High Priority]

## Metrics Summary

| Metric | Current | Trend | Target |
|--------|---------|-------|--------|
| Gate pass rate | X% | up/down/stable | >90% |
| Skill utilization | X/Y active | - | All skills >5 invocations |
| Decision churn | X repeats | - | 0 repeats |
| Health score | X/100 | up/down/stable | >80 |
| DORA lead time | X days | up/down/stable | <7 days |
| Test coverage | X% | up/down/stable | >80% |

## Recommended Next Steps

1. [Highest-impact action with owner suggestion]
2. [Second action]
3. [Third action]
```

### Step 5 -- Emit Telemetry

After report generation:

```bash
ai-eng signals emit evolve_analysis_complete --actor=ai --detail='{"findings_high":<count>,"findings_medium":<count>,"data_quality":"<HIGH|MEDIUM|LOW>"}'
```

Fail-open -- if telemetry emission fails, the report is still valid.

## Data Quality Indicator

Assess data quality based on the analysis window:

- **HIGH** (>=500 events AND >=60 days of history): patterns are statistically representative, proposals are high-confidence.
- **MEDIUM** (>=100 events AND >=14 days of history): patterns are directionally accurate, proposals should be validated.
- **LOW** (<100 events OR <14 days of history): insufficient data for reliable pattern detection. Report findings as hypotheses, not conclusions.

Always display the data quality level prominently in the report header. When data quality is LOW, prepend each finding with a caveat about sample size.

## Security

- **READ-ONLY**: this skill reads state files and git history. It never modifies artifacts.
- **Proposals as text**: all improvement suggestions are written as markdown text in the report. No automated application of changes.
- **Human approval required**: proposals become actionable only when a human creates a spec or plan from them. The standard plan-then-execute workflow applies.
- **No secret access**: this skill does not read `.env`, credentials, or any sensitive configuration.

## When NOT to Use

- **Real-time monitoring** -- use `/ai:observe` for current-state dashboards.
- **Incident response** -- use `/ai:debug` for active issue diagnosis.
- **Decision making** -- evolve proposes, humans decide. Do not use evolve output as automatic justification for changes.

## Examples

### Example 1: Post-sprint retrospective

User says: `/ai:evolve` after completing 3 specs.

1. **Load**: 847 audit-log events, 12 decisions, 8 weeks of health history, 156 commits.
2. **Analyze**: Rule 1 fires (ruff format fails 52% of the time), Rule 3 fires (3 decisions about import ordering), Rule 10 fires (lead time grew from 2 days to 5 days over 4 weeks).
3. **Rank**: ruff failures (HIGH/HIGH), lead time increase (HIGH/HIGH), import decisions (HIGH/MEDIUM).
4. **Report**: proposes adding ruff format to pre-save hook, consolidating import ordering into a standard, and investigating branch review bottleneck.

### Example 2: Low data quality

User says: `/ai:evolve` on a new project with 2 weeks of history.

1. **Load**: 73 audit-log events, 2 decisions, 2 weeks of health history, 28 commits.
2. **Data quality**: LOW (<100 events). Report header shows caveat.
3. **Analyze**: Only rules with sufficient data fire. Most rules skipped due to insufficient sample.
4. **Report**: 1-2 tentative findings with explicit "insufficient data" caveats. Recommends re-running after 4 more weeks.

## References

- `.github/prompts/ai-dashboard.prompt.md` -- observability dashboards (current-state, not longitudinal).
- `state/audit-log.ndjson` -- primary event store.
- `state/decision-store.json` -- decision lifecycle data.
- `state/health-history.json` -- weekly health score history.
- `standards/framework/quality/core.md` -- quality thresholds referenced by analysis rules.
