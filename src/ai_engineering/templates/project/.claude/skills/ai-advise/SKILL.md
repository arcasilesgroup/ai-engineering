---
name: ai-advise
description: "Proactive governance advisor — checks standards, decisions, and quality trends during development. Always advisory, NEVER blocks. Three modes: `advise` (post-edit), `gate` (pre-dispatch), `drift` (on-demand decision audit). Trigger for 'governance check', 'advise on this change', 'check for drift', 'is this aligned with active decisions', 'shift-left advisory'. Not for blocking gates — use /ai-verify. Not for narrative code review — use /ai-review."
effort: cheap
argument-hint: "[advise|gate|drift] [paths...]"
tags: [governance, advisory, proactive]
---


# Advise

Discoverable wrapper around the `ai-advise` governance advisor: dispatches the agent via the Agent tool and renders a severity-tagged advisory (`info | warn | concern`). Never blocks, never modifies code.

## Workflow

Principles: §10.6 SDD (every warning traces to an active decision or stack standard — no advice without a documented anchor); §10.4 DRY (the agent contract owns the analysis loop — the skill never paraphrases standards inline).

1. **Load stack contexts** — read `.ai-engineering/manifest.yml` `providers.stacks`; apply `.ai-engineering/overrides/<stack>/conventions.md` so stack-specific standards are in scope.
2. **Detect mode** — first positional arg is `advise` (default), `gate`, or `drift`. Anything else is a path filter; mode defaults to `advise`.
3. **Dependency preflight** — verify `.claude/agents/ai-advise.md` exists. STOP and report the exact missing path if absent; never paraphrase agent instructions inline.
4. **Dispatch** — invoke the `ai-advise` agent via the Agent tool with `{mode, paths, severity_floor}`. It runs in its own context window and returns the structured advisory.
5. **Render** — emit the advisory table grouped by severity (`concern` → `warn` → `info`). Each row: `File | Finding | Recommendation | Anchor`, where Anchor is the standard or active decision the finding traces to.
6. **Audit** — emit `framework_event` `kind=advisory_emitted` with `{mode, file_count, warning_count, severity_distribution}`. Never emit `BLOCK`/`FAIL` outcomes — those belong to `/ai-verify` and git hooks.

## Modes

| Mode | Trigger | Agent action |
|---|---|---|
| `advise` (default) | Post-edit in build | Scan changed files against stack standards + active decisions; emit severity-tagged warnings with recommendation. |
| `gate` | Pre-dispatch | Validate the proposed task respects governance boundaries (agent capabilities, expired risk acceptances, scope leakage). |
| `drift` | On-demand | Compare implementation against active architectural decisions; classify drift `none | minor | major | critical`. **Spec-140 W3** absorbed the former `verifier-architecture` heuristics: in `drift` mode also surface solution-intent alignment gaps, layer violations, structural drift, dependency-health concerns (circular imports, deep dependency chains), and boundary integrity (agents/skills/handlers staying within declared scope). Advisory only — `drift` never emits BLOCK. |

## Output Contract

Grouped by severity, rendered as a markdown table. Severity scale: `info` < `warn` < `concern` (never `error`/`critical`/`blocker`).

```markdown
# Guard Advisory: <mode>

## Summary
- Files checked: N
- Warnings: N (concern: N, warn: N, info: N)

## Warnings
| # | Severity | File | Finding | Recommendation | Anchor |

## Decision Context
[Active decisions that informed this advisory]
```

## Differentiation

| Aspect | `/ai-advise` | `/ai-verify` | `/ai-review` |
|---|---|---|---|
| When | During development | Pre-release / pre-merge | Pre-merge narrative review |
| Blocking | Never (fail-open) | Can BLOCK on FAIL | Never (judgement only) |
| Scope | Changed files + active decisions | Full codebase or mode-specific | PR / branch / paths |
| Output | Severity-tagged warnings | Scored evidence-backed verdicts | Specialist-attributed findings |
| Engine | `ai-advise` agent (read-only) | `ai-verify` agent + specialists | `ai-review` agent + 9 specialists |

Shift-left lane: catch friction before it reaches the gates. `/ai-verify` is the gate; `/ai-review` asks "would a staff engineer approve this?".

## Boundaries

- **Never modifies code** — advisory only.
- **Never blocks execution** — fail-open always.
- **Never emits FAIL / BLOCK / CRITICAL** — reserved for `/ai-verify` and git hooks.
- **Read-only** for all files except `decision-store.json` (drift annotations only, via the audit API) and `state/framework-events.ndjson` (canonical outcomes).
- **Single agent dispatch** — never reads the agent file inline; dispatches via the Agent tool so the agent runs in its own context window.

## Examples

User: "advise on the changes I just made under src/auth/"

```
/ai-advise advise src/auth/
```

Dispatches the `ai-advise` agent in `advise` mode scoped to `src/auth/`: it loads cross-cutting + Python-stack standards, checks decision drift against `decision-store.json` rows intersecting `src/auth/`, and returns severity-tagged `warn` findings. The skill renders the advisory and emits a `framework_event`. No code modified.

## Integration

**Called by**: operators via `/ai-advise`; `/ai-build` + `/ai-autopilot` (wave-end advisory pass). **Calls**: the `ai-advise` agent (`.claude/agents/ai-advise.md`) via the Agent tool — Agent-tool dispatch is the primary path. **Inline fallback**: on a harness WITHOUT a subagent/Agent-tool primitive, this skill is executed by reading the `.claude/agents/ai-advise.md` specialist file inline and running its steps in-context sequentially — inline-sequential is the floor, not a substitute for the isolated dispatch. **See also**: `.claude/skills/ai-verify/SKILL.md` (evidence-backed BLOCK lane), `.claude/skills/ai-review/SKILL.md` (narrative review), `.ai-engineering/overrides/<stack>/conventions.md` (stack overrides); D-134-06 (`ai-guard` agent → `ai-advise` rename), D-134-07 (cohesion test enforcement).

$ARGUMENTS
