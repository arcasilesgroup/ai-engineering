---
id: "044"
slug: "skill-agent-telemetry"
status: "complete"
created: "2026-03-10"
size: "M"
tags: ["observability", "telemetry", "skills", "agents", "cross-ide"]
branch: "feat/044-skill-agent-telemetry"
pipeline: "standard"
decisions:
  - id: "D044-001"
    title: "CLI-as-bridge for cross-IDE emission"
    rationale: "ai-eng signals emit already exists (spec-042). All IDEs can execute shell commands. No IDE-specific hooks needed."
  - id: "D044-002"
    title: "Emit directive at Procedure/Behavior start"
    rationale: "Placing the directive at the top of the procedural section maximizes LLM compliance. Pattern proven in build.md and scan.md."
  - id: "D044-003"
    title: "Fire-and-forget emission"
    rationale: "Emission is best-effort. If ai-eng is not installed or fails, the skill/agent continues normally. Fail-open."
---

# Spec 044 — Skill & Agent Telemetry: Cross-IDE Usage Tracking

## Problem

The observe agent (modes `team` and `ai`) promises dashboards for:
- **Skill Usage**: which skills invoked, frequency, avg tokens consumed
- **Agent Dispatch**: which agents dispatched, success rate

But **no `skill_invoked` or `agent_dispatched` events exist** in the audit log. Spec-042 explicitly deferred this (D042-001: "wait for dispatcher"). The result: observe team/ai dashboards are data-starved for these metrics.

Since skills and agents are LLM-side (markdown instructions, no Python dispatcher), the emission must work across all supported IDEs: Claude Code, GitHub Copilot, Gemini CLI, and OpenAI Codex.

## Solution

Use the existing `ai-eng signals emit` CLI (spec-042) as the cross-IDE bridge. Add a standardized emit directive to every skill and agent markdown file. Add aggregators and wire observe dashboards.

### Architecture

```
┌─────────────────┐     ┌──────────────────────────┐     ┌──────────────┐
│ AI (any IDE)    │────>│ ai-eng signals emit      │────>│ audit-log    │
│ reads SKILL.md  │     │   skill_invoked           │     │  .ndjson     │
│ runs shell cmd  │     │   agent_dispatched         │     └──────────────┘
└─────────────────┘     └──────────────────────────┘
```

All IDEs can execute shell commands — no IDE-specific hooks required.

## Scope

### In Scope

1. **Emit directives** — add `ai-eng signals emit skill_invoked` to 35 SKILL.md files
2. **Emit directives** — add `ai-eng signals emit agent_dispatched` to 5 agent .md files (build/scan already have domain-specific emitters; add generic dispatch event to all 7)
3. **Template sync** — update `src/ai_engineering/templates/.ai-engineering/` mirrors
4. **Aggregators** — `skill_usage_from()` and `agent_dispatch_from()` in `signals.py`
5. **Dashboard wiring** — observe team: Skill Usage + Agent Dispatch sections; observe ai: skill efficiency
6. **Tests** — unit tests for new aggregators

### Out of Scope

- Token counting per skill (requires IDE-specific instrumentation)
- Escalation tracking (no mechanism exists)
- Modifying the `ai-eng signals emit` CLI command (already works)
- Adding new Python emitter functions to `audit.py` (using generic CLI emit)

## Acceptance Criteria

1. All 35 SKILL.md files contain `ai-eng signals emit skill_invoked` directive
2. All 7 agent .md files contain `ai-eng signals emit agent_dispatched` directive
3. Template mirrors in `src/ai_engineering/templates/` are synced
4. `skill_usage_from()` returns frequency, most-used, least-used from audit log
5. `agent_dispatch_from()` returns frequency per agent from audit log
6. `observe team` shows Skill Usage and Agent Dispatch sections
7. `observe ai` includes skill/agent data in efficiency metrics
8. All existing tests pass, new tests cover new aggregators
9. `ruff check` + `ruff format` + `ty` clean

## Risks

1. **LLM compliance** — LLMs may skip the emit directive silently. **Mitigation**: prominent placement at procedure start; observe reports "LOW confidence" when events are sparse.
2. **Template drift** — 35+ files to keep in sync between `.ai-engineering/` and `templates/`. **Mitigation**: batch update script; validator already checks template sync.
3. **Event noise** — frequent skill invocations could bloat audit log. **Mitigation**: NDJSON append-only is cheap; log rotation is a future concern.
