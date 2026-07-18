---
name: ai-advise
description: "Proactive governance advisor — checks standards, decisions, and quality trends during development. Always advisory, NEVER blocks. Three modes: `advise` (post-edit), `gate` (pre-dispatch), `drift` (on-demand decision audit). Trigger for 'governance check', 'advise on this change', 'check for drift', 'is this aligned with active decisions', 'shift-left advisory'. Not for blocking gates — use /ai-verify. Not for narrative code review — use /ai-review."
effort: cheap
argument-hint: "[advise|gate|drift] [paths...]"
tags: [governance, advisory, proactive]
model_tier: sonnet
mirror_family: cursor-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-advise/SKILL.md
edit_policy: generated-do-not-edit
---



# Advise

Discoverable wrapper around the `ai-advise` governance advisor: dispatches the agent via the Agent tool, captures findings with severity (`info | warn | concern`), renders an advisory. Never blocks. Never modifies code.

## Quick start

```
/ai-advise                    # advise mode on staged changes (default)
/ai-advise advise src/auth/   # post-edit advisory, scoped to paths
/ai-advise gate               # pre-dispatch governance check
/ai-advise drift              # compare implementation to active decisions
```

## Workflow

Principles: §10.6 SDD (every warning traces to an active decision or stack standard — no advice without a documented anchor); §10.4 DRY (the agent contract owns the analysis loop — the skill never paraphrases standards inline).

1. **Load stack contexts** — read `.ai-engineering/manifest.yml` `providers.stacks`; apply `.ai-engineering/overrides/<stack>/conventions.md` so stack-specific standards are in scope.
2. **Detect mode** — first positional arg is `advise` (default), `gate`, or `drift`. Anything else is a path filter; mode defaults to `advise`.
3. **Dependency preflight** — verify `.cursor/agents/ai-advise.mdc` exists. STOP and report the exact missing path if absent; never paraphrase agent instructions inline.
4. **Dispatch** — invoke the `ai-advise` agent via the Agent tool with `{mode, paths, severity_floor}`. It runs in its own context window and returns the structured advisory.
5. **Render** — emit the advisory table grouped by severity (`concern` → `warn` → `info`). Each row: `File | Finding | Recommendation | Anchor`, where Anchor is the standard or active decision the finding traces to.
6. **Audit** — emit `framework_event` `kind=advisory_emitted` with `{mode, file_count, warning_count, severity_distribution}`. Never emit `BLOCK`/`FAIL` outcomes — those belong to `/ai-verify` and git hooks.

## When to Use

- In-flight feature edit — catch standard drift before commit.
- Before dispatching a multi-task plan — confirm scope respects governance boundaries (`gate`).
- On-demand — audit code alignment with the active architectural decision set (`drift`).
- When you want advisory feedback, not an evidence-backed BLOCK verdict (use `/ai-verify` for that).

## Modes

| Mode | Trigger | Agent action |
|---|---|---|
| `advise` (default) | Post-edit in build | Scan changed files against stack standards + active decisions; emit severity-tagged warnings with recommendation. |
| `gate` | Pre-dispatch | Validate the proposed task respects governance boundaries (agent capabilities, expired risk acceptances, scope leakage). |
| `drift` | On-demand | Compare implementation against active architectural decisions; classify drift `none | minor | major | critical`. **Spec-140 W3** absorbed the former `verifier-architecture` heuristics: in `drift` mode also surface solution-intent alignment gaps, layer violations, structural drift, dependency-health concerns (circular imports, deep dependency chains), and boundary integrity (agents/skills/handlers staying within declared scope). Advisory only — `drift` never emits BLOCK. |

## Output Contract

Grouped by severity, rendered as a markdown table. Severity scale: `info` < `warn` < `concern`. Never `error`/`critical`/`blocker` — those belong to verify and git hooks.

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

Dispatches the `ai-advise` agent in `advise` mode scoped to `src/auth/`. The agent loads cross-cutting standards (`core.md`, `quality/core.md`) plus the Python stack overrides, checks decision drift against `decision-store.json` rows intersecting `src/auth/`, and returns two `warn` findings (a complexity trend near the cyclomatic ceiling; a missing telemetry field per an active observability decision). The skill renders the advisory and emits a `framework_event`. No code modified.

## Integration

**Called by**: operators directly via `/ai-advise`; auto-invoked by `/ai-build`
+ `/ai-autopilot` as the wave-end advisory pass.

**Calls**: the `ai-advise` agent (`.cursor/agents/ai-advise.mdc`) via the Agent
tool. Never reads or executes the agent body inline — strictly dispatch.

**See also**:
- `.cursor/skills/ai-verify/SKILL.md` — evidence-backed BLOCK lane (different engine).
- `.cursor/skills/ai-review/SKILL.md` — narrative human-judgment review.
- `.ai-engineering/overrides/<stack>/conventions.md` — stack overrides the agent consults.
- D-134-06 (rename direction `ai-guard` agent → `ai-advise`), D-134-07 (cohesion test enforcement).

$ARGUMENTS
