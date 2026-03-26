---
id: sub-004
parent: spec-080
title: "/ai-code Skill Creation"
status: planning
files: [".claude/skills/ai-code/SKILL.md", ".claude/agents/ai-build.md", ".ai-engineering/manifest.yml", ".ai-engineering/schemas/manifest.schema.json"]
depends_on: [sub-003]
---

# Sub-Spec 004: /ai-code Skill Creation

## Scope
Create a dedicated `/ai-code` skill (SKILL.md) that replaces the 4-word `code` classify mode in ai-build. The skill defines: pre-coding checklist, context loading with layer precedence (team > frameworks > languages), file placement protocol, interface-first design, backward-compatibility checks, and self-review against loaded contexts. Add `contexts.precedence` field to manifest.yml. Update ai-build classify table to reference the new skill. Create mirrors in .github/skills/ and .agents/skills/.

## Exploration

### Current State

**ai-build classify table** (`.claude/agents/ai-build.md`, lines 43-55): The table has 10 modes. The `code` row is a 4-word stub: "Write code following stack standards". Other modes like `test`, `debug`, `refactor`, `simplify`, `api`, `db`, `infra`, `cicd`, `migrate` each have short descriptions but only `test`, `debug`, and `simplify` are backed by dedicated SKILL.md files (referenced in ai-build's "Referenced Skills" section, line 95-97). The remaining modes (`refactor`, `api`, `db`, `infra`, `cicd`, `migrate`) either map to existing skills (`db` -> ai-schema, `cicd` -> ai-pipeline) or are inline behaviors without backing skills.

**Context loading in ai-build** (Section 2, lines 32-39): Currently loads languages (14 files), frameworks (15 files), and team conventions -- but with NO defined precedence order. The instruction says "Apply loaded standards" without specifying which wins on conflict.

**Exemplar: ai-test SKILL.md**: Frontmatter has `name`, `description`, `effort`, `argument-hint`. The body has: Purpose, When to Use, Process (with mode-specific subsections), Stack Commands, Testing Rules, Anti-Patterns, Iron Law, Common Mistakes, Integration, and ends with `$ARGUMENTS`. No "Step 0: Load Contexts" (that is sub-003's job to add).

**Exemplar: ai-debug SKILL.md**: Same frontmatter pattern. Body has: Purpose, When to Use, Process (4 phases), Escalation Protocol, 5 Whys Example, Common Mistakes, Integration. Also ends with `$ARGUMENTS`. No context loading step either.

**Context loading gold standard** (ai-review/handlers/review.md, Step 1, lines 9-19): The most complete context loading procedure in the codebase. It: (1) runs /ai-explore for architecture map, (2) identifies diff scope, (3) detects languages and reads language/framework/team contexts, (4) reads decision-store.json. This is the pattern sub-003 will standardize as "Step 0" across 8 skills.

**lang-generic.md category structure** (lines 42-49): Four review categories defined: (a) Naming conventions -- casing, prefixes, suffixes, forbidden patterns; (b) Idiomatic patterns -- recommended patterns from context file; (c) Anti-patterns -- explicitly listed anti-patterns; (d) Error handling -- documented conventions. Severity mapping: critical (security/memory safety), major (anti-patterns, missing error handling), minor (style deviations).

**manifest.yml** (`.ai-engineering/manifest.yml`): Has no `contexts` section. The `contexts.precedence` field must be added to the USER CONFIGURATION section (above "FRAMEWORK MANAGED" line 75). The skills registry currently has 38 entries (line 78-127) and would need `ai-code` added.

**manifest.schema.json**: Uses `additionalProperties: false` at the top level (line 257). Adding `contexts.precedence` requires adding a `contexts` property to the schema. The existing pattern for array fields (e.g., `tooling`, `agents.names`) uses `type: array` with `items: { type: string }`.

**Mirror generation** (`scripts/sync_command_mirrors.py`): Fully automated. The `discover_skills()` function (lines 510-526) scans `.claude/skills/ai-*/SKILL.md` and auto-discovers any new skill. Mirrors are generated to 5 surfaces: `.agents/skills/`, `.agents/agents/`, `.github/skills/`, `.github/agents/`, and template project paths. Creating `.claude/skills/ai-code/SKILL.md` is sufficient -- running `python scripts/sync_command_mirrors.py` generates all mirrors automatically. No code changes to the script are needed.

### Dependency Analysis

**sub-003 provides**: "Step 0: Load Contexts" pattern that will be added to 8 code-touching skills including ai-code. Sub-004 must include Step 0 in the ai-code SKILL.md using the pattern sub-003 defines.

**sub-003 scope note**: sub-003 lists "ai-code" in its 8 target skills (sub-003/spec.md line 13), meaning sub-003 expects ai-code to already exist OR will add Step 0 to it when it does. Since sub-004 depends on sub-003, sub-004 creates ai-code WITH the Step 0 pattern already baked in.

### Design Decisions

**SKILL.md structure**: Follow the ai-test/ai-debug pattern: frontmatter (name, description, effort, argument-hint), then sections: Purpose, When to Use, Process (Step 0 from sub-003 + Steps 1-6), Self-Review, Common Mistakes, Integration, `$ARGUMENTS`.

**Process steps for /ai-code**:
1. Step 0 -- Load Contexts (from sub-003 pattern): read languages/, frameworks/, team/ with precedence team > frameworks > languages
2. Step 1 -- Pre-Coding Checklist: understand the task, identify affected files, check for existing patterns
3. Step 2 -- File Placement Protocol: where new files go based on project conventions
4. Step 3 -- Interface-First Design: define interfaces/protocols/types before implementation
5. Step 4 -- Write Code: implement following loaded standards
6. Step 5 -- Backward Compatibility: check public API changes, deprecation requirements
7. Step 6 -- Self-Review: lightweight check against loaded contexts (naming, anti-patterns, error handling) -- produces compliance trace

**Self-review uses lang-generic.md categories**: naming conventions, idiomatic patterns, anti-patterns, error handling. This is the lightweight build-time check; full validation stays in /ai-review.

**contexts.precedence manifest field**: Array of layer names in descending priority: `[team, frameworks, languages]`. Added to manifest.yml user configuration section and schema.

**Effort level**: `high` (matches ai-test which is also a build-phase skill invoked by ai-build).

**ai-build classify table update**: Change the `code` row from inline description to a reference pattern. The current table format shows `What it does` as prose; update to match the way test/debug are conceptually referenced -- the description stays as prose but ai-build's "Referenced Skills" section (line 95) adds `/ai-code` to the list.

### Files Changed

| File | Change |
|------|--------|
| `.claude/skills/ai-code/SKILL.md` | NEW -- full skill definition |
| `.claude/agents/ai-build.md` | UPDATE -- classify table `code` row description, add ai-code to Referenced Skills |
| `.ai-engineering/manifest.yml` | UPDATE -- add `contexts` section with `precedence`, add `ai-code` to skills registry, bump total to 39 |
| `.ai-engineering/schemas/manifest.schema.json` | UPDATE -- add `contexts` property with `precedence` array |

### Files Auto-Generated (via `python scripts/sync_command_mirrors.py`)

| File | Notes |
|------|-------|
| `.agents/skills/code/SKILL.md` | Generic IDE mirror (stripped ai- prefix) |
| `.github/skills/ai-code/SKILL.md` | GitHub Copilot Agent Skill mirror |
| `src/ai_engineering/templates/project/.claude/skills/ai-code/SKILL.md` | Install template |
| `src/ai_engineering/templates/project/.agents/skills/code/SKILL.md` | Install template generic |
| `src/ai_engineering/templates/project/.github/skills/ai-code/SKILL.md` | Install template Copilot |

### Risks and Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| Self-review adds latency to every code task | Low | Limited to 3 critical categories (naming, anti-patterns, error handling); full review stays in /ai-review |
| contexts.precedence may conflict with sub-003 Step 0 pattern | Low | Sub-004 depends on sub-003; precedence is complementary (declares the order sub-003 Step 0 applies) |
| manifest.yml schema additionalProperties:false blocks new `contexts` field | Medium | Schema must be updated in same task; validated before mirrors run |
| Skill total count drift (currently 38, sub-007 adds/removes others) | Low | Sub-004 only increments to 39; sub-007 handles its own delta later |

### Self-Challenge

**Strongest argument against**: ai-code duplicates content that should live in ai-build's Section 2 and Section 4. Why create a separate skill file when ai-build already has context loading and post-edit validation?

**Response**: ai-build is the agent (coordinator); ai-code is the skill (procedure). The agent picks the mode; the skill defines the detailed procedure. This matches the established pattern (ai-build agent -> ai-test skill, ai-build agent -> ai-debug skill). The 4-word `code` stub is the weakest mode in the classify table -- every other critical mode has either a backing skill or substantial inline procedure.

**Assumption most likely to be wrong**: That teams will actually benefit from build-time self-review. If context files are too generic, the self-review becomes a rubber stamp.

**Response**: The self-review uses the same category structure as lang-generic.md (proven in code review). Even if context files are lean (DEC-014: max 1 page), the naming + anti-pattern checks catch the most impactful deviations. The compliance trace makes the check transparent.
