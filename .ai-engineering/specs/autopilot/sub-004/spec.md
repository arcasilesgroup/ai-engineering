---
id: sub-004
parent: spec-079
title: "Context Loading Enforcement + Language Cleanup"
status: complete
files: [".ai-engineering/contexts/languages/ruby.md", ".ai-engineering/contexts/languages/elixir.md", ".ai-engineering/contexts/languages/universal.md", ".ai-engineering/contexts/languages/cpp.md", "src/ai_engineering/templates/.ai-engineering/contexts/languages/ruby.md", "src/ai_engineering/templates/.ai-engineering/contexts/languages/elixir.md", "src/ai_engineering/templates/.ai-engineering/contexts/languages/universal.md", "src/ai_engineering/templates/.ai-engineering/contexts/languages/cpp.md", ".claude/skills/ai-review/handlers/lang-generic.md", ".claude/skills/ai-review/handlers/review.md", ".claude/skills/ai-review/handlers/lang-ruby.md", ".claude/skills/ai-review/handlers/lang-elixir.md", ".claude/agents/ai-build.md", "CLAUDE.md", "src/ai_engineering/templates/project/CLAUDE.md", "src/ai_engineering/templates/project/copilot-instructions.md", ".github/skills/ai-review/handlers/lang-generic.md", ".github/skills/ai-review/handlers/review.md", ".agents/skills/review/handlers/lang-generic.md", ".agents/skills/review/handlers/review.md"]
depends_on: ["sub-003"]
---

# Sub-Spec 004: Context Loading Enforcement + Language Cleanup

## Scope

Remove ruby, elixir, and universal.md from language contexts (templates + dogfood). Create cpp.md context file. Create lang-generic.md handler with fallback dispatch in review.md. Add explicit context loading instruction in CLAUDE.md and copilot-instructions.md. Update ai-build agent with enumerated language list (13 languages).

## Exploration

### Current State: Language Context Files

**Dogfood directory** (`.ai-engineering/contexts/languages/`): 16 files total.
- KEEP (13): bash.md (444 lines), csharp.md (187), dart.md (457), go.md (229), java.md (263), javascript.md (422), kotlin.md (380), php.md (383), python.md (207), sql.md (151), swift.md (351), typescript.md (270), rust.md (250)
- DELETE (3): ruby.md (248 lines), elixir.md (284 lines), universal.md (281 lines)
- CREATE (1): cpp.md (does NOT exist yet)

**Template directory** (`src/ai_engineering/templates/.ai-engineering/contexts/languages/`): identical 16 files, same delete/create actions needed.

**Template instructions** (`src/ai_engineering/templates/project/instructions/`): contains `ruby.instructions.md` and `elixir.instructions.md` -- these must also be deleted.

**Count clarification**: The parent spec says "13 lenguajes" but enumerates 13 names that exclude rust. Since the spec only explicitly deletes ruby, elixir, universal, and rust.md has a dedicated handler (`lang-rust.md`), rust.md STAYS. Post-cleanup: **14 context files** (13 listed + rust). The ai-build enumerated list should include rust (14 languages, not 13). The parent spec line 219 already says "(14)" -- line 223 saying "13" is the error.

### Current State: Review Handlers

**`.claude/skills/ai-review/handlers/`** contains 11 files:
- Generic: `find.md`, `learn.md`, `review.md`
- Language-specific (8): `lang-cpp.md`, `lang-flutter.md`, `lang-go.md`, `lang-java.md`, `lang-kotlin.md`, `lang-python.md`, `lang-rust.md`, `lang-typescript.md`
- `lang-ruby.md` and `lang-elixir.md` do NOT exist (no deletion needed for handlers)
- `lang-generic.md` does NOT exist (must be created)

**Mirror directories** (`.github/skills/ai-review/handlers/` and `.agents/skills/review/handlers/`): identical 11 files in each. Same creation needed.

### Current State: review.md Dispatch

All three mirrors of `review.md` have identical content. Step 1 says:
> "Detect languages in the diff (file extensions) and read .ai-engineering/contexts/languages/{lang}.md"

There is NO explicit fallback instruction. The handler dispatch between dedicated lang-X.md and a generic fallback does NOT exist yet. Step 2 dispatches 8 concern agents but does NOT mention language handlers. The language handlers (lang-python.md etc.) say they are dispatched as "Step 2b" but review.md does NOT document this step.

### Current State: ai-build.md

Lines 31-35 contain the context loading step:
```
1. `.ai-engineering/contexts/languages/{detected_language}.md` for each detected language
2. `.ai-engineering/contexts/frameworks/{detected_framework}.md` for each detected framework
3. `.ai-engineering/contexts/team/*.md` for all team conventions
```
This uses a generic `{detected_language}` pattern. No enumerated list. Must be updated to enumerate available languages (14) and frameworks.

### Current State: CLAUDE.md and copilot-instructions.md

**CLAUDE.md** (root, line 172): References `Contexts` pointing to `.ai-engineering/contexts/languages/`, `frameworks/`, `team/` in the Source of Truth table. NO explicit instruction to load contexts before writing code.

**Template CLAUDE.md** (`src/ai_engineering/templates/project/CLAUDE.md`): identical content to root CLAUDE.md.

**copilot-instructions.md** (root `.github/copilot-instructions.md`, line 9): references contexts directory. NO explicit context loading instruction.

**Template copilot-instructions.md** (`src/ai_engineering/templates/project/copilot-instructions.md`): different/older content. References `framework-contract.md` (sub-003 dependency will have already cleaned this).

### Current State: Python Code References

**`src/ai_engineering/installer/autodetect.py`** (lines 43-50): `_STACK_POPULARITY` tuple includes "ruby", "elixir", "universal". `_FILE_MARKERS` dict (lines 108-110): maps `Gemfile` -> ruby, `mix.exs` -> elixir. OUT OF SCOPE for this sub-spec per parent spec (autodetect changes are separate concern).

**`scripts/sync_command_mirrors.py`** (lines 313-315): `_LANG_GLOBS` dict includes "ruby" -> `**/*.rb` and "elixir" -> `**/*.ex,**/*.exs`. OUT OF SCOPE.

**`tests/unit/installer/test_autodetect.py`**: tests for Gemfile -> ruby and mix.exs -> elixir. OUT OF SCOPE.

**`tests/unit/installer/test_wizard.py`** (line 40): `_STACKS` list includes ruby, elixir, universal. OUT OF SCOPE.

**`.ai-engineering/scripts/hooks/_lib/injection_patterns.py`** (line 107): regex pattern includes `ruby` in `base64_pipe_shell` -- this is a SECURITY pattern detecting injection, NOT a language context reference. Must NOT be modified.

### Dependency Analysis (sub-003)

Sub-003 modifies:
- `CLAUDE.md` and template: adds project-identity loading instruction
- `.github/copilot-instructions.md` and template: adds project-identity loading instruction, fixes `framework-contract.md` reference

Sub-004 must ADD context loading instruction AFTER sub-003's project-identity instruction. Both instructions go in the same area (Session Start / Workflow Orchestration).

### Pattern: lang-python.md (template for lang-generic.md)

Structure:
1. Purpose (1 line)
2. Integration note (Step 2b dispatch, +10% confidence bonus)
3. Step 1: Detect scope (file extensions, skip if none, detect frameworks)
4. Step 2-4: Findings by severity (critical, major, minor)
5. Step 5: Framework-specific checks
6. Step 6: Diagnostic tool cross-reference table
7. Output format (YAML)

The generic handler must follow this structure but be PARAMETERIZED by language instead of hardcoded.
