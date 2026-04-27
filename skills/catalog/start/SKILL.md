---
name: start
description: Use at the beginning of every session to bootstrap the framework — load CONSTITUTION + AGENTS + CLAUDE, render the dashboard (active spec, plan progress, decisions, governance findings, board state), and activate the instinct observation hook. Read-only. Trigger for "/ai-start", "begin session", "what's the state of the repo", "where did we leave off".
effort: medium
tier: core
capabilities: [tool_use, structured_output]
governance:
  blocking: false
---

# /ai-start

Session bootstrap. Reads the framework's constitutional and contextual
files, renders a one-screen dashboard of where the project is right now,
and activates the silent telemetry hook that feeds `/ai-learn`.

> **Read-only.** `/ai-start` never writes code, never opens issues,
> never transitions board state. Its single output is situational
> awareness for the next skill.

## When to use

- First action of every session — "begin session", "/ai-start"
- Returning to a project after a break — "where did we leave off"
- After a long-running task to re-orient — "show me the state"
- Before triaging — "what's open / failing / waiting"

## Process

1. **Load constitution** — read `CONSTITUTION.md`. Articles I–X are
   loaded into the working set; subsequent skills assume them.
2. **Load entry points** — `AGENTS.md` (cross-IDE), `CLAUDE.md` (this
   IDE if applicable), `GETTING_STARTED.md` for first-run users.
3. **Load active context** — `.ai-engineering/manifest.toml` (profile,
   stacks, overrides), the most recent spec, the current plan.
4. **Activate instinct hook** — register a passive observer on
   `framework-events.ndjson`. Each skill invocation, gate failure, and
   correction emits a structured event for `/ai-learn` to aggregate later.
5. **Render dashboard** (one screen):
   - Active spec — id, title, state (draft / approved / implementing)
   - Plan progress — % tasks complete, blockers
   - Recent decisions — last 5 entries from `decision-store.json`
   - Open governance findings — TTL-expiring risk acceptances
   - Board state — issues mapped to specs, gaps and orphans
   - Skills + agents matrix — what's available in this profile
6. **Suggest next skill** based on dashboard state (e.g. `/ai-plan`
   if a spec is approved but lacks a plan).

## Dashboard sketch

```
+-- ai-engineering session --------------------------------+
| Spec     spec-073 "Rate-limit middleware"  [approved]    |
| Plan     8/12 tasks complete, 2 blocked                  |
| Risks    1 high TTL expires in 3 days (FIN-2025-12)      |
| Board    JIRA-1842 In Review (mapped)                    |
| Gates    deterministic green | governance amber          |
| Next     /ai-implement   (plan approved, builder ready)  |
+----------------------------------------------------------+
```

## Hard rules

- NEVER mutate state in `/ai-start`. Read-only contract.
- NEVER skip constitution load — Articles I–X must be in context for
  every subsequent skill.
- NEVER show stale dashboards — read live state, not cached snapshots.
- Telemetry hook must be non-blocking; failure to register logs
  `instinct.hook_skipped` and continues.

## Common mistakes

- Treating `/ai-start` as optional "for new sessions" — it's mandatory
- Skipping constitution load to save tokens (later skills suffer)
- Rendering a stale dashboard from cached state
- Forgetting to suggest the next skill — the user is left wondering
- Letting the hook registration fail silently and losing learn data
