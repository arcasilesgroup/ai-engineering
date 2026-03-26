---
id: sub-003
parent: spec-079
title: "Project Identity — replace contracts"
status: planning
files: ["src/ai_engineering/templates/.ai-engineering/contexts/product/", "src/ai_engineering/templates/.ai-engineering/contexts/project-identity.md", ".ai-engineering/contexts/product/", ".ai-engineering/contexts/project-identity.md", "src/ai_engineering/installer/phases/governance.py", "src/ai_engineering/state/defaults.py", "src/ai_engineering/validator/categories/instruction_consistency.py", "src/ai_engineering/validator/categories/counter_accuracy.py", ".claude/skills/ai-brainstorm/SKILL.md", ".claude/skills/ai-brainstorm/handlers/interrogate.md", ".claude/skills/ai-plan/SKILL.md", ".claude/skills/ai-governance/SKILL.md", ".claude/skills/ai-project-identity/SKILL.md", "src/ai_engineering/templates/project/.claude/skills/ai-governance/SKILL.md", "src/ai_engineering/templates/project/.github/skills/ai-governance/SKILL.md", "src/ai_engineering/templates/project/.agents/skills/governance/SKILL.md", "src/ai_engineering/templates/project/copilot-instructions.md", "CLAUDE.md", "src/ai_engineering/templates/project/CLAUDE.md", ".ai-engineering/manifest.yml", "src/ai_engineering/templates/.ai-engineering/manifest.yml", "tests/unit/test_state.py", "tests/unit/test_validator.py", "tests/integration/test_gap_fillers4.py", "tests/e2e/test_install_clean.py", ".ai-engineering/state/decision-store.json", ".github/skills/ai-project-identity/SKILL.md", ".github/skills/ai-governance/SKILL.md", ".agents/skills/project-identity/SKILL.md", ".agents/skills/governance/SKILL.md"]
depends_on: []
---

# Sub-Spec 003: Project Identity — replace contracts

## Scope

Replace `framework-contract.md` + `product-contract.md` with lightweight `project-identity.md`. Create new skill `/ai-project-identity` (auto-detect + Q&A). Add centralized loading instruction in CLAUDE.md and copilot-instructions.md. Update ai-governance to validate against project-identity + CLAUDE.md + manifest. Migrate pointer-count logic from instruction_consistency.py to counter_accuracy.py then delete instruction_consistency. Update all counts from 37 to 38 skills. Update defaults.py ownership. Update all affected tests.

## Exploration

### 1. What is being replaced

**framework-contract.md** (208 lines) -- a prescriptive document defining all framework rules: non-negotiable directives, agentic model, session contracts, ownership model, security/quality gates, command contracts, pipeline strategy, progressive disclosure. Most of this content now lives in CLAUDE.md, manifest.yml, and individual SKILL.md files. The file is dead in the active repo (removed by spec-055) but **survives in templates** at `src/ai_engineering/templates/.ai-engineering/contexts/product/framework-contract.md`.

**product-contract.md** (596 lines) -- a comprehensive product document covering identity, objectives, functional requirements, architecture, security, quality, observability, and roadmap. Contains ai-engineering-specific data (version 0.2.0, repo name `arcasilesgroup/ai-engineering`, KPIs, semgrep findings). This data should NOT be copied to consumer projects. Also dead in active repo but **survives in templates** at `src/ai_engineering/templates/.ai-engineering/contexts/product/product-contract.md`.

Both files are under `contexts/product/` which defaults.py classifies as `TEAM_MANAGED/DENY` -- meaning the framework updater cannot overwrite them. This ownership is correct for team content but the directory itself needs to go since the replacement (`project-identity.md`) lives at `contexts/` root level.

### 2. Ownership in defaults.py

Current ownership rules in `_DEFAULT_OWNERSHIP_PATHS` (line 45-128 of defaults.py):
- `".ai-engineering/contexts/product/**"` -> `TEAM_MANAGED/DENY` (line 71-75)
- `".ai-engineering/contexts/orgs/**"` -> `TEAM_MANAGED/DENY` (line 70)

The `contexts/product/**` rule must be replaced with `contexts/project-identity.md` as `TEAM_MANAGED/DENY`. The `contexts/orgs/**` rule is handled by sub-002 (not this sub-spec).

### 3. Governance phase installer

`governance.py` (144 lines) copies the `.ai-engineering/` template tree to target projects. Key behaviors:
- `_EXCLUDE_PREFIXES = ("agents/", "skills/")` -- skips IDE-specific content
- `_TEAM_OWNED = "contexts/team/"` -- hard-skips team content in all modes
- `_STATE_PREFIX = "state/"` -- handled by state phase
- The `_classify` method determines skip/create/overwrite per file based on mode

For project-identity.md: needs to be seeded as `create` in INSTALL mode (new file) and `skip` if already exists (team-managed, never overwrite). This is the default behavior for files not matching any exclusion prefix. Since `project-identity.md` lives at `contexts/project-identity.md` (not under `contexts/team/`), it will naturally get the `create` action in INSTALL mode and `skip` if existing. No special code needed in governance.py beyond having the template file exist.

However, the `contexts/product/` templates will no longer exist, so they will simply stop being copied. Clean removal.

### 4. Validator: instruction_consistency.py

This file (278 lines) does two things:
1. **Pointer-count validation** (lines 84-90, 230-277): Extracts `Skills (N)` / `Agents (N)` from instruction files and validates against manifest.yml. Uses `_POINTER_SKILL_RE` and `_POINTER_AGENT_RE`.
2. **Detailed listing consistency** (lines 93-227): Compares detailed skill/agent listings across instruction files for consistency.
3. **Subsection structure check** (lines 137-149): Checks `_REQUIRED_SUBSECTIONS` -- but this is currently an **empty set** (`set()` in _shared.py line 196), so this check effectively does nothing.

**Critical dependency**: `counter_accuracy.py` already **imports from instruction_consistency.py** at line 16:
```python
from ai_engineering.validator.categories.instruction_consistency import _extract_listings
```

This means the migration is more nuanced:
- `_extract_listings` and its helpers (`_extract_subsection`, `_parse_skill_names_from_subsection`, `_parse_agent_names_from_subsection`) must move to either `counter_accuracy.py` or `_shared.py`
- The pointer-count regex patterns (`_POINTER_SKILL_RE`, `_POINTER_AGENT_RE`) are duplicated between both files -- counter_accuracy has its own (`_POINTER_COUNT_RE`, `_POINTER_AGENT_COUNT_RE`)
- After migration, counter_accuracy.py handles ALL count validation (both pointer and detailed)
- The detailed-listing consistency check (comparing files against each other) can be absorbed into counter_accuracy or dropped since the pointer-count check against manifest is the authoritative validation

### 5. Validator service.py and categories/__init__.py

`service.py` registers 7 categories in the `checkers` list (line 88-102). `INSTRUCTION_CONSISTENCY` is at position 5 (line 96). Both service.py and categories/__init__.py import and re-export `_check_instruction_consistency`.

After deletion:
- Remove from `checkers` list in service.py
- Remove from imports and `__all__` in both service.py and categories/__init__.py
- `IntegrityCategory.INSTRUCTION_CONSISTENCY` in `_shared.py` should be removed
- The `IntegrityReport.to_dict()` iterates over all `IntegrityCategory` values -- removing the enum value handles this

### 6. Validator _shared.py

`_REQUIRED_SUBSECTIONS: set[str] = set()` (line 196) -- empty, only used by instruction_consistency.py. Safe to remove.
`_SUBSECTION_PATTERN` (line 195) -- only used by instruction_consistency.py. Safe to remove.

The `_extract_listings` function is NOT in _shared.py -- it lives in instruction_consistency.py. But `_extract_section`, `_parse_skill_names`, `_parse_agent_names` ARE in _shared.py and are used by instruction_consistency.py. These shared functions should remain since they may be used by counter_accuracy.py after migration.

### 7. Skills to update

**ai-brainstorm/SKILL.md**: Step 1 "Load context" (line 25) -- add reading of `project-identity.md`.
**ai-brainstorm/handlers/interrogate.md**: Step 1 "Explore First" (line 11) -- add reading project-identity.md as context.
**ai-plan/SKILL.md**: Step 2 "Read context" (line 26) -- add reading of `project-identity.md`.
**ai-governance/SKILL.md**: "compliance" mode (line 24-31) -- replace `framework-contract.md` reference with `project-identity.md` + CLAUDE.md + manifest.yml.

### 8. CLAUDE.md and copilot-instructions.md

**CLAUDE.md** (175 lines in repo root):
- Line 106: `## Skills (37)` -> needs `(38)`
- Line 167: `| Skills (37) |` -> needs `(38)`
- Line 115: Meta skill list -> add `project-identity`
- Effort table line 125: medium count 11 -> 12, add project-identity
- Add new instruction in Workflow Orchestration section: read project-identity.md

**Template CLAUDE.md** (`src/ai_engineering/templates/project/CLAUDE.md`) -- identical content, same changes.

**AGENTS.md** (164 lines):
- Line 105: `## Skills (37)` -> `(38)`
- Line 156: `| Skills (37) |` -> `(38)`
- Line 114: Meta skill list -> add `project-identity`

**Template AGENTS.md** -- same changes.

**copilot-instructions.md** (root `.github/`):
- Line 72: `Skills (37)` -> `(38)`
- Add project-identity loading instruction

**Template copilot-instructions.md** (`src/ai_engineering/templates/project/copilot-instructions.md`):
- Line 7: `Governance rules: .ai-engineering/context/product/framework-contract.md` -> remove this line entirely (path was wrong too -- `context/` instead of `contexts/`)
- Line 50: `Skills (37)` -> `(38)`
- Add project-identity loading instruction

### 9. Manifest files

Both `.ai-engineering/manifest.yml` and its template mirror:
- Line 78: Comment `# Skills registry (37 skills)` -> `(38 skills)`
- Line 80: `total: 37` -> `total: 38`
- Add `ai-project-identity: { type: meta, tags: [governance] }` to registry (after ai-autopilot, in Meta section)

### 10. Test files requiring changes

**tests/unit/test_state.py**:
- `test_contexts_product_denied` (lines 156-159): References `contexts/product/product-contract.md`. Must be replaced with `test_contexts_project_identity_denied` testing `contexts/project-identity.md`.

**tests/unit/test_validator.py**:
- `_write_product_contract` helper (lines 114-144): Writes `context/product/product-contract.md` fixture. Must be removed or replaced.
- `_setup_full_project` (line 190): Calls `_write_product_contract`. Must be updated.
- The `_parse_counter` tests (lines 200-236) use hardcoded "37 skills" in test strings -- these are testing the parser with literal values, NOT asserting against framework state. They should remain as-is (they test the parser, not the count).

**tests/integration/test_gap_fillers4.py**:
- Lines 262-264: Creates `product-contract.md` fixture with "1 skills, 1 agents".
- Lines 352-353: Same pattern.
- Both create `context/product/product-contract.md` for testing validator behavior. Must be removed since the validator category that consumes them (instruction_consistency) is being deleted.

**tests/e2e/test_install_clean.py**:
- `test_install_creates_required_dirs` (lines 38-49): Asserts `contexts/product` directory exists. Must replace with assertion that `contexts/project-identity.md` file exists.

### 11. New skill: ai-project-identity

Pattern from existing skills (ai-note as reference):
- Frontmatter: name, description, effort (medium), argument-hint
- Sections: Purpose, When to Use, Procedure, Quick Reference, Integration
- Must exist in 3 mirror locations:
  - `.claude/skills/ai-project-identity/SKILL.md`
  - `.github/skills/ai-project-identity/SKILL.md`
  - `.agents/skills/project-identity/SKILL.md` (no `ai-` prefix per .agents convention)
- Also in template mirrors:
  - `src/ai_engineering/templates/project/.claude/skills/ai-project-identity/SKILL.md`
  - `src/ai_engineering/templates/project/.github/skills/ai-project-identity/SKILL.md`
  - `src/ai_engineering/templates/project/.agents/skills/project-identity/SKILL.md`

### 12. Project-identity.md template content

Target: `src/ai_engineering/templates/.ai-engineering/contexts/project-identity.md`
Also create dogfood: `.ai-engineering/contexts/project-identity.md`

Structure (~30-50 lines):
```markdown
# Project Identity

## Project
- **Name**: [project name]
- **Purpose**: [1-2 sentences -- what this project does and why it exists]
- **Status**: [active development | maintenance | deprecated]

## Services & APIs
- [what this project exposes or consumes]

## Dependencies & Consumers
- **Depends on**: [critical upstream dependencies]
- **Consumed by**: [downstream consumers or stakeholders]

## Boundaries
- [what MUST NOT change without coordination]
- [who to notify if boundaries are affected]
```

### 13. Dogfood contexts/product/ check

Confirmed: `.ai-engineering/contexts/` contains `frameworks/`, `languages/`, `orgs/`, `team/` -- NO `product/` directory. The `product/` directory was already removed from dogfood by spec-055. Only templates need cleanup.

### 14. Cross-cutting count: files to touch

| Category | Files | Count |
|----------|-------|-------|
| Delete templates | framework-contract.md, product-contract.md, product/ dir | 3 |
| Create template | project-identity.md | 1 |
| Create dogfood | project-identity.md | 1 |
| Create skill (3 mirrors + 3 template mirrors) | ai-project-identity SKILL.md | 6 |
| Update instruction files | CLAUDE.md (2), AGENTS.md (2), copilot-instructions.md (2) | 6 |
| Update manifests | manifest.yml (2) | 2 |
| Update skills | brainstorm (2), plan (1), governance (4 mirrors) | 7 |
| Update Python code | defaults.py, counter_accuracy.py | 2 |
| Delete Python code | instruction_consistency.py | 1 |
| Update Python imports | categories/__init__.py, service.py, _shared.py | 3 |
| Update tests | test_state.py, test_validator.py, test_gap_fillers4.py, test_install_clean.py | 4 |
| **Total** | | **~36** |
