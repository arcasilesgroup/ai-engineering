---
total: 4
completed: 4
---

# Plan: sub-004 /ai-code Skill Creation

## Dependencies

- **imports**: Step 0 context loading pattern (from sub-003) -- sub-004 bakes this pattern into the new SKILL.md
- **exports**: `.claude/skills/ai-code/SKILL.md`, `contexts.precedence` manifest field -- consumed by sub-005 (Build Standards Validation)

## Plan

### T-4.1: Create ai-code SKILL.md

Create `.claude/skills/ai-code/SKILL.md` with the full skill definition.

**Files**:
- `NEW .claude/skills/ai-code/SKILL.md`

**Content structure**:

Frontmatter:
- `name: ai-code`
- `description: "Use when writing new code, implementing features, or adding functionality. Pre-coding checklist, context-aware coding with layer precedence, interface-first design, backward-compatibility checks, self-review."`
- `effort: high`
- `argument-hint: "[task description or file:target]"`

Body sections (in order):
1. **Purpose**: Code implementation skill. Writes code that satisfies loaded context standards on the first pass. Lightweight self-review at build-time; full validation deferred to /ai-review.
2. **When to Use**: New features, implementing approved plans, adding functionality to existing modules, writing utility/helper code. NOT for tests (use /ai-test), debugging (use /ai-debug), refactoring (use /ai-simplify), or schema work (use /ai-schema).
3. **Process**:
   - **Step 0 -- Load Contexts**: Read `manifest.yml providers.stacks` for detected stack. For each stack, read `.ai-engineering/contexts/languages/{lang}.md`, `.ai-engineering/contexts/frameworks/{fw}.md`, and ALL `.ai-engineering/contexts/team/*.md`. Apply with precedence: team > frameworks > languages (declared in `manifest.yml contexts.precedence`). When a team convention conflicts with a framework default, team wins.
   - **Step 1 -- Pre-Coding Checklist**: (a) Restate the task in one sentence. (b) Identify target files -- existing files to modify or new files to create. (c) Search for existing patterns -- grep for similar implementations in the codebase to match conventions. (d) Check decision-store.json for relevant architectural decisions.
   - **Step 2 -- File Placement Protocol**: (a) New files go in the directory matching existing project structure (follow the pattern, don't invent new paths). (b) Test files mirror source structure (e.g., `src/foo/bar.py` -> `tests/foo/test_bar.py`). (c) Never create top-level files without explicit user instruction. (d) If unsure about placement, check 3 similar files in the codebase and follow their pattern.
   - **Step 3 -- Interface-First Design**: (a) Define public interfaces (protocols, abstract classes, type signatures) before writing implementation. (b) Document the contract: inputs, outputs, errors, side effects. (c) If the interface touches other modules, check those modules' existing contracts first. (d) Skip for trivial changes (single-function additions, config updates).
   - **Step 4 -- Write Code**: Implement following all loaded context standards. Apply stack-specific conventions from Step 0. Use YAGNI -- write the minimal code that satisfies the requirement.
   - **Step 5 -- Backward Compatibility Check**: (a) If changing a public function signature: add deprecation path or confirm breaking change is intentional. (b) If modifying config format: ensure backward-compatible parsing. (c) If renaming exports: grep for all callers and update them. (d) Skip for internal/private code.
   - **Step 6 -- Self-Review (Compliance Trace)**: Check written code against loaded contexts for 3 critical categories (from lang-generic.md structure): (1) Naming conventions -- verify casing, prefixes, suffixes match context rules. (2) Anti-patterns -- verify no code matches anti-patterns listed in context files. (3) Error handling -- verify error handling follows documented conventions. Produce a compliance trace:
     ```
     ## Compliance Trace
     | Category | Status | Notes |
     |----------|--------|-------|
     | Naming conventions | PASS/DEVIATION | [details if deviation] |
     | Anti-patterns | PASS/DEVIATION | [details if deviation] |
     | Error handling | PASS/DEVIATION | [details if deviation] |
     ```
     Fix deviations before reporting task complete. If a deviation is intentional, document the reason.
4. **Common Mistakes**:
   - Writing code before loading contexts (standards drift)
   - Inventing new file paths instead of following existing project structure
   - Skipping interface definition for non-trivial features
   - Not checking for callers when changing public signatures
   - Ignoring anti-patterns listed in context files
   - Self-reviewing against general knowledge instead of loaded context rules
5. **Integration**:
   - **Called by**: `ai-build agent` (classify mode: code), `/ai-dispatch` (implementation tasks), user directly
   - **Calls**: stack-specific linters (post-edit validation via ai-build Step 4)
   - **Transitions to**: `/ai-test` (TDD GREEN phase), `/ai-verify` (quality validation), `/ai-review` (full review)
6. `$ARGUMENTS`

**Done**:
- [x] File exists at `.claude/skills/ai-code/SKILL.md`
- [x] Frontmatter has name, description, effort (high), argument-hint
- [x] Step 0 matches the sub-003 context loading pattern (read manifest stacks, load languages/frameworks/team with precedence)
- [x] Steps 1-6 cover: pre-coding checklist, file placement, interface-first, write code, backward compat, self-review
- [x] Self-review produces compliance trace with 3 categories (naming, anti-patterns, error handling)
- [x] Common Mistakes and Integration sections present
- [x] File ends with `$ARGUMENTS`

### T-4.2: Update ai-build classify table and references

Update `.claude/agents/ai-build.md` to reference the new /ai-code skill.

**Files**:
- `EDIT .claude/agents/ai-build.md`

**Changes**:

1. **Classify table** (line 45): Change the `code` row description from "Write code following stack standards" to "Pre-coding checklist, context-aware coding, interface-first, self-review". This makes the description match the skill's actual procedure (same pattern as `test` row saying "Plan, write, run tests (modes: plan/run/gap)").

2. **Referenced Skills** (line 95): Add `.claude/skills/ai-code/SKILL.md` to the first line of referenced skills. Current line is:
   ```
   - `.claude/skills/ai-test/SKILL.md`, `.claude/skills/ai-debug/SKILL.md`, `.claude/skills/ai-simplify/SKILL.md`
   ```
   Updated to:
   ```
   - `.claude/skills/ai-code/SKILL.md`, `.claude/skills/ai-test/SKILL.md`, `.claude/skills/ai-debug/SKILL.md`, `.claude/skills/ai-simplify/SKILL.md`
   ```

**Done**:
- [x] Classify table `code` row has updated description reflecting the skill's procedure
- [x] Referenced Skills section lists ai-code SKILL.md
- [x] No other lines in ai-build.md are modified

### T-4.3: Add contexts.precedence to manifest.yml and schema

Add the `contexts` section with `precedence` field to manifest.yml and extend the JSON schema.

**Files**:
- `EDIT .ai-engineering/manifest.yml`
- `EDIT .ai-engineering/schemas/manifest.schema.json`

**Changes to manifest.yml**:

1. Add `contexts` section in USER CONFIGURATION area (after `cicd` block, before the "FRAMEWORK MANAGED" separator at line 75):
   ```yaml
   # Context loading precedence
   # When conventions from different context layers conflict,
   # the first layer in the list wins (team overrides framework, framework overrides language).
   contexts:
     precedence: [team, frameworks, languages]
   ```

2. Add `ai-code` to the skills registry (after `ai-debug` entry, in the "Core workflow" group):
   ```yaml
       ai-code: { type: workflow, tags: [implementation] }
   ```

3. Update `skills.total` from `38` to `39`.

**Changes to manifest.schema.json**:

1. Add `contexts` property to the top-level properties object:
   ```json
   "contexts": {
     "type": "object",
     "properties": {
       "precedence": {
         "type": "array",
         "items": {
           "type": "string",
           "enum": ["team", "frameworks", "languages"]
         },
         "minItems": 1,
         "uniqueItems": true
       }
     },
     "required": ["precedence"],
     "additionalProperties": false
   }
   ```

2. The `contexts` property does NOT need to be added to the top-level `required` array (it is user configuration, not framework-mandatory). But because the top level has `additionalProperties: false`, the property MUST be declared even if not required -- otherwise validation will reject manifests that include it.

**Done**:
- [x] manifest.yml has `contexts.precedence: [team, frameworks, languages]` in user configuration section
- [x] manifest.yml skills registry has `ai-code` entry with type: workflow, tags: [implementation]
- [x] manifest.yml skills total is 41 (was 40 at execution time, not 38 as planned; incremented by 1)
- [x] manifest.schema.json has `contexts` property definition with precedence array (enum: team, frameworks, languages)
- [x] Schema validation passes: `additionalProperties: false` at top level does not reject the new field

### T-4.4: Generate mirrors and validate

Run the mirror sync script to auto-generate all IDE surface mirrors for the new ai-code skill.

**Files**:
- `RUN python scripts/sync_command_mirrors.py`
- `VERIFY .agents/skills/code/SKILL.md` (auto-generated)
- `VERIFY .github/skills/ai-code/SKILL.md` (auto-generated)
- `VERIFY src/ai_engineering/templates/project/.claude/skills/ai-code/SKILL.md` (auto-generated)
- `VERIFY src/ai_engineering/templates/project/.agents/skills/code/SKILL.md` (auto-generated)
- `VERIFY src/ai_engineering/templates/project/.github/skills/ai-code/SKILL.md` (auto-generated)

**Process**:
1. Run `python scripts/sync_command_mirrors.py` -- this discovers the new `.claude/skills/ai-code/SKILL.md` and generates mirrors to all 5 surfaces.
2. Run `python scripts/sync_command_mirrors.py --check` -- verify zero drift.
3. Spot-check: confirm `.agents/skills/code/SKILL.md` uses bare name `code` (ai- prefix stripped) and `.github/skills/ai-code/SKILL.md` has `mode: agent` in frontmatter.

**Done**:
- [x] `python scripts/sync_command_mirrors.py` completes without error
- [x] `python scripts/sync_command_mirrors.py --check` exits 0 (no drift)
- [x] `.agents/skills/code/SKILL.md` exists with stripped ai- prefix in name
- [x] `.github/skills/ai-code/SKILL.md` exists with `mode: agent` frontmatter
- [x] All 5 template mirrors exist
- [x] Cross-references in mirrors use platform-appropriate paths (`.agents/skills/` for generic, `.github/skills/` for Copilot)

## Confidence Assessment

| Task | Confidence | Rationale |
|------|-----------|-----------|
| T-4.1 | 95% | Pattern is well-established (ai-test, ai-debug); only uncertainty is exact wording for Step 0 alignment with sub-003 |
| T-4.2 | 98% | Trivial edit -- 2 lines in a well-understood file |
| T-4.3 | 90% | Schema change requires careful handling of additionalProperties:false; contexts property declaration must be correct |
| T-4.4 | 95% | Mirror script is battle-tested; auto-discovers new skills without code changes |
| Overall | 93% | Low-risk sub-spec with well-established patterns; main dependency (sub-003 Step 0 pattern) is complementary, not blocking |

## Self-Report

**Status**: COMPLETE (4/4 tasks)

**Tasks executed**:

| Task | Result | Notes |
|------|--------|-------|
| T-4.1 | PASS | Created SKILL.md with frontmatter, Steps 0-6, compliance trace, common mistakes, integration, $ARGUMENTS |
| T-4.2 | PASS | Updated classify table description and added ai-code to Referenced Skills |
| T-4.3 | PASS | Added contexts.precedence to manifest.yml and schema; added ai-code to registry; total 40->41 |
| T-4.4 | PASS | Mirror sync created 6 files, updated 6 files; --check exits 0; spot-checks confirmed |

**Deviation from plan**: The plan expected `skills.total` to go from 38 to 39. At execution time, the manifest was already at 40 skills (upstream changes since plan was written). Incremented to 41 to account for the new ai-code entry. The mirror sync script confirmed 41 skills discovered.

**Files created** (1 canonical + 5 mirrors):
- `.claude/skills/ai-code/SKILL.md` (canonical)
- `.agents/skills/code/SKILL.md` (auto-generated)
- `.github/skills/ai-code/SKILL.md` (auto-generated)
- `src/ai_engineering/templates/project/.claude/skills/ai-code/SKILL.md` (auto-generated)
- `src/ai_engineering/templates/project/.agents/skills/code/SKILL.md` (auto-generated)
- `src/ai_engineering/templates/project/.github/skills/ai-code/SKILL.md` (auto-generated)

**Files modified** (4 canonical + 6 mirrors):
- `.claude/agents/ai-build.md` (classify table + referenced skills)
- `.ai-engineering/manifest.yml` (contexts section + ai-code registry + total)
- `.ai-engineering/schemas/manifest.schema.json` (contexts property)
- 6 mirror files auto-updated by sync script

**Exports for downstream**:
- `.claude/skills/ai-code/SKILL.md` -- consumed by sub-005 (Build Standards Validation)
- `contexts.precedence` manifest field -- consumed by sub-005 and all context-loading skills
