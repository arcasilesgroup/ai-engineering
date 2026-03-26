---
id: sub-006
parent: spec-080
title: "AGENTS.md Single-Source Generation"
status: planning
files: ["scripts/sync_command_mirrors.py", "AGENTS.md", "CLAUDE.md", ".github/copilot-instructions.md", "src/ai_engineering/templates/project/AGENTS.md", "src/ai_engineering/templates/project/copilot-instructions.md", "src/ai_engineering/validator/_shared.py", "src/ai_engineering/validator/categories/mirror_sync.py"]
depends_on: [sub-001]
---

# Sub-Spec 006: AGENTS.md Single-Source Generation

## Scope
Extend sync_command_mirrors.py to generate AGENTS.md and copilot-instructions.md from CLAUDE.md as canonical source. Strip Claude-specific references for AGENTS.md, add Copilot-specific subagent orchestration for copilot-instructions.md. Fix template agent paths. Add validator content parity check. Remove AGENTS.md `# CLAUDE.md` title. Restore 5 missing items. Update CLAUDE.md Effort Levels table and skill group listings when new skills exist on disk.

## Exploration

### Current State

**sync_command_mirrors.py** (1194 lines) generates mirrors across 6 surfaces:
1. `.agents/skills/` and `.agents/agents/` (generic IDE)
2. `.github/skills/` and `.github/agents/` (Copilot)
3. `src/ai_engineering/templates/project/.claude/`, `.agents/`, `.github/` (install templates)
4. `instructions/{lang}.instructions.md` (from language contexts)

It does NOT generate AGENTS.md, copilot-instructions.md, or their template copies. These 4 files are hand-maintained and have drifted.

**Key functions to extend:**
- `sync_all()` orchestrates all surfaces (phases 1-4: validate, generate, orphan detect, summary)
- `translate_refs()` handles `.claude/` path translation to target IDE
- `_generate_surface()` writes/checks a single file
- `_check_or_write()` handles diff detection and file writing

**CLAUDE.md vs AGENTS.md -- 5 confirmed missing items:**

| # | Missing from AGENTS.md | CLAUDE.md location |
|---|------------------------|-------------------|
| 1 | `project-identity.md` read instruction | Line 10, Workflow Orchestration |
| 2 | `### 10. Context Loading` subsection (entire 8-line block) | Lines 68-76 |
| 3 | Autopilot row in Agent Selection table | Line 104 |
| 4 | `## Effort Levels` section (entire 10-line block with 3-tier table) | Lines 127-136 |
| 5 | `UserPromptSubmit(/ai-*)` hook name (AGENTS.md has stale `PostToolUse(Skill)`) | Line 155 |

**Root copilot-instructions.md vs template copilot-instructions.md:**
- Root (correct): `.github/agents/<name>.agent.md`
- Template (wrong): `.github/agents/ai-<name>.agent.md`
- Actual files on disk: `<name>.agent.md` (no `ai-` prefix)
- Root has Subagent Orchestration section and correct hook event names; template is stale.

**Validator current state:**
- `counter_accuracy.py` checks skill/agent counts across instruction files (uses `_extract_listings()`)
- `mirror_sync.py` checks SHA-256 parity for governance, commands, skills, agents directories
- No parity check exists for CLAUDE.md <-> AGENTS.md <-> copilot-instructions.md section content
- `_shared.py` defines `_BASE_INSTRUCTION_FILES` list: `[".github/copilot-instructions.md", "AGENTS.md", "CLAUDE.md"]`

**Skill count:** 38 skills on disk. CLAUDE.md lists 38. The scope mentions updating to 41 (add ai-code, ai-docs, ai-board-discover, ai-board-sync; remove ai-solution-intent) -- these changes must come from other sub-specs that create the actual skill files. This sub-spec should generate from whatever skills exist on disk at runtime.

### Generation Strategy

**AGENTS.md generation from CLAUDE.md:**
1. Read CLAUDE.md content
2. Replace title `# CLAUDE.md` with `# AGENTS.md` (or a neutral title)
3. Strip Claude-specific references (`.claude/settings.json` deny rules in Don't section item 7)
4. Translate all `.claude/` paths to `.agents/` paths via existing `translate_refs(content, "generic")`
5. Keep all sections intact (no more drift)

**copilot-instructions.md generation from CLAUDE.md:**
1. Read CLAUDE.md content
2. Strip to essential sections (copilot-instructions.md is intentionally condensed)
3. Translate paths via `translate_refs(content, "copilot")`
4. Append Copilot-specific Subagent Orchestration section (from AGENT_METADATA)
5. Append Copilot-specific Observability section (hook event names)

**Template copies:** Both templates are identical to their root counterparts (generated in same pass).

### Constraints

- CLAUDE.md is the single canonical source -- AGENTS.md and copilot-instructions.md are derived
- The generation must be idempotent (running sync twice produces same output)
- Template copies must be byte-identical to root copies
- Validator parity check should compare section-level content, not byte-level (since path translations change bytes)
- imports: CLAUDE.md governance values from sub-001 (Don't section, Core Principles)
- exports: generated AGENTS.md, generated copilot-instructions.md, updated CLAUDE.md skill listings
