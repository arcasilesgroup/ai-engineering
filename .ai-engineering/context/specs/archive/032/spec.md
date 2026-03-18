---
id: "032"
title: "ai-engineering v3: Architecture redesign — 6 agents, 33 skills, Python CLI, observability"
status: "in-progress"
created: "2026-03-04"
branch: "spec/032-ai-eng-v3"
---

# Spec 032: ai-engineering v3 — Full Architecture Redesign

## Problem

Current architecture (6 agents, 47 skills) suffers from:
- **God Object**: Review agent handles security, quality, governance, performance — violates SRP.
- **Skill overlap**: 47 skills with shared concerns, no clear owner boundaries.
- **Rigid pipeline**: Single pipeline strategy, no auto-classification.
- **No observability**: 2/10 — audit-log exists but no metrics, dashboards, or DORA.
- **Empty decision store**: Never operationalized.
- **No fault tolerance**: No session checkpoints or recovery.
- **Token waste**: All work done via LLM, ~38% could be deterministic Python.

## Solution

Redesign from scratch with DevSecOps + ALM + GitOps principles:

1. **6 Agents with clean bounded contexts**: Plan, Build, Scan, Release, Write, Observe
2. **47 → 33 skills**: Consolidate overlapping skills, add new capabilities
3. **Python CLI (`ai-eng`)**: Deterministic tasks run locally (~38% token savings)
4. **7-mode unified scanner**: governance, security, quality, perf, a11y, feature-gap, architecture
5. **Observability for 3 audiences**: engineers, team, AI — plus DORA metrics
6. **Session recovery**: Checkpoints, partial completion, Hamilton-inspired fault tolerance
7. **Pipeline auto-classification**: trivial/hotfix/standard/full
8. **Single event store**: audit-log.ndjson (no dual-write)

## Stacks Supported

Python, .NET, React, TypeScript, Next.js, Node, NestJS, React Native, Rust,
YAML, Terraform, Astro, GitHub Actions, Azure Pipelines, Azure, Bash, PowerShell, SQL, PostgreSQL

## Success Criteria

- 6 agents, 33 skills operational
- `ai-eng` CLI runs standalone (no AI tokens for deterministic tasks)
- `/ai:scan platform` produces GO/NO-GO with score 0-100
- `/ai:observe health` renders dashboard for 3 audiences
- Session checkpoint + recovery works
- Pipeline auto-classification tested
- All existing `/ai:commit` and `/ai:pr` workflows preserved

## Design Principles (The Conclave)

| Principle | Author | Application |
|-----------|--------|-------------|
| Bounded Contexts | Fowler | 6 agents = 6 bounded contexts |
| Dependency Rule | Uncle Bob | Skills don't know who invokes them |
| Design for Failure | Hamilton | Session checkpoints + recovery |
| Message Passing | Kay | Agents communicate via spec + tasks, not shared state |
| Measure then Optimize | Carmack | Python CLI for hot paths, LLM for cold paths |
| Ubiquitous Language | Evans | Agent, Skill, Scanner, Gate, Signal, Decision |
