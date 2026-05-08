---
name: ai-create
description: "Creates new ai-engineering skills or agents end-to-end: scaffold, TDD pressure-test, optimize description, register in manifest, sync mirrors. Trigger for 'create a new skill', 'add a slash command', 'the framework needs a capability for', 'build a new agent', 'scaffold a skill for'. Not for evolving existing skills; use /ai-skill-tune instead. Not for description-only optimization; use /ai-prompt instead."
effort: high
argument-hint: "skill [name]|agent [name]"
tags: [meta, framework, creation]
mirror_family: gemini-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-create/SKILL.md
edit_policy: generated-do-not-edit
---


# Create

## Purpose

Create new skills and agents for the ai-engineering framework. Owns the ai-engineering context layer (governance, manifest registration, IDE mirrors, pain sources). Delegates skill drafting, TDD pressure testing, eval pipeline, and description optimization to Anthropic's `skill-creator`.

## Trigger

`/ai-create skill <name>` or `/ai-create agent <name>` — when the framework needs a new capability that no existing skill or agent covers.

---

## Start Here — Registration Checklist

This is the invariant checklist that must be satisfied regardless of whether you're creating a skill or an agent. Write it at the top and check items off as you go:

```
## Registration Checklist — [NAME]
- [ ] No overlap with existing skills (checked skill list in manifest.yml)
- [ ] File created at correct path (.gemini/skills/ai-{name}/SKILL.md or .gemini/agents/ai-{name}.md)
- [ ] Frontmatter has name, description, argument-hint
- [ ] Description is CSO-optimized (triggering conditions, not summary)
- [ ] IDE-compatibility fields set if needed (copilot_compatible, disable-model-invocation)
- [ ] Registered in .ai-engineering/manifest.yml (skills.registry or agents.names + total)
- [ ] Mirror sync run: python scripts/sync_command_mirrors.py
- [ ] Tests pass: source .venv/bin/activate && python -m pytest tests/unit/ -q
- [ ] Pain sources consulted (decision-store, LESSONS.md) for constraints
```

---

## Workflow

Two modes:

- **skill `<name>`** — context load (overlap check + pain sources), delegate to skill-creator for TDD + evals, register in `manifest.yml`, sync mirrors.
- **agent `<name>`** — scaffold the agent file, declare frontmatter (description, model, tools, dispatch source), register in `manifest.yml`, sync mirrors.

## Mode: skill <name>

### Phase 1 — ai-engineering Context (this skill owns this)

Follow `handlers/create-skill.md`. Before creating anything, load project context:

1. **Check for overlap** — read `.ai-engineering/manifest.yml` skill registry. If a skill already covers this capability, evolve it with `/ai-skill-tune` instead.
2. **Load pain sources** — read state.db.decisions, LESSONS.md, observations.yml for constraints (e.g., DEC-003 plan/execute split, similar-skill failures, instinct sequences this skill should optimize).
3. **Determine IDE compatibility** — see IDE-Compatibility Frontmatter below.

### Phase 2 — Delegate to skill-creator for TDD + Evals

Invoke Anthropic's `skill-creator` with this context:

```
Create a new skill called "ai-{name}" for the ai-engineering framework.

Context about the framework:
- Skills live in .gemini/skills/ai-{name}/SKILL.md
- They follow this frontmatter format: name, description (CSO-optimized), effort, argument-hint, tags
- The description field is the primary triggering mechanism — it must describe WHEN to use, not WHAT it does
- Pain sources found: [pass relevant lessons, decisions, instinct patterns from Phase 1]

The skill should:
[pass the user's requirements]

Look at existing skills like .gemini/skills/ai-security/SKILL.md or .gemini/skills/ai-review/SKILL.md
for format reference.
```

skill-creator owns drafting, TDD pressure testing, eval pipeline (grader/analyzer/benchmark/HTML viewer), description-optimization, and iteration. After it returns, verify the SKILL.md follows ai-engineering conventions (Step 0 context loading, output contract), frontmatter has all required fields, and description is CSO-optimized.

### Phase 3 — Register and Sync (this skill owns this)

Walk the Registration Checklist (Start Here) and `handlers/validate.md`. Manifest entry shape: `ai-{name}: { type: <type>, tags: [<tags>] }`; bump `skills.total`. Mirror sync: `python scripts/sync_command_mirrors.py`. Tests: `source .venv/bin/activate && python -m pytest tests/unit/ -q`. Update README.md skill counts if they changed.

---

## Mode: agent <name>

Follow `handlers/create-agent.md`. Agents don't go through skill-creator (they're not skills) — create them directly:

1. **Define mandate** — singular responsibility (one thing).
2. **Load pain sources** — same as skill Phase 1; check decision-store for agent-architecture constraints (e.g., DEC-019).
3. **Scaffold** `.gemini/agents/ai-{name}.md` with: Identity (role/experience/specialization), Mandate (owns/does-not-own), Capabilities (declared permissions: read-only/read-write/paths), Behavior (modes/procedures), Output Contract (structured format), Boundaries (hard limits/escalation), Self-challenge protocol (pre-action questions).
4. **Register** in `manifest.yml` agents section (names array + total count).
5. **Create matching skill** — if `/ai-{name}` entry point is needed, scaffold via `/ai-create skill {name}`.
6. **Sync and test** — same as skill Phase 3.

---

## CSO Description Patterns

The `description` field is the skill's search ranking — it determines whether the skill triggers. It must describe **triggering conditions**, not summarize functionality.

| Bad (summary)             | Good (CSO trigger)                                                          |
| ------------------------- | --------------------------------------------------------------------------- |
| "Generates standup notes" | "Use when preparing daily standup notes or summarizing recent PR activity"  |
| "Sprint planning tool"    | "Use when planning a new sprint or running a retrospective"                 |
| "Resolves git conflicts"  | "Use when git reports merge conflicts during rebase, merge, or cherry-pick" |

## IDE-Compatibility Frontmatter

| Field                            | Effect                                                           |
| -------------------------------- | ---------------------------------------------------------------- |
| `copilot_compatible: false`      | Excludes from `.github/skills/` mirror (Claude Code-only skills) |
| `codex_compatible: false`        | Excludes from `.codex/skills/` mirror                            |
| `gemini_compatible: false`       | Excludes from `.gemini/skills/` mirror                           |
| `disable-model-invocation: true` | Tells GitHub Copilot not to invoke LLM (script-only skills)      |

`ai-analyze-permissions` is the current example of a provider-scoped skill: it opts out of GitHub Copilot, Codex, and Gemini mirrors.

## Quick Reference

```
/ai-create skill standup     # create a new standup skill (delegates TDD to skill-creator)
/ai-create agent reviewer    # create a new reviewer agent (direct scaffold)
```

## Examples

### Example 1 — create a brand-new skill

User: "the framework needs a capability for OpenAPI schema validation — create the skill"

```
/ai-create skill ai-openapi
```

Loads pain context, delegates draft + TDD to `skill-creator`, registers in `manifest.yml`, runs `sync_command_mirrors.py`, verifies tests still pass.

### Example 2 — scaffold a new specialist agent

User: "add a new reviewer agent for accessibility"

```
/ai-create agent reviewer-accessibility
```

Scaffolds the agent file with CSO description, `tools` whitelist, `model: sonnet`, dispatch-source comment; registers in manifest; syncs mirrors.

## Integration

Delegates to: Anthropic `skill-creator` (TDD + evals + description optimization). Reads: `manifest.yml`, `state.db.decisions`, `LESSONS.md`. Calls: `python scripts/sync_command_mirrors.py`. See also: `/ai-skill-tune` (improve existing), `/ai-prompt` (description-only).

$ARGUMENTS
