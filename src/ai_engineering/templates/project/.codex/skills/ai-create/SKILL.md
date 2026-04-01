---
name: ai-create
description: Use when adding a new slash command, building a new agent role, or extending the ai-engineering framework with a capability it does not yet have. Trigger for 'create a new skill', 'add a slash command', 'the framework needs a capability for X', 'build a new agent'. Covers skill scaffold, TDD pressure testing, description optimization, registration, and mirror sync.
effort: high
argument-hint: "skill <name>|agent <name>"
tags: [meta, framework, creation]
---



# Create

## Purpose

Create new skills and agents for the ai-engineering framework. This skill owns the **ai-engineering context layer** (governance, manifest registration, IDE mirrors, pain sources). For the actual skill creation, TDD pressure testing, eval pipeline, and description optimization, it delegates to Anthropic's `skill-creator` which has the full infrastructure.

## Trigger

- Command: `/ai-create skill <name>` or `/ai-create agent <name>`
- Context: framework needs a new capability that no existing skill or agent covers.

---

## Start Here — Registration Checklist

This is the invariant checklist that must be satisfied regardless of whether you're creating a skill or an agent. Write it at the top and check items off as you go:

```
## Registration Checklist — [NAME]
- [ ] No overlap with existing skills (checked skill list in manifest.yml)
- [ ] File created at correct path (.codex/skills/ai-{name}/SKILL.md or .codex/agents/ai-{name}.md)
- [ ] Frontmatter has name, description, argument-hint
- [ ] Description is CSO-optimized (triggering conditions, not summary)
- [ ] IDE-compatibility fields set if needed (copilot_compatible, disable-model-invocation)
- [ ] Registered in .ai-engineering/manifest.yml (skills.registry or agents.names + total)
- [ ] Mirror sync run: python scripts/sync_command_mirrors.py
- [ ] Tests pass: source .venv/bin/activate && python -m pytest tests/unit/ -q
- [ ] Pain sources consulted (decision-store, LESSONS.md) for constraints
```

---

## Mode: skill <name>

### Phase 1 — ai-engineering Context (this skill owns this)

Follow `handlers/create-skill.md` for the full scaffold procedure.

Before creating anything, load project context:

1. **Check for overlap** — read `.ai-engineering/manifest.yml` skill registry. If a skill already covers this capability, evolve it with `/ai-skill-evolve` instead of creating a new one.

2. **Load pain sources** — read decision-store.json, LESSONS.md, instincts.yml for constraints that affect this skill:
   - Decisions that limit scope (e.g., DEC-003 plan/execute split means a planning skill must not also execute)
   - Lessons about similar skills that failed or needed correction
   - Instinct patterns that reveal tool sequences this skill should optimize

3. **Determine IDE compatibility**:
   - Most skills: omit `copilot_compatible` (mirrors to all 4 IDEs)
   - Skills that use Claude Code-exclusive features (e.g., reading `.claude/settings.json` deny rules): set `copilot_compatible: false`
   - Script-only skills that bypass LLM: also set `disable-model-invocation: true`

### Phase 2 — Delegate to skill-creator for TDD + Evals

Invoke Anthropic's `skill-creator` with this context:

```
Create a new skill called "ai-{name}" for the ai-engineering framework.

Context about the framework:
- Skills live in .codex/skills/ai-{name}/SKILL.md
- They follow this frontmatter format: name, description (CSO-optimized), effort, argument-hint, tags
- The description field is the primary triggering mechanism — it must describe WHEN to use, not WHAT it does
- Pain sources found: [pass relevant lessons, decisions, instinct patterns from Phase 1]

The skill should:
[pass the user's requirements]

Look at existing skills like .codex/skills/ai-security/SKILL.md or .codex/skills/ai-review/SKILL.md
for format reference.
```

**What skill-creator handles:**
- Drafting the SKILL.md content
- TDD pressure testing (RED/GREEN/REFACTOR cycle with parallel agents)
- Eval pipeline: grader, analyzer, benchmark aggregation, HTML viewer
- Description optimization for triggering accuracy (run_loop.py)
- Iterating based on user feedback

**What you verify after skill-creator is done:**
- The SKILL.md follows ai-engineering conventions (Step 0 context loading, output contract)
- Frontmatter has all required fields
- Description is CSO-optimized (triggering conditions, not summary)

### Phase 3 — Register and Sync (this skill owns this)

Follow `handlers/validate.md` for the validation checklist.

After skill-creator delivers the SKILL.md:

1. **Verify file is at correct path**: `.codex/skills/ai-{name}/SKILL.md`

2. **Register in manifest** — add to `.ai-engineering/manifest.yml`:
   ```yaml
   ai-{name}: { type: <type>, tags: [<tags>] }
   ```
   Update `skills.total` count.

3. **Sync mirrors** — run:
   ```bash
   python scripts/sync_command_mirrors.py
   ```
   This creates mirrors in `.codex/`, `.gemini/`, `.github/skills/` (if copilot-compatible), and updates instruction files with correct counts.

4. **Run tests**:
   ```bash
   source .venv/bin/activate && python -m pytest tests/unit/ -q
   ```
   Fix any count mismatches in hardcoded test assertions if needed.

5. **Update README.md** skill counts if they changed.

6. **Check off the Registration Checklist** from Start Here.

---

## Mode: agent <name>

Follow `handlers/create-agent.md` for the full scaffold procedure.

Agents don't go through skill-creator (they're not skills). Create them directly:

1. **Define mandate** — what is this agent's singular responsibility? An agent does ONE thing.

2. **Load pain sources** — same as skill Phase 1. Check decision-store for constraints on agent architecture (e.g., DEC-019 agent boundaries).

3. **Scaffold** — create `.codex/agents/ai-{name}.md` with:
   - Identity (role, experience level, specialization)
   - Mandate (what it owns, what it does not own)
   - Capabilities (declared permissions: read-only, read-write, which files/paths)
   - Behavior (modes, procedures)
   - Output Contract (structured format the agent always produces)
   - Boundaries (hard limits, escalation protocol)
   - Self-challenge protocol (questions the agent asks itself before acting)

4. **Register** — add to `manifest.yml` agents section (names array + total count).

5. **Create matching skill** — if this agent needs a `/ai-{name}` entry point, create a minimal skill that activates it. Use `/ai-create skill {name}` for that (which delegates to skill-creator).

6. **Sync and test** — same as skill Phase 3 steps 3-6.

---

## CSO Description Patterns

The `description` field is the skill's search ranking — it determines whether the skill triggers. It must describe **triggering conditions**, not summarize functionality.

| Bad (summary) | Good (CSO trigger) |
|---------------|-------------------|
| "Generates standup notes" | "Use when preparing daily standup notes or summarizing recent PR activity" |
| "Sprint planning tool" | "Use when planning a new sprint or running a retrospective" |
| "Resolves git conflicts" | "Use when git reports merge conflicts during rebase, merge, or cherry-pick" |

## IDE-Compatibility Frontmatter

| Field | Type | Value | Effect |
|-------|------|-------|--------|
| `copilot_compatible` | bool | `false` | Excludes skill from `.github/skills/` mirror |
| `disable-model-invocation` | bool | `true` | Tells GitHub Copilot not to invoke LLM (script-only skills) |

**When to set:**
- Most skills: omit both (mirrors to all IDEs)
- Claude Code-only skills: set `copilot_compatible: false`
- Script-only skills: also set `disable-model-invocation: true`

Currently only `ai-analyze-permissions` uses `copilot_compatible: false`.

## Handlers

| Handler | Phase | File |
|---------|-------|------|
| Skill scaffold | Phase 1 | `handlers/create-skill.md` |
| Agent scaffold | Phase 2 | `handlers/create-agent.md` |
| Validation | Phase 3 | `handlers/validate.md` |
| Shell scaffold | Phase 1 | `scripts/scaffold-skill.sh` |

## Quick Reference

```
/ai-create skill standup     # create a new standup skill (delegates TDD to skill-creator)
/ai-create agent reviewer    # create a new reviewer agent (direct scaffold)
```

## Integration

- **Delegates to**: Anthropic `skill-creator` for skill TDD, evals, description optimization
- **Reads**: manifest.yml, decision-store.json, LESSONS.md (ai-engineering context)
- **Triggers sync**: `python scripts/sync_command_mirrors.py` after creation
- **Related**: `/ai-skill-evolve` for improving existing skills (also delegates to skill-creator)

$ARGUMENTS
