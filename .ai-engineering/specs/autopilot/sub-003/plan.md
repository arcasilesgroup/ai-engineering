---
total: 29
completed: 29
---

# Plan: sub-003 Project Identity — replace contracts

## Pipeline: full
## Phases: 6
## Tasks: 29 (build: 29)

### Phase 1: Delete old contract templates
**Gate**: No `framework-contract.md`, `product-contract.md`, or `contexts/product/` directory exist in templates.

- [x] T-1.1: Delete template contract files and product/ directory
  **Files**:
  - DELETE `src/ai_engineering/templates/.ai-engineering/contexts/product/framework-contract.md`
  - DELETE `src/ai_engineering/templates/.ai-engineering/contexts/product/product-contract.md`
  - DELETE `src/ai_engineering/templates/.ai-engineering/contexts/product/` (entire directory)
  **Done**: `ls src/ai_engineering/templates/.ai-engineering/contexts/product/` returns "No such file or directory". The `contexts/` directory still exists with other content (languages/, frameworks/, team/).

### Phase 2: Create project-identity.md template + dogfood
**Gate**: `project-identity.md` exists in both template and dogfood locations with correct structure.

- [x] T-2.1: Create project-identity.md template
  **Files**:
  - CREATE `src/ai_engineering/templates/.ai-engineering/contexts/project-identity.md`
  **Content**: Generic template with placeholder sections (Project, Services & APIs, Dependencies & Consumers, Boundaries). Use `[project name]` placeholders, NOT ai-engineering-specific content. ~30-50 lines.
  **Done**: File exists, contains all 4 sections, has no ai-engineering-specific data, uses generic placeholders.

- [x] T-2.2: Create project-identity.md dogfood
  **Files**:
  - CREATE `.ai-engineering/contexts/project-identity.md`
  **Content**: Filled-in version for the ai-engineering project itself: Name=ai-engineering, Purpose=governance framework for AI-assisted development, Services=CLI (ai-eng), Skills, Agents. Boundaries: never overwrite team-managed content, never weaken quality gates.
  **Done**: File exists, contains ai-engineering-specific data, all 4 sections populated.

### Phase 3: Create ai-project-identity skill (6 mirrors)
**Gate**: Skill exists in all 3 IDE mirror locations plus their template mirrors. Frontmatter valid.

- [x] T-3.1: Create ai-project-identity SKILL.md for Claude Code
  **Files**:
  - CREATE `.claude/skills/ai-project-identity/SKILL.md`
  **Content**: Frontmatter (name: ai-project-identity, description, effort: medium, argument-hint). Sections: Purpose (generate/maintain project-identity.md), When to Use (first install, project scope changes), Procedure (1. auto-detect from manifest/package files, 2. Q&A for what cannot be inferred, 3. write to contexts/project-identity.md), Quick Reference, Integration. Follow ai-note SKILL.md as pattern.
  **Done**: File exists, frontmatter parses correctly, has name/description/effort fields, contains Purpose/Procedure/Integration sections.

- [x] T-3.2: Create ai-project-identity mirrors for GitHub Copilot and Codex/Gemini
  **Files**:
  - CREATE `.github/skills/ai-project-identity/SKILL.md` (same content as Claude Code version)
  - CREATE `.agents/skills/project-identity/SKILL.md` (same content, directory name without `ai-` prefix per .agents convention)
  **Done**: Both files exist with identical content to T-3.1.

- [x] T-3.3: Create ai-project-identity template mirrors
  **Files**:
  - CREATE `src/ai_engineering/templates/project/.claude/skills/ai-project-identity/SKILL.md`
  - CREATE `src/ai_engineering/templates/project/.github/skills/ai-project-identity/SKILL.md`
  - CREATE `src/ai_engineering/templates/project/.agents/skills/project-identity/SKILL.md`
  **Done**: All 3 files exist, content identical to their canonical counterparts from T-3.1 and T-3.2.

### Phase 4: Update instruction files, manifests, and skill references
**Gate**: All instruction files say "38 skills", all manifests register ai-project-identity, governance skill references project-identity.md, copilot-instructions.md has no framework-contract reference.

- [x] T-4.1: Update CLAUDE.md (repo root) -- counts, skill list, effort table, loading instruction
  **Files**:
  - EDIT `CLAUDE.md`
  **Changes**:
  1. In Workflow Orchestration section, after the "Read the decision store" line, add: `Before writing code or designing features, read .ai-engineering/contexts/project-identity.md if it exists.`
  2. `## Skills (37)` -> `## Skills (38)`
  3. In Meta line, add `project-identity` to the list
  4. Effort table medium: add `project-identity` to the list, update count from `11` to `12`
  5. Source of Truth table: `Skills (37)` -> `Skills (38)`
  **Done**: All 5 changes applied. `grep -c "Skills (38)" CLAUDE.md` returns 2. `grep "project-identity" CLAUDE.md` shows entries in skill list, effort table, and loading instruction.

- [x] T-4.2: Update template CLAUDE.md -- same changes as T-4.1
  **Files**:
  - EDIT `src/ai_engineering/templates/project/CLAUDE.md`
  **Changes**: Identical to T-4.1 (template must mirror repo root CLAUDE.md).
  **Done**: Content is identical to repo root CLAUDE.md after edits.

- [x] T-4.3: Update AGENTS.md (repo root) -- counts and skill list
  **Files**:
  - EDIT `AGENTS.md`
  **Changes**:
  1. `## Skills (37)` -> `## Skills (38)`
  2. In Meta line, add `project-identity` to the list
  3. Source of Truth table: `Skills (37)` -> `Skills (38)`
  **Done**: `grep -c "Skills (38)" AGENTS.md` returns 2.

- [x] T-4.4: Update template AGENTS.md -- same changes as T-4.3
  **Files**:
  - EDIT `src/ai_engineering/templates/project/AGENTS.md`
  **Done**: Content mirrors repo root AGENTS.md after edits.

- [x] T-4.5: Update .github/copilot-instructions.md -- count and loading instruction
  **Files**:
  - EDIT `.github/copilot-instructions.md`
  **Changes**:
  1. `Skills (37)` -> `Skills (38)` in Quick Reference section
  2. In Session Start Protocol, add reading project-identity.md instruction
  **Done**: `grep "Skills (38)" .github/copilot-instructions.md` matches. Loading instruction present.

- [x] T-4.6: Update template copilot-instructions.md -- count, loading, remove framework-contract ref, fix path
  **Files**:
  - EDIT `src/ai_engineering/templates/project/copilot-instructions.md`
  **Changes**:
  1. DELETE line 7: `- Governance rules: .ai-engineering/context/product/framework-contract.md` (dead reference, wrong path)
  2. `Skills (37)` -> `Skills (38)` in Quick Reference section
  3. Add project-identity.md loading instruction in Session Start Protocol
  **Done**: No `framework-contract` reference exists. No `context/product` path exists (was the wrong path anyway). `grep "Skills (38)"` matches.

- [x] T-4.7: Update both manifest.yml files -- total, registry, comment
  **Files**:
  - EDIT `.ai-engineering/manifest.yml`
  - EDIT `src/ai_engineering/templates/.ai-engineering/manifest.yml`
  **Changes** (both files, identical):
  1. Comment: `# Skills registry (37 skills)` -> `# Skills registry (38 skills)`
  2. `total: 37` -> `total: 38`
  3. After `ai-autopilot` entry, add: `ai-project-identity: { type: meta, tags: [governance] }`
  **Done**: Both files have `total: 38`, both have `ai-project-identity` in registry, comment matches.

- [x] T-4.8: Update ai-brainstorm SKILL.md -- add project-identity to context loading
  **Files**:
  - EDIT `.claude/skills/ai-brainstorm/SKILL.md`
  **Changes**: Step 1 "Load context" -- add `project-identity.md` to the list of files to read: after `decision-store.json`, add `, and .ai-engineering/contexts/project-identity.md (project boundaries)`
  **Done**: Step 1 mentions `project-identity.md`.

- [x] T-4.9: Update ai-brainstorm/handlers/interrogate.md -- add identity as explore context
  **Files**:
  - EDIT `.claude/skills/ai-brainstorm/handlers/interrogate.md`
  **Changes**: In Step 1 "Explore First", add item 5: `Read project identity (.ai-engineering/contexts/project-identity.md) for project boundaries and stakeholders`
  **Done**: Step 1 mentions project-identity.md.

- [x] T-4.10: Update ai-plan SKILL.md -- add project-identity to context loading
  **Files**:
  - EDIT `.claude/skills/ai-plan/SKILL.md`
  **Changes**: Step 2 "Read context" -- add `project-identity.md` to the list.
  **Done**: Step 2 mentions `project-identity.md`.

- [x] T-4.11: Update ai-governance SKILL.md -- replace framework-contract reference in all 4 mirrors
  **Files**:
  - EDIT `.claude/skills/ai-governance/SKILL.md`
  - EDIT `src/ai_engineering/templates/project/.claude/skills/ai-governance/SKILL.md`
  - EDIT `src/ai_engineering/templates/project/.github/skills/ai-governance/SKILL.md`
  - EDIT `src/ai_engineering/templates/project/.agents/skills/governance/SKILL.md`
  - EDIT `.github/skills/ai-governance/SKILL.md`
  - EDIT `.agents/skills/governance/SKILL.md`
  **Changes** (all files): In compliance mode, replace `Validate that rules in \`framework-contract.md\` are enforced.` with `Validate that rules in \`CLAUDE.md\`, \`manifest.yml\`, and boundaries in \`project-identity.md\` are enforced.`
  **Done**: No file contains `framework-contract.md`. All 6 files reference `project-identity.md`.

### Phase 5: Update Python code -- defaults.py, validator migration, cleanup
**Gate**: `instruction_consistency.py` deleted. `counter_accuracy.py` handles all count validation including pointer-format and detailed listings. `defaults.py` has `project-identity.md` ownership rule. `_shared.py` cleaned of dead constants. `service.py` and `categories/__init__.py` updated.

- [x] T-5.1: Update defaults.py -- replace product/** ownership with project-identity.md
  **Files**:
  - EDIT `src/ai_engineering/state/defaults.py`
  **Changes**: Replace the `(".ai-engineering/contexts/product/**", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY)` entry (lines 71-75) with `(".ai-engineering/contexts/project-identity.md", OwnershipLevel.TEAM_MANAGED, FrameworkUpdatePolicy.DENY)`.
  **Done**: No `contexts/product` reference in defaults.py. `contexts/project-identity.md` entry present as TEAM_MANAGED/DENY.

- [x] T-5.2: Migrate _extract_listings and helpers from instruction_consistency.py to _shared.py
  **Files**:
  - EDIT `src/ai_engineering/validator/_shared.py`
  **Changes**: Move these functions from instruction_consistency.py to _shared.py (they are general-purpose helpers needed by counter_accuracy.py):
  - `_extract_listings`
  - `_extract_subsection`
  - `_parse_skill_names_from_subsection`
  - `_parse_agent_names_from_subsection`
  **Done**: All 4 functions exist in _shared.py. counter_accuracy.py can import from _shared.py.

- [x] T-5.3: Migrate pointer-count validation from instruction_consistency.py into counter_accuracy.py
  **Files**:
  - EDIT `src/ai_engineering/validator/categories/counter_accuracy.py`
  **Changes**:
  1. Update import to get `_extract_listings` from `_shared` instead of `instruction_consistency`
  2. The detailed-listing cross-file consistency check (comparing files against each other for identical skill/agent sets) is dropped -- the counter_accuracy check against manifest.yml is the authoritative validation. If files list different counts, that is already caught.
  3. Remove the duplicated regex patterns (`_POINTER_COUNT_RE`, `_POINTER_AGENT_COUNT_RE`) since counter_accuracy already has its own.
  **Done**: counter_accuracy.py imports from _shared, not from instruction_consistency. No import cycle.

- [x] T-5.4: Delete instruction_consistency.py
  **Files**:
  - DELETE `src/ai_engineering/validator/categories/instruction_consistency.py`
  **Done**: File does not exist.

- [x] T-5.5: Update categories/__init__.py -- remove instruction_consistency
  **Files**:
  - EDIT `src/ai_engineering/validator/categories/__init__.py`
  **Changes**: Remove `_check_instruction_consistency` import and __all__ entry.
  **Done**: No reference to `instruction_consistency` in the file.

- [x] T-5.6: Update service.py -- remove INSTRUCTION_CONSISTENCY from checkers
  **Files**:
  - EDIT `src/ai_engineering/validator/service.py`
  **Changes**:
  1. Remove `_check_instruction_consistency` from imports
  2. Remove the `(IntegrityCategory.INSTRUCTION_CONSISTENCY, _check_instruction_consistency)` tuple from the `checkers` list
  3. Remove `_check_instruction_consistency` from `__all__`
  4. Update docstring: "7 content-integrity categories" -> "6 content-integrity categories"
  **Done**: No reference to `instruction_consistency` in service.py. Docstring says 6 categories.

- [x] T-5.7: Update _shared.py -- remove dead constants and enum value
  **Files**:
  - EDIT `src/ai_engineering/validator/_shared.py`
  **Changes**:
  1. Remove `INSTRUCTION_CONSISTENCY = "instruction-consistency"` from IntegrityCategory enum
  2. Remove `_SUBSECTION_PATTERN` (line 195)
  3. Remove `_REQUIRED_SUBSECTIONS` (line 196)
  **Done**: No `INSTRUCTION_CONSISTENCY`, `_SUBSECTION_PATTERN`, or `_REQUIRED_SUBSECTIONS` in _shared.py.

### Phase 6: Update tests
**Gate**: `pytest tests/unit/test_state.py tests/unit/test_validator.py tests/integration/test_gap_fillers4.py tests/e2e/test_install_clean.py` all pass. No references to `product-contract`, `instruction_consistency`, or `contexts/product` in test files.

- [x] T-6.1: Update test_state.py -- replace product test with project-identity test
  **Files**:
  - EDIT `tests/unit/test_state.py`
  **Changes**:
  1. Replace `test_contexts_product_denied` (lines 156-159) with `test_contexts_project_identity_denied`:
     ```python
     def test_contexts_project_identity_denied(self) -> None:
         om = default_ownership_map()
         assert om.is_update_allowed(".ai-engineering/contexts/project-identity.md") is False
         assert om.has_deny_rule(".ai-engineering/contexts/project-identity.md") is True
     ```
  **Done**: No `product` test. New `project_identity` test passes.

- [x] T-6.2: Update test_validator.py -- remove product-contract fixtures, update setup
  **Files**:
  - EDIT `tests/unit/test_validator.py`
  **Changes**:
  1. Remove `_write_product_contract` helper function (lines 114-144)
  2. Remove `_write_product_contract(ai)` call from `_setup_full_project` (line 190)
  3. Remove `_check_instruction_consistency` from any imports if present
  4. Verify `_parse_counter` tests are untouched (they test the parser with literal values, not framework state)
  **Done**: No `product_contract` function. `_setup_full_project` does not call it. All remaining tests pass.

- [x] T-6.3: Update test_gap_fillers4.py -- remove product-contract fixtures
  **Files**:
  - EDIT `tests/integration/test_gap_fillers4.py`
  **Changes**:
  1. Remove lines 262-264 (product_contract directory creation and file write)
  2. Remove lines 352-353 (product-contract.md write)
  3. Remove `IntegrityCategory.INSTRUCTION_CONSISTENCY` from the categories list in the validator call at line 271 (if present)
  4. Remove `context/product` directory creation at line 306
  5. Remove product-contract.md write at lines 352-353
  **Done**: No `product-contract` or `context/product` references in test_gap_fillers4.py.

- [x] T-6.4: Update test_install_clean.py -- replace contexts/product with project-identity.md
  **Files**:
  - EDIT `tests/e2e/test_install_clean.py`
  **Changes**: In `test_install_creates_required_dirs` (line 41-49), replace `"contexts/product"` in the `required` list with a check that `contexts/project-identity.md` file exists. Since project-identity.md is a file (not a directory), may need to add a separate assertion: `assert (ai_dir / "contexts" / "project-identity.md").is_file()`.
  **Done**: No `contexts/product` in the test. `project-identity.md` existence is verified.

- [x] T-6.5: Run full test suite to verify no regressions
  **Files**: None (verification only)
  **Command**: `cd /Users/soydachi/repos/ai-engineering && python -m pytest tests/unit/test_state.py tests/unit/test_validator.py tests/integration/test_gap_fillers4.py tests/e2e/test_install_clean.py -v`
  **Done**: All tests pass. Zero failures.

## Exports (artifacts produced by this sub-spec)

| Artifact | Path | Consumer |
|----------|------|----------|
| project-identity.md template | `src/ai_engineering/templates/.ai-engineering/contexts/project-identity.md` | Installer (governance phase) |
| project-identity.md dogfood | `.ai-engineering/contexts/project-identity.md` | All skills, agents |
| ai-project-identity skill (Claude) | `.claude/skills/ai-project-identity/SKILL.md` | Users, manifest |
| ai-project-identity skill (Copilot) | `.github/skills/ai-project-identity/SKILL.md` | Copilot users |
| ai-project-identity skill (Codex) | `.agents/skills/project-identity/SKILL.md` | Codex/Gemini users |
| Updated manifests (38 skills) | `.ai-engineering/manifest.yml`, template mirror | Validator, skills service |
| Updated instruction files (38 skills) | CLAUDE.md, AGENTS.md, copilot-instructions.md + templates | AI agents, validator |
| Updated defaults.py (project-identity ownership) | `src/ai_engineering/state/defaults.py` | Installer, updater |
| Updated counter_accuracy.py (absorbed instruction_consistency logic) | `src/ai_engineering/validator/categories/counter_accuracy.py` | `ai-eng validate` |

## Imports (artifacts this sub-spec depends on)

| Artifact | Source | Needed for |
|----------|--------|------------|
| None | -- | This sub-spec has no dependencies on other sub-specs |

## Confidence Assessment

| Dimension | Score | Notes |
|-----------|-------|-------|
| Scope clarity | 9/10 | All files identified, all changes enumerated. Minor risk around test_gap_fillers4 interactions. |
| Dependency risk | 8/10 | No external sub-spec dependencies. Internal dependency: counter_accuracy imports from instruction_consistency must be redirected before deletion. Ordering in Phase 5 handles this. |
| Test coverage | 9/10 | All 4 test files identified with specific changes. Parser tests (test_validator.py _parse_counter) are NOT affected (they test parser logic with literal values). |
| Mirror consistency | 8/10 | 6 governance skill mirrors + 6 project-identity skill mirrors = 12 files to keep in sync. Risk of drift if one is missed. |
| Blast radius | 7/10 | ~36 files touched. Mitigated by the centralized CLAUDE.md instruction approach (avoids touching 30+ individual SKILL.md files). |
| **Overall** | **8/10** | High confidence. The validator migration (Phase 5) is the most complex piece and requires careful ordering. |

## Execution Order Summary

```
Phase 1 (delete) -> Phase 2 (create) -> Phase 3 (skill) -> Phase 4 (references) -> Phase 5 (Python) -> Phase 6 (tests)
```

Phase 1-3 are independent but ordered for logical flow. Phase 4 can partially overlap with Phase 3. Phase 5 must complete before Phase 6. Phase 6 is verification.

## Self-Report

**Status**: COMPLETE -- 29/29 tasks executed, all 6 phases passed.

**Test Results**: 139 unit + 9 integration + 12 e2e = 160 tests passing, 0 failures.

**Deviations from plan**:
1. **test_validator_extra.py** (not in original plan): Contained 2 tests referencing `IntegrityCategory.INSTRUCTION_CONSISTENCY` and a `_mk` helper creating `context/product`. All 3 cleaned up.
2. **test_validator.py TestInstructionConsistency class** (not in original plan): Entire class (3 tests) removed since category was deleted. Also removed `INSTRUCTION_CONSISTENCY` assertion from `test_all_categories_checked_by_default`.
3. **Template copilot-instructions.md T-4.6**: Instead of deleting the `framework-contract.md` line entirely, replaced it with `project-identity.md` reference to preserve the Source of Truth section structure.

**Files touched**: ~40 (36 planned + test_validator_extra.py + TestInstructionConsistency removal + plan.md + decision-store.json)

**DEC-027** added to decision-store.json documenting the architectural change.
