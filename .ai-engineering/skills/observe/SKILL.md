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

## Procedure

1. **Invoke Python CLI** -- `ai-eng observe <mode>` to collect and compute raw metrics.
2. **Read output** -- parse the formatted markdown from CLI.
3. **Interpret** -- identify trends, anomalies, and improvement opportunities.
4. **Recommend** -- generate top 3 actionable improvements with estimated impact.
5. **Report** -- present dashboard with data quality indicator (HIGH/MEDIUM/LOW).

## Data Quality Indicator

- **HIGH** (>=500 events, >=60 days): representative
- **MEDIUM** (>=100 events, >=14 days): directionally accurate
- **LOW** (<100 events or <14 days): may not be representative
