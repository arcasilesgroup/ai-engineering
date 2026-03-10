---
name: observe
description: "Generate observability dashboards across 5 modes (engineer, team, AI, DORA, health) for 4 audience tiers."
metadata:
  version: 1.0.0
  tags: [observability, metrics, dora, dashboard, analytics]
  ai-engineering:
    scope: read-only
    token_estimate: 1200
---

# Observe

## Purpose

Generate observability dashboards and metrics for engineering teams, framework maintainers, and AI assistants. Computes DORA metrics, health scores, and actionable recommendations from the single event store.

## Trigger

- Command: `/ai:observe [engineer|team|ai|dora|health]`
- Context: need visibility into code quality, delivery velocity, or framework health.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"observe"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## Modes

### engineer — Developer metrics

What: code quality, security posture, test confidence, delivery velocity, gate health.
How: `ai-eng observe engineer` -> LLM interprets and adds recommendations.

### team — Framework maintainer metrics

What: framework health, skill usage, agent dispatch, decision store, token economy, adoption.
How: `ai-eng observe team` -> LLM interprets and identifies trends.

### ai — AI self-awareness metrics

What: context utilization, decision continuity, session recovery, escalation rate.
How: `ai-eng observe ai` -> LLM identifies self-optimization opportunities.

### dora — Delivery performance

What: deployment frequency, lead time, MTTR, change failure rate.
How: `ai-eng observe dora` -> LLM benchmarks against industry standards.

### health — Aggregated score

What: all dimensions combined -> 0-100 score, GREEN/YELLOW/RED semaphore.
How: `ai-eng observe health` -> LLM generates top 3 improvement actions.

## Shared Rules (Canonical)

Use these rules as the single source of truth for observability behavior shared by skill and agent.

- **OBS-R1 (CLI-first collection):** collect deterministic metrics via `ai-eng observe <mode>` before any interpretation.
- **OBS-R2 (Mode discipline):** execute exactly one requested mode (`engineer|team|ai|dora|health`) unless explicit aggregate request.
- **OBS-R3 (Interpretation contract):** report trends, anomalies, and top 3 actions with estimated impact.
- **OBS-R4 (Confidence labeling):** always include HIGH/MEDIUM/LOW data quality indicator.
- **OBS-B1 (Read-only boundary):** do not modify code, state, trackers, or governance artifacts.

## Procedure

1. **Apply shared rules** -- execute `OBS-R1..OBS-R4` for the requested mode.
2. **Report boundary** -- enforce `OBS-B1` and fail-open with explicit LOW confidence when data is incomplete.

## Data Quality Indicator

- **HIGH** (>=500 events, >=60 days): representative
- **MEDIUM** (>=100 events, >=14 days): directionally accurate
- **LOW** (<100 events or <14 days): may not be representative
