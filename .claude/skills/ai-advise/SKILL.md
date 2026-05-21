---
name: ai-advise
description: "Proactive governance advisor — checks standards, decisions, and quality trends during development. Always advisory, NEVER blocks. Three modes: `advise` (post-edit), `gate` (pre-dispatch), `drift` (on-demand decision audit). Trigger for 'governance check', 'advise on this change', 'check for drift', 'is this aligned with active decisions', 'shift-left advisory'. Not for blocking gates — use /ai-verify. Not for narrative code review — use /ai-review."
effort: cheap
model_tier: sonnet
argument-hint: "[advise|gate|drift] [paths...]"
tags: [governance, advisory, proactive]
---


# Advise

Discoverable wrapper around the `ai-advise` governance advisor: dispatches the agent via the Agent tool, captures findings with severity (`info | warn | concern`), and renders an advisory output. Never blocks. Never modifies code.

## Quick start

```
/ai-advise                                # default: advise mode on staged changes
/ai-advise advise src/auth/               # post-edit advisory, scoped to paths
/ai-advise gate                           # pre-dispatch governance check
/ai-advise drift                          # compare implementation to active decisions
```

## Workflow

Principles applied: §10.6 SDD (the advisory output traces every warning to an active decision or stack standard — no advice without a documented anchor); §10.4 DRY (the agent contract owns the analysis loop — the skill never paraphrases standards inline).

1. **Step 0** — load stack contexts: read `.ai-engineering/manifest.yml` `providers.stacks` and apply `.ai-engineering/overrides/<stack>/conventions.md` so stack-specific standards are in scope when guard analyses changed files.
2. **Detect mode** — first positional argument is `advise` (default), `gate`, or `drift`. Anything else is treated as a path filter and the mode defaults to `advise`.
3. **Dependency preflight** — verify `.claude/agents/ai-advise.md` (or, post-rename, `.claude/agents/ai-advise.md`) is on disk. STOP and report the exact missing path if absent — never paraphrase agent instructions inline.
4. **Dispatch** — invoke the `ai-advise` agent (or post-rename `ai-advise` agent) via the Agent tool with `{mode, paths, severity_floor}`. The agent runs in its own context window and returns the structured advisory.
5. **Render** — emit the advisory table grouped by severity (`concern` first, then `warn`, then `info`). Every row carries `File | Finding | Recommendation | Anchor` where `Anchor` is the standard or active decision the finding traces to.
6. **Audit** — emit `framework_event` `kind=advisory_emitted` with `{mode, file_count, warning_count, severity_distribution}`. Never emits `BLOCK` or `FAIL` outcomes — those belong to `/ai-verify` and git hooks.

## When to Use

- During an in-flight feature edit, to catch standard drift before commit time.
- Before dispatching a multi-task plan to confirm scope respects governance boundaries (`gate` mode).
- On-demand to audit how well current code aligns with the active architectural decision set (`drift` mode).
- When you need advisory feedback instead of an evidence-backed BLOCK verdict (use `/ai-verify` for the latter).

## Modes

| Mode | Trigger | What the agent does |
|---|---|---|
| `advise` (default) | Post-edit in build | Scan changed files against stack standards + active decisions; emit warnings with severity and recommendation. |
| `gate` | Pre-dispatch | Validate the proposed task respects governance boundaries (agent capabilities, expired risk acceptances, scope leakage). |
| `drift` | On-demand | Compare implementation against active architectural decisions; classify drift `none | minor | major | critical`. **Spec-140 W3** absorbed the former `verifier-architecture` heuristics: in `drift` mode also surface solution-intent alignment gaps, layer violations, structural drift, dependency-health concerns (circular imports, deep dependency chains), and boundary integrity (agents/skills/handlers staying within declared scope). All advisory only -- `drift` never emits BLOCK. |

## Output Contract

The advisory is grouped by severity and rendered as a markdown table. Severity scale: `info` < `warn` < `concern`. Guard never uses `error`, `critical`, or `blocker` — those vocabularies belong to verify and git hooks.

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

| Aspect | `/ai-advise` (this skill) | `/ai-verify` | `/ai-review` |
|---|---|---|---|
| When | During development | Pre-release / pre-merge | Pre-merge narrative review |
| Blocking | Never (fail-open) | Can BLOCK on FAIL | Never (judgement only) |
| Scope | Changed files + active decisions | Full codebase or mode-specific | PR / branch / paths |
| Output | Severity-tagged warnings | Scored evidence-backed verdicts | Specialist-attributed findings |
| Engine | `ai-advise` agent (read-only) | `ai-verify` agent + specialists | `ai-review` agent + 9 specialists |

`/ai-advise` is the shift-left lane: catch friction before it reaches the gates. `/ai-verify` is the gate itself. `/ai-review` is the human-judgement lane that asks "would a staff engineer approve this?".

## Boundaries

- **Never modifies code** — advisory only.
- **Never blocks execution** — fail-open always.
- **Never emits FAIL / BLOCK / CRITICAL** — those vocabularies are reserved for `/ai-verify` and git hooks.
- **Read-only** for all files except `decision-store.json` (drift annotations only, via the audit API) and `state/framework-events.ndjson` (canonical outcomes).
- **Single agent dispatch** — the SKILL.md never reads the agent file inline; it dispatches via the Agent tool so the agent runs in its own context window.

## Examples

### Example 1 — post-edit advisory after a feature change

User: "advise on the changes I just made under src/auth/"

```
/ai-advise advise src/auth/
```

Skill dispatches the `ai-advise` agent in `advise` mode scoped to `src/auth/`. The agent loads cross-cutting standards (`core.md`, `quality/core.md`) plus the Python stack overrides, checks decision drift against the active `decision-store.json` rows that intersect `src/auth/`, and returns an advisory listing two `warn` findings (a complexity trend approaching the cyclomatic ceiling, and a missing telemetry field per an active observability decision). The skill renders the advisory and emits a `framework_event`. No code is modified.

### Example 2 — drift scan against active architectural decisions

User: "do a drift check across the persistence layer"

```
/ai-advise drift src/persistence/
```

Skill dispatches the `ai-advise` agent in `drift` mode. The agent loads active decisions tagged with persistence-layer scope (e.g. "repositories return entities, not rows"), maps each decision to governed locations, and classifies alignment per location. The skill renders a drift table showing one `minor` cosmetic drift (a repository method returning a dataclass instead of the documented domain entity) and zero `critical` contradictions. Recommendation: open a refactor ticket; no immediate action required.

## Integration

**Called by**: operators directly via `/ai-advise`; auto-invoked by `/ai-build`
+ `/ai-autopilot` as the wave-end advisory pass.

**Calls**: the `ai-advise` agent (`.claude/agents/ai-advise.md`) via the Agent
tool. Never reads or executes the agent body inline — strictly dispatch.

**See also**:
- `.claude/skills/ai-verify/SKILL.md` — evidence-backed BLOCK lane (different engine).
- `.claude/skills/ai-review/SKILL.md` — narrative human-judgment review.
- `.ai-engineering/overrides/<stack>/conventions.md` — stack overrides the agent consults.
- D-134-06 (rename direction `ai-guard` agent → `ai-advise`), D-134-07 (cohesion test enforcement).

$ARGUMENTS
