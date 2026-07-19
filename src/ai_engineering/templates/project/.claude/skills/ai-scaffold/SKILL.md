---
name: ai-scaffold
description: "Creates new ai-engineering skills or agents end-to-end: scaffold, TDD pressure-test, optimize description, register in manifest, sync mirrors. Trigger for 'create a new skill', 'add a slash command', 'the framework needs a capability for', 'build a new agent', 'scaffold a skill for'. Not for evolving existing skills; use /ai-skill-improve instead. Not for description-only optimization; use /ai-prompt-tune instead."
effort: mid
argument-hint: "skill [name]|agent [name]"
tags: [meta, framework, creation]
---

# Scaffold

Create new skills and agents for the ai-engineering framework. Owns the ai-engineering
context layer (governance, manifest registration, IDE mirrors, pain sources); delegates
skill drafting, TDD pressure-testing, eval pipeline, and description optimization to
Anthropic's `skill-creator`.

## Registration Checklist — [NAME]

Write at top; check off regardless of skill vs agent:

- [ ] No overlap with existing skills (checked `manifest.yml` registry)
- [ ] File at correct path (`.claude/skills/ai-<name>/SKILL.md` or `.claude/agents/ai-<name>.md`)
- [ ] Frontmatter has name, description, argument-hint
- [ ] Description CSO-optimized (triggering conditions, not summary)
- [ ] IDE-compatibility fields set if needed (copilot_compatible, disable-model-invocation)
- [ ] Registered in `.ai-engineering/manifest.yml` (skills.registry or agents.names + total)
- [ ] Mirror sync run: `python scripts/sync_command_mirrors.py`
- [ ] Tests pass: `source .venv/bin/activate && python -m pytest tests/unit/ -q`
- [ ] Pain sources consulted (decision-store, LESSONS.md) for constraints

## Workflow

- Principles applied: §10.6 SDD (every new capability traces to a documented gap — no
  scaffold without one); §10.4 DRY (a capability lives in exactly one skill; overlap
  routes to /ai-skill-improve).

### Mode: skill <name>

1. **Context (owned here)** — follow `handlers/create-skill.md`:
   - Check overlap: read `manifest.yml` skill registry; if the capability is covered, STOP and route to `/ai-skill-improve`.
   - Load pain sources: `decision-store.json`, `LESSONS.md`, `observations.yml` (e.g. DEC-003 plan/execute split, similar-skill failures, instinct sequences to optimize).
   - Determine IDE compatibility (see table below).
2. **Delegate to skill-creator** — invoke Anthropic `skill-creator` with the context block below. It owns drafting, TDD pressure-testing, the eval pipeline (grader/analyzer/benchmark/HTML viewer), description optimization, and iteration.
3. **Verify return** — SKILL.md follows ai-engineering conventions (Step 0 context loading, output contract); frontmatter has all required fields; description is CSO-optimized.
4. **Register + sync (owned here)** — walk the Registration Checklist and `handlers/validate.md`. Manifest entry: `ai-<name>: { type: <type>, tags: [<tags>] }`; bump `skills.total`. Run `python scripts/sync_command_mirrors.py`; run unit tests; update README skill counts if they changed.

skill-creator context block:

```
Create a new skill called "ai-<name>" for the ai-engineering framework.
- Skills live in .claude/skills/ai-<name>/SKILL.md
- Frontmatter: name, description (CSO-optimized), effort, argument-hint, tags
- description is the primary triggering mechanism — describe WHEN to use, not WHAT it does
- Pain sources found: [lessons, decisions, instinct patterns from Step 1]
The skill should: [pass the user's requirements]
Format reference: .claude/skills/ai-security/SKILL.md or .claude/skills/ai-review/SKILL.md
```

### Mode: agent <name>

Agents skip skill-creator (they are not skills). Follow `handlers/create-agent.md`:

1. **Define mandate** — singular responsibility (one thing).
2. **Load pain sources** — as skill Step 1; check decision-store for agent-architecture constraints (e.g. DEC-019).
3. **Scaffold** `.claude/agents/ai-<name>.md` — frontmatter (CSO description, `model`, `tools` whitelist, dispatch-source comment) plus body: Identity (role/experience/specialization), Mandate (owns/does-not-own), Capabilities (read-only/read-write/paths), Behavior (modes/procedures), Output Contract, Boundaries (limits/escalation), Self-challenge protocol.
4. **Register** in `manifest.yml` agents section (names array + total count).
5. **Create matching skill** — if a `/ai-<name>` entry point is needed, scaffold via `/ai-scaffold skill <name>`.
6. **Sync + test** — as skill Step 4.

## CSO Description Patterns

The `description` field is the skill's search ranking — describe triggering conditions, not functionality.

| Bad (summary) | Good (CSO trigger) |
| --- | --- |
| "Generates standup notes" | "Use when preparing daily standup notes or summarizing recent PR activity" |
| "Sprint planning tool" | "Use when planning a new sprint or running a retrospective" |
| "Resolves git conflicts" | "Use when git reports merge conflicts during rebase, merge, or cherry-pick" |

## IDE-Compatibility Frontmatter

| Field | Effect |
| --- | --- |
| `copilot_compatible: false` | Excludes from `.github/skills/` mirror (Claude Code-only) |
| `codex_compatible: false` | Excludes from `.codex/skills/` mirror |
| `disable-model-invocation: true` | Tells GitHub Copilot not to invoke LLM (script-only skills) |

Provider-scoped skills set these to opt out of the Copilot and Codex mirrors while staying available in Claude Code; no skill currently uses this scoping.

## Examples

### Example — create a brand-new skill

User: "the framework needs a capability for OpenAPI schema validation — create the skill"

```
/ai-scaffold skill ai-openapi
```

Loads pain context, delegates draft + TDD to `skill-creator`, registers in `manifest.yml`, runs `sync_command_mirrors.py`, verifies tests still pass.

## Integration

Delegates to: Anthropic `skill-creator` (TDD + evals + description optimization). Reads: `manifest.yml`, `decision-store.json`, `LESSONS.md`. Calls: `python scripts/sync_command_mirrors.py`. See also: `/ai-skill-improve` (improve existing), `/ai-prompt-tune` (description-only).

$ARGUMENTS
