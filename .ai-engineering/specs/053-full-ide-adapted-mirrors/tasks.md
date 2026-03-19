---
spec: "053"
total: 22
completed: 0
last_session: "2026-03-16"
next_session: "2026-03-16"
---

# Tasks — Spec 053

## Phase 1: Core Generator [L]

- [ ] T-001: Change SKILLS_ROOT/AGENTS_ROOT to read from templates canonical
- [ ] T-002: New function `read_canonical_body(path)` — strip YAML frontmatter, return body
- [ ] T-003: New function `transform_cross_references(content, target_ide)` — translate paths per IDE
- [ ] T-004: Rewrite `generate_claude_skill()` — full canonical content + Claude frontmatter
- [ ] T-005: Rewrite `generate_claude_agent_activation()` — full agent content + skill frontmatter
- [ ] T-006: New function `generate_claude_agent()` — replaces validate-only, full content + Claude frontmatter
- [ ] T-007: Rewrite `generate_copilot_agent()`, `generate_agents_agent()`, `generate_skill_copilot_prompt()` — full content
- [ ] T-008: Update `sync_all()` — generate .claude/agents/ + templates/project/ surfaces

**Phase 1 Gate**: `python scripts/sync_command_mirrors.py` generates FULL content, `--check` passes

## Phase 2: Delete Canonical from Framework Repo [S]

- [ ] T-009: Delete `.ai-engineering/agents/` and `.ai-engineering/skills/` directories
- [ ] T-010: Update CLAUDE.md and AGENTS.md refs to IDE-specific paths

**Phase 2 Gate**: `test ! -d .ai-engineering/agents && test ! -d .ai-engineering/skills` → exit 0

## Phase 3: Installer Exclusion [S]

- [ ] T-011: Add `exclude` parameter to `copy_template_tree()` in `installer/templates.py`
- [ ] T-012: Pass `exclude=["agents/", "skills/"]` in `installer/service.py`

**Phase 3 Gate**: `ai-eng install` in tmp_path does NOT create .ai-engineering/agents/ or skills/

## Phase 4: Ownership Model [S]

- [ ] T-013: Remove `.ai-engineering/skills/**` and `.ai-engineering/agents/**` patterns from defaults.py

## Phase 5: Validators [M]

- [ ] T-014: Update skill_frontmatter.py, cross_references.py, manifest_coherence.py to scan IDE dirs
- [ ] T-015: Update _shared.py mirror globs and path patterns

## Phase 6: Skills Service + CLI [S]

- [ ] T-016: Update skills/service.py to scan IDE dirs; update CLI message

## Phase 7: Instruction Files [S]

- [ ] T-017: Translate refs in template CLAUDE.md, AGENTS.md, copilot-instructions.md, copilot/*

## Phase 8: Migration [M]

- [ ] T-018: Add legacy detection and migration in updater/service.py
- [ ] T-019: Add exclude in _evaluate_governance_files()

## Phase 9: Tests [L]

- [ ] T-020: Update test_sync_mirrors.py — full content expectations + new function tests
- [ ] T-021: Update test_real_project_integrity.py, test_validator.py, test_installer.py, e2e tests

## Phase 10: Apply + Verify [S]

- [ ] T-022: Regenerate all mirrors, run all 14 ACs

**Final Gate**: All 14 ACs pass (see spec.md)
