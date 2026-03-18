---
spec: "053"
approach: "serial-phases"
---

# Plan — Full IDE-Adapted Mirrors

## Architecture

### Changed Files

| File | Change | Phase |
|------|--------|-------|
| `scripts/sync_command_mirrors.py` | Rewrite 6 generate functions + 3 new functions + update sync_all() | 1 |
| `.ai-engineering/agents/` | DELETE (canonical in templates/) | 2 |
| `.ai-engineering/skills/` | DELETE (canonical in templates/) | 2 |
| `CLAUDE.md` | Translate refs to .claude/ paths | 2 |
| `AGENTS.md` | Translate refs to .agents/ paths | 2 |
| `src/ai_engineering/installer/templates.py` | Add exclude param to copy_template_tree() | 3 |
| `src/ai_engineering/installer/service.py` | Pass exclude=["agents/", "skills/"] | 3 |
| `src/ai_engineering/state/defaults.py` | Remove .ai-engineering/agents/** and skills/** ownership | 4 |
| `src/ai_engineering/validator/categories/skill_frontmatter.py` | Scan IDE dirs instead of .ai-engineering/skills/ | 5 |
| `src/ai_engineering/validator/categories/cross_references.py` | Iterate IDE dirs | 5 |
| `src/ai_engineering/validator/categories/manifest_coherence.py` | Don't require agents/ skills/ in .ai-engineering/ | 5 |
| `src/ai_engineering/validator/_shared.py` | Update mirror globs and path patterns | 5 |
| `src/ai_engineering/skills/service.py` | Scan IDE dirs for skill eligibility | 6 |
| `src/ai_engineering/cli_commands/skills.py` | Path-agnostic message | 6 |
| `src/ai_engineering/templates/project/CLAUDE.md` | Translate refs to .claude/ | 7 |
| `src/ai_engineering/templates/project/AGENTS.md` | Translate refs to .agents/ | 7 |
| `src/ai_engineering/templates/project/copilot-instructions.md` | Translate refs to .github/ | 7 |
| `src/ai_engineering/updater/service.py` | Add migration logic + exclude agents/skills | 8 |
| `tests/unit/test_sync_mirrors.py` | Update expected output, add new tests | 9 |
| `tests/unit/test_real_project_integrity.py` | Validate IDE dirs | 9 |
| `tests/e2e/test_install_clean.py` | Remove agents/skills expectations | 9 |
| `tests/unit/test_validator.py` | Update fixtures | 9 |
| `tests/unit/test_installer.py` | Test exclude param | 9 |

## Session Map

### Phase 1: Core Generator [L]

**Agent**: build

Rewrite `scripts/sync_command_mirrors.py`:
1. Change SKILLS_ROOT/AGENTS_ROOT to read from `src/ai_engineering/templates/.ai-engineering/`
2. New: `read_canonical_body()`, `transform_cross_references()`
3. Rewrite: all 6 generate functions (thin → full embed)
4. New: `generate_claude_agent()` (replaces validate-only)
5. Update: `sync_all()` to generate in templates/project/ too

### Phase 2: Delete Canonical from Framework Repo [S]

**Agent**: build

1. Delete `.ai-engineering/agents/` and `.ai-engineering/skills/`
2. Update CLAUDE.md, AGENTS.md refs

### Phase 3: Installer Exclusion [S]

**Agent**: build

1. Add `exclude` param to `copy_template_tree()`
2. Pass `exclude=["agents/", "skills/"]` in install()

### Phase 4: Ownership Model [S]

**Agent**: build

1. Remove obsolete patterns from defaults.py
2. Verify IDE dir coverage

### Phase 5: Validators [M]

**Agent**: build

1. skill_frontmatter.py — scan IDE dirs
2. cross_references.py — iterate IDE dirs
3. manifest_coherence.py — don't require agents/skills in .ai-engineering/
4. _shared.py — update mirror globs and patterns

### Phase 6: Skills Service [S]

**Agent**: build

1. Scan IDE dirs for skill status
2. Path-agnostic CLI messages

### Phase 7: Instruction Files [S]

**Agent**: build

1. Translate refs in template CLAUDE.md, AGENTS.md, copilot-instructions.md

### Phase 8: Migration [M]

**Agent**: build

1. Detect legacy structure in updater
2. Migrate agents/skills to IDE dirs
3. Exclude in governance evaluation

### Phase 9: Tests [L]

**Agent**: build

1. test_sync_mirrors.py — full content expectations
2. test_real_project_integrity.py — IDE dir validation
3. test_install_clean.py — no agents/skills expectations
4. test_validator.py — IDE dir fixtures
5. test_installer.py — exclude param tests

### Phase 10: Apply + Verify [S]

**Agent**: build

1. Regenerate all mirrors
2. Run all verification commands from ACs

## Patterns

- One commit per phase: `spec-053: Phase N — description`
- Sync script changes FIRST (Phase 1) — everything else depends on generation
- Delete canonical SECOND (Phase 2) — ensures we're committed to new architecture
- Tests LAST (Phase 9) — after all code changes are stable
