---
total: 5
completed: 0
---

# Plan: sub-006 AGENTS.md Single-Source Generation

## Plan

### T-6.1: Add AGENTS.md generation to sync_command_mirrors.py

Add a new generation function and surface entry that produces `AGENTS.md` from `CLAUDE.md` as canonical source. The generator must:

1. Read CLAUDE.md content
2. Replace title `# CLAUDE.md` with the project's generic multi-IDE heading (no `# CLAUDE.md` title leak)
3. Translate `.claude/` path references to `.agents/` paths using existing `translate_refs(content, "generic")`
4. Strip Claude-specific item: Don't section item 7 references `.claude/settings.json` deny rules (Claude Code specific -- not relevant for generic IDE)
5. Write to both `AGENTS.md` (root) and `src/ai_engineering/templates/project/AGENTS.md` (template)

This restores all 5 missing items automatically since they exist in CLAUDE.md and the generation is full-content, not selective. The stale `PostToolUse(Skill)` hook name in AGENTS.md gets replaced by the canonical `UserPromptSubmit(/ai-*)` from CLAUDE.md.

**Files:**
- `scripts/sync_command_mirrors.py` -- add `generate_agents_md()` function, add Surface 7 block in `sync_all()`
- `AGENTS.md` -- now generated (no manual edits)
- `src/ai_engineering/templates/project/AGENTS.md` -- now generated (byte-identical to root)

**Done:** `python scripts/sync_command_mirrors.py --check` reports AGENTS.md and template as in-sync. Root AGENTS.md contains all 5 previously missing items. Title is NOT `# CLAUDE.md`.

---

### T-6.2: Add copilot-instructions.md generation to sync_command_mirrors.py

Add a generation function that produces `.github/copilot-instructions.md` from CLAUDE.md as canonical source, plus Copilot-specific additions.

The generator must:

1. Read CLAUDE.md content
2. Produce a condensed version with these sections:
   - Source of Truth (condensed to bullet list)
   - Session Start Protocol (adapted from Workflow Orchestration + Context Loading)
   - Plan/Execute Flow (from Task Management)
   - Absolute Prohibitions (from Don't section, excluding Claude-specific items)
   - Observability (with Copilot hook event names: sessionStart, sessionEnd, userPromptSubmitted, preToolUse, postToolUse, errorOccurred)
   - Subagent Orchestration table (generated from `AGENT_METADATA` -- extract `copilot_agents`, `copilot_handoffs` to build orchestrator/delegates/handoffs table)
   - Quick Reference (skill/agent counts and paths, using `.github/` paths)
3. Translate all paths via `translate_refs(content, "copilot")`
4. Write to both `.github/copilot-instructions.md` (root) and `src/ai_engineering/templates/project/copilot-instructions.md` (template)

**Files:**
- `scripts/sync_command_mirrors.py` -- add `generate_copilot_instructions()` function, add Surface 8 block in `sync_all()`
- `.github/copilot-instructions.md` -- now generated
- `src/ai_engineering/templates/project/copilot-instructions.md` -- now generated, fixes the `ai-<name>.agent.md` path bug (correct: `<name>.agent.md`)

**Done:** `python scripts/sync_command_mirrors.py --check` reports copilot-instructions.md files as in-sync. Template no longer has wrong `ai-` prefix in agent paths. Subagent Orchestration table is auto-generated from AGENT_METADATA.

---

### T-6.3: Add instruction file parity check to validator

Add a new check in the validator that verifies CLAUDE.md, AGENTS.md, and copilot-instructions.md share consistent content sections. This is section-level parity (not byte-level, since path translations differ).

The check should verify:

1. **Skill listings parity** -- all instruction files list the same set of skill names (already exists in `counter_accuracy.py` but only checks counts, not names across all files)
2. **Agent listings parity** -- same agent names across all instruction files
3. **Section presence** -- AGENTS.md contains all non-Claude-specific sections from CLAUDE.md (Workflow Orchestration, Task Management, Core Principles, Agent Selection, Skills, Effort Levels, Quality Gates, Observability, Don't, Source of Truth)
4. **Count consistency** -- skill/agent counts in section headers match manifest.yml

This builds on existing `_extract_listings()` and `_extract_section()` in `_shared.py`. The new check belongs in `counter_accuracy.py` or as a new function in `mirror_sync.py` since it validates derived-file parity.

**Files:**
- `src/ai_engineering/validator/categories/mirror_sync.py` -- add `_check_instruction_parity()` function called from `_check_mirror_sync()`
- `src/ai_engineering/validator/_shared.py` -- add section extraction constants if needed

**Done:** `ai-eng doctor` runs the parity check and passes. Removing a section from AGENTS.md manually and re-running causes a FAIL.

---

### T-6.4: Update CLAUDE.md skill listings and effort table for current disk state

Update CLAUDE.md sections to reflect the actual skills on disk. Currently 38 skills. If other sub-specs have added/removed skills by execution time, the counts and listings should match what `discover_skills()` finds.

Specific updates:
1. `## Skills (N)` -- update N and group listings to match disk
2. `## Effort Levels` -- update effort tier counts and listings to match skill frontmatter on disk
3. `## Source of Truth` -- update `Skills (N)` count
4. Template CLAUDE.md (`src/ai_engineering/templates/project/CLAUDE.md`) must match root

This task runs AFTER T-6.1 and T-6.2 so the generated AGENTS.md and copilot-instructions.md automatically pick up the updated counts.

**Files:**
- `CLAUDE.md` -- update skill count, group listings, effort table
- `src/ai_engineering/templates/project/CLAUDE.md` -- mirror of root

**Done:** `python scripts/sync_command_mirrors.py --check` passes. Skill counts in CLAUDE.md match `discover_skills()` output. Effort Levels table sums to total skill count.

---

### T-6.5: Verify end-to-end generation and validator pass

Run full verification to confirm all changes work together:

1. `python scripts/sync_command_mirrors.py` -- generates all surfaces including new AGENTS.md and copilot-instructions.md
2. `python scripts/sync_command_mirrors.py --check` -- confirms zero drift
3. `ruff check scripts/sync_command_mirrors.py` -- no lint errors
4. `ruff check src/ai_engineering/validator/` -- no lint errors
5. `pytest tests/ -k "validator or sync"` -- all tests pass
6. Manual inspection: AGENTS.md title is NOT `# CLAUDE.md`, contains all 5 previously missing items, template copilot-instructions.md uses correct `<name>.agent.md` paths

**Files:**
- All files from T-6.1 through T-6.4

**Done:** All checks pass. Zero drift. Zero lint errors. Tests green.

## Confidence

| Task | Confidence | Risk |
|------|-----------|------|
| T-6.1 | HIGH | Low -- straightforward extension of existing generation pattern |
| T-6.2 | MEDIUM | Medium -- copilot-instructions.md condensation logic requires careful section mapping; Subagent Orchestration table generation from AGENT_METADATA is new |
| T-6.3 | MEDIUM | Medium -- section-level parity is harder than byte-level; needs clear definition of what "parity" means for condensed files |
| T-6.4 | HIGH | Low -- reading frontmatter and counting is well-established pattern |
| T-6.5 | HIGH | Low -- verification only |

Overall confidence: **HIGH** -- all tasks extend existing, well-understood patterns in sync_command_mirrors.py and the validator.

## Self-Report
[EMPTY -- populated by Phase 4]
