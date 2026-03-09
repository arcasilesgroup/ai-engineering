---
spec: "041"
title: "Observe Quick Wins — Trends, Smart Actions, Self-Optimization"
size: S-M
pipeline: standard
created: "2026-03-09"
branch: "feat/041-observe-quick-wins"
---

# Spec 041 — Observe Quick Wins

## Problem

Health dashboard shows static scores without historical context — users can't tell if things are improving or degrading. Actions are hardcoded generic suggestions instead of targeted recommendations based on weakest components. AI dashboard lacks self-optimization hints despite having enough data to detect patterns.

## Solution

Three quick wins that close Tier C gaps with zero new event types:

1. **Trend history** — persist weekly health snapshots in `state/health-history.json`, show ↑↓→ direction indicators next to the overall score.
2. **Smart actions with score gain** — analyze weakest components, suggest specific remediation with estimated point impact.
3. **Self-optimization hints** — detect patterns from existing AI data (low decision reuse, high gate failures, token waste) and surface actionable suggestions.

## Scope

### In Scope
- `state/health-history.json` schema and persistence
- `save_health_snapshot()` and `load_health_history()` in `lib/signals.py`
- Direction indicator (↑↓→) in health dashboard header
- Dynamic smart actions in health dashboard (replace hardcoded actions)
- Self-optimization hints section in AI dashboard
- Tests for all new functions

### Out of Scope
- New event types (skill_invoked, agent_dispatch)
- External integrations (issue tracker for MTTR)
- Scan dimension breakdown (needs scan events first)

## Acceptance Criteria

1. `ai-eng observe health` shows `↑`, `↓`, or `→` next to the score when history exists
2. `ai-eng observe health` shows dynamic actions with estimated score gain (e.g., "+15 pts")
3. `ai-eng observe ai` shows Self-Optimization Hints section with pattern-based suggestions
4. `state/health-history.json` is created/appended on each `observe health` call
5. All existing tests pass, new tests cover the 3 features
6. `ruff check` + `ruff format` + `ty` clean

## Risks

1. **History file growth** — mitigated by keeping max 12 weekly entries (rolling window)
2. **Score gain estimates inaccurate** — mitigated by conservative estimates based on component weight

## Decisions

- D041-001: History stored as JSON array with weekly granularity (not daily — too noisy)
- D041-002: Direction computed from last 2 entries (current vs previous week)
- D041-003: Score gain estimated as `(100 - component_score) / num_components` (proportional impact)
