---
spec: "031"
approach: "serial-phases"
---

# Plan — Architecture Refactor: Agents, Skills & Standards

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `.ai-engineering/agents/plan.md` | Orchestration + planning pipeline agent |
| `.ai-engineering/agents/build.md` | Implementation agent (only code read-write) |
| `.ai-engineering/agents/review.md` | Reviews + governance agent (individual modes) |
| `.ai-engineering/agents/scan.md` | Feature scanner + architecture analyzer agent |
| `.ai-engineering/agents/write.md` | Documentation agent |
| `.ai-engineering/agents/triage.md` | Auto-prioritization agent |
| `.ai-engineering/skills/work-item/SKILL.md` | Azure Boards + GitHub Issues integration |
| `.ai-engineering/skills/agent-card/SKILL.md` | Platform-portable agent descriptors |
| `.ai-engineering/skills/triage/SKILL.md` | Prioritization logic |
| `.github/agents/plan.agent.md` | Copilot agent mirror — plan |
| `.github/agents/build.agent.md` | Copilot agent mirror — build |
| `.github/agents/review.agent.md` | Copilot agent mirror — review |
| `.github/agents/scan.agent.md` | Copilot agent mirror — scan |
| `.github/agents/write.agent.md` | Copilot agent mirror — write |
| `.github/agents/triage.agent.md` | Copilot agent mirror — triage |

### Modified Files

| File | Change |
|------|--------|
| `.ai-engineering/manifest.yml` | agents 6, skills 47, flat org, `work_items` section |
| `.ai-engineering/standards/framework/skills-schema.md` | remove `category` required, add `platforms`, update inventory |
| `CLAUDE.md` | 6 agents, 47 skills, `/ai:*` commands |
| `AGENTS.md` | 6 agents, new command contract, updated lifecycle |
| `.github/copilot-instructions.md` | Updated agent/skill references |
| 44 SKILL.md files | move + rename + update frontmatter |
| 44+ `.github/prompts/` files | rename to `ai-<name>.prompt.md` |
| `.claude/commands/` | restructure to `ai/<name>.md` |

### Mirror Copies

| Source | Mirror |
|--------|--------|
| `.ai-engineering/agents/*.md` | `src/ai_engineering/templates/.ai-engineering/agents/*.md` |
| `.ai-engineering/skills/*/SKILL.md` | `src/ai_engineering/templates/.ai-engineering/skills/*/SKILL.md` |
| `.ai-engineering/manifest.yml` | `src/ai_engineering/templates/.ai-engineering/manifest.yml` |
| `.ai-engineering/standards/` | `src/ai_engineering/templates/.ai-engineering/standards/` |

### Delete (~160+ files)

| Category | Count | Pattern |
|----------|-------|---------|
| Old agent files | 19 | `.ai-engineering/agents/<old-name>.md` |
| Old copilot agents | 19 | `.github/agents/<old-name>.agent.md` |
| Old claude commands | ~50 | `.claude/commands/{agent,dev,docs,govern,quality,review,workflows}/` |
| Old template agents | 19 | `src/ai_engineering/templates/.ai-engineering/agents/<old-name>.md` |
| Old template skills | ~70 | `src/ai_engineering/templates/.ai-engineering/skills/<category>/<name>/` |
| Old prompts | ~46 | `.github/prompts/<old-prefix>-*.prompt.md` |
| Empty category dirs | 6 | `.ai-engineering/skills/{workflows,dev,review,quality,docs,govern}/` |

## File Structure

```
.ai-engineering/
  agents/
    plan.md          # 6 agents (was 19)
    build.md
    review.md
    scan.md
    write.md
    triage.md
  skills/            # flat (was 6 category subdirs)
    commit/SKILL.md
    pr/SKILL.md
    cleanup/SKILL.md
    improve/SKILL.md
    debug/SKILL.md
    refactor/SKILL.md
    code-review/SKILL.md
    ... (47 total)
    work-item/SKILL.md    # NEW
    agent-card/SKILL.md   # NEW
    triage/SKILL.md       # NEW

.claude/commands/
  ai/                # unified namespace
    commit.md
    pr.md
    cleanup.md
    ... (47 skill commands)
    plan.md          # agent commands
    build.md
    review.md
    scan.md
    write.md
    triage.md

.github/
  agents/
    plan.agent.md    # 6 agents
    build.agent.md
    review.agent.md
    scan.agent.md
    write.agent.md
    triage.agent.md
  prompts/
    ai-commit.prompt.md
    ai-pr.prompt.md
    ... (47 + 4 workflow prompts)
```

## Session Map

### Phase 0: Scaffold [S]
- Create spec, branch, activate.

### Phase 1: Author 6 New Agents [L]
- Write `agents/plan.md` — orchestrator v2 + planning pipeline.
- Write `agents/build.md` — merges 8 implementation agents, skill-routing protocol.
- Write `agents/review.md` — merges 6 review agents, individual modes.
- Write `agents/scan.md` — feature scanner (spec-vs-code gap analysis).
- Write `agents/write.md` — documentation + test docs.
- Write `agents/triage.md` — auto-prioritization.

### Phase 2: Restructure 44 Skills [L]
- For each skill: move from `skills/<category>/<old-name>/` → `skills/<new-name>/`.
- Update each SKILL.md: `name`, remove `category`, bump version.
- Move any sub-dirs (scripts/, references/, assets/).

### Phase 3: Author 3 New Skills [M]
- Write `skills/work-item/SKILL.md`.
- Write `skills/agent-card/SKILL.md`.
- Write `skills/triage/SKILL.md`.

### Phase 4: Update Standards + Manifest [M]
- Update `skills-schema.md`: remove `category` required, add `platforms`, update inventory.
- Update `manifest.yml`: agents 6, skills 47, flat org, `work_items` section.

### Phase 5: External Integration [L]
- `.github/agents/`: create 6 new.
- `.github/prompts/`: rename 44 + create 3 new.
- `.claude/commands/`: restructure to `ai/<name>.md`.

### Phase 6: Instruction Files [M]
- Update `CLAUDE.md`, `AGENTS.md`.
- Update `.github/copilot-instructions.md`, `.github/copilot/` files.
- Update all cross-references in skill bodies.

### Phase 7: Template Mirrors [L]
- Update all `src/ai_engineering/templates/` to match new structure byte-identical.

### Phase 8: Delete Old Files [L]
- Delete 19 old agent files + mirrors + copilot agents + claude commands.
- Delete empty category directories.
- ~160+ files deleted/moved.

### Phase 9: Verification [M]
- Integrity-check.
- `ruff check` + `ruff format --check`.
- Zero orphaned references (grep for all old names).
- Count verification: 6 agents, 47 skills everywhere.
- CHANGELOG + done.md + PR.

## Patterns

- **Atomic commits**: one commit per phase (`spec-031: Phase N — <description>`).
- **Move-then-update**: `git mv` for renames, then update frontmatter — preserves git history.
- **Mirror-last**: update source files first, copy to templates as a separate phase.
- **Delete-last**: remove old files only after all new files are verified.
- **Parallel sub-phases**: within a phase, independent skill moves can be parallelized.
