---
total: 12
completed: 12
---

# Plan: sub-004 Context Loading Enforcement + Language Cleanup

## Plan

### Task 1: Delete ruby.md from dogfood and template contexts
- [x] Delete `.ai-engineering/contexts/languages/ruby.md`
- [x] Delete `src/ai_engineering/templates/.ai-engineering/contexts/languages/ruby.md`
- **Files**: `.ai-engineering/contexts/languages/ruby.md`, `src/ai_engineering/templates/.ai-engineering/contexts/languages/ruby.md`
- **Done**: Neither file exists. `ls` confirms 0 matches for `ruby.md` in both directories.

### Task 2: Delete elixir.md from dogfood and template contexts
- [x] Delete `.ai-engineering/contexts/languages/elixir.md`
- [x] Delete `src/ai_engineering/templates/.ai-engineering/contexts/languages/elixir.md`
- **Files**: `.ai-engineering/contexts/languages/elixir.md`, `src/ai_engineering/templates/.ai-engineering/contexts/languages/elixir.md`
- **Done**: Neither file exists. `ls` confirms 0 matches for `elixir.md` in both directories.

### Task 3: Delete universal.md from dogfood and template contexts
- [x] Delete `.ai-engineering/contexts/languages/universal.md`
- [x] Delete `src/ai_engineering/templates/.ai-engineering/contexts/languages/universal.md`
- **Files**: `.ai-engineering/contexts/languages/universal.md`, `src/ai_engineering/templates/.ai-engineering/contexts/languages/universal.md`
- **Done**: Neither file exists. `ls` confirms 0 matches for `universal.md` in both directories.

### Task 4: Delete ruby and elixir template instruction files
- [x] Delete `src/ai_engineering/templates/project/instructions/ruby.instructions.md`
- [x] Delete `src/ai_engineering/templates/project/instructions/elixir.instructions.md`
- **Files**: `src/ai_engineering/templates/project/instructions/ruby.instructions.md`, `src/ai_engineering/templates/project/instructions/elixir.instructions.md`
- **Done**: Neither file exists in `src/ai_engineering/templates/project/instructions/`.

### Task 5: Create cpp.md context file (dogfood + template)
- [x] Create `.ai-engineering/contexts/languages/cpp.md` following the pattern of existing context files (200+ lines)
- [x] Copy to `src/ai_engineering/templates/.ai-engineering/contexts/languages/cpp.md`
- **Content structure** (follow go.md/rust.md pattern):
  - Naming conventions (snake_case functions, PascalCase types, UPPER_SNAKE constants)
  - Memory management (smart pointers over raw, RAII, no manual new/delete)
  - Modern C++ guidelines (prefer C++17/20 features, std::optional, std::variant, structured bindings)
  - Error handling (exceptions vs error codes, noexcept, RAII for cleanup)
  - Concurrency (std::mutex with lock_guard/scoped_lock, std::atomic, avoid detached threads)
  - Common pitfalls (dangling references, iterator invalidation, undefined behavior, uninitialized variables)
  - const correctness (const references, const member functions, constexpr)
  - Build and tooling (compiler warnings: -Wall -Wextra -Wpedantic, clang-tidy, cppcheck, sanitizers)
  - Testing patterns (Google Test or Catch2, mocking, assertions)
  - Performance (pass by const ref, move semantics, reserve containers, cache locality)
- **Files**: `.ai-engineering/contexts/languages/cpp.md`, `src/ai_engineering/templates/.ai-engineering/contexts/languages/cpp.md`
- **Done**: Both files exist with 200+ lines. Content covers all sections listed above. No TODOs or stubs remain.

### Task 6: Create lang-generic.md handler (all 3 mirrors)
- [x] Create `.claude/skills/ai-review/handlers/lang-generic.md`
- [x] Copy to `.github/skills/ai-review/handlers/lang-generic.md`
- [x] Copy to `.agents/skills/review/handlers/lang-generic.md`
- **Content structure** (follow lang-python.md pattern):
  - Purpose: Generic language review handler for languages without a dedicated `lang-{language}.md` handler
  - Integration: Step 2b, same YAML format, +10% confidence bonus on corroboration
  - Step 1 -- Detect language scope:
    - Map file extensions to language name: `.py` -> python, `.ts/.tsx` -> typescript, `.go` -> go, `.rs` -> rust, `.cpp/.cc/.cxx/.hpp/.h` -> cpp, `.java` -> java, `.kt/.kts` -> kotlin, `.cs` -> csharp, `.swift` -> swift, `.dart` -> dart, `.php` -> php, `.sh/.bash` -> bash, `.sql` -> sql, `.js/.jsx` -> javascript, `.rb` -> ruby (fallback if context file exists)
    - Read `.ai-engineering/contexts/languages/{language}.md` for loaded standards
    - If no context file exists for the detected language, apply only the universal best practices from the review.md concern agents
  - Step 2 -- Apply context-file standards: check diff against loaded language conventions (naming, patterns, anti-patterns, testing, error handling)
  - Step 3 -- Severity mapping: critical (security/memory safety issues per context file), major (anti-patterns flagged in context file), minor (style deviations from context conventions)
  - Step 4 -- Diagnostic tool cross-reference: suggest language-appropriate tools from context file if mentioned
  - Output format: same YAML as lang-python.md with `id: lang-generic-N`
- **Files**: `.claude/skills/ai-review/handlers/lang-generic.md`, `.github/skills/ai-review/handlers/lang-generic.md`, `.agents/skills/review/handlers/lang-generic.md`
- **Done**: All 3 files exist with identical content. Structure matches lang-python.md pattern. Extension-to-language mapping covers all 14 supported languages.

### Task 7: Update review.md with fallback dispatch instruction (all 3 mirrors)
- [x] Edit `.claude/skills/ai-review/handlers/review.md` -- add Step 2b between Step 2 and Step 3
- [x] Edit `.github/skills/ai-review/handlers/review.md` -- same change
- [x] Edit `.agents/skills/review/handlers/review.md` -- same change
- **Change**: After existing Step 2 ("Dispatch 8 Agents"), add:
  ```
  ### Step 2b -- Language-Specific Review

  For each language detected in the diff:
  1. If a dedicated handler exists (`lang-{language}.md`), dispatch it
  2. Otherwise, dispatch `lang-generic.md` with the detected language

  Dedicated handlers exist for: cpp, flutter, go, java, kotlin, python, rust, typescript.
  All other languages use the generic handler.

  Language handler findings feed into Step 3 aggregation with the same YAML format.
  ```
- **Files**: `.claude/skills/ai-review/handlers/review.md`, `.github/skills/ai-review/handlers/review.md`, `.agents/skills/review/handlers/review.md`
- **Done**: All 3 files contain Step 2b with dedicated handler list and generic fallback instruction. Step numbering is consistent (Steps 1, 2, 2b, 3, 4).

### Task 8: Update CLAUDE.md with context loading instruction (root + template)
- [x] Edit `CLAUDE.md` -- add context loading instruction in Workflow Orchestration section
- [x] Edit `src/ai_engineering/templates/project/CLAUDE.md` -- same change
- **Change**: Add a new numbered subsection (after sub-003's project-identity instruction, which will be in the Workflow Orchestration area). Insert as the LAST numbered item before "## Task Management":
  ```
  ### 10. Context Loading

  Before writing or reviewing code, load the applicable context files:
  1. Detect the project's languages from file extensions and build config
  2. Read `.ai-engineering/contexts/languages/{language}.md` for each detected language
  3. Read `.ai-engineering/contexts/frameworks/{framework}.md` for each detected framework
  4. Read `.ai-engineering/contexts/team/*.md` for team conventions
  5. Apply loaded standards to all code generation and review
  ```
  Note: The exact section number depends on what sub-003 adds. If sub-003 adds section 10, this becomes section 11. Coordinate by reading the file at execution time.
- **Files**: `CLAUDE.md`, `src/ai_engineering/templates/project/CLAUDE.md`
- **Done**: Both files contain the context loading instruction in the Workflow Orchestration section. The instruction follows sub-003's project-identity instruction.

### Task 9: Update copilot-instructions.md with context loading instruction (root + template)
- [x] Edit `.github/copilot-instructions.md` -- add context loading instruction
- [x] Edit `src/ai_engineering/templates/project/copilot-instructions.md` -- add context loading instruction
- **Change**: Add under Session Start Protocol (after sub-003's project-identity instruction):
  ```
  5. **Load contexts** -- read `.ai-engineering/contexts/languages/{lang}.md`, `frameworks/{fw}.md`, and `team/*.md` for each detected stack before writing code.
  ```
  Note: Same coordination concern as Task 8 -- the exact insertion point depends on sub-003's changes. Read the file at execution time.
- **Files**: `.github/copilot-instructions.md`, `src/ai_engineering/templates/project/copilot-instructions.md`
- **Done**: Both files contain the context loading instruction. Root file has it in Session Start Protocol. Template file has it in the equivalent section.

### Task 10: Update ai-build.md with enumerated language list
- [x] Edit `.claude/agents/ai-build.md` lines 32-35 -- replace generic `{detected_language}` with enumerated list
- **Change**: Replace the Load Contexts section content with:
  ```
  ### 2. Load Contexts

  After detecting the stack, read the applicable context files:
  1. **Languages** -- read `.ai-engineering/contexts/languages/{lang}.md` for each detected language.
     Available (14): bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, rust, sql, swift, typescript
  2. **Frameworks** -- read `.ai-engineering/contexts/frameworks/{fw}.md` for each detected framework.
     Available: android, api-design, aspnetcore, backend-patterns, bun, claude-api, deployment-patterns, django, flutter, ios, mcp-sdk, nextjs, nodejs, react, react-native
  3. **Team** -- read `.ai-engineering/contexts/team/*.md` for all team conventions.

  Apply loaded standards to all subsequent code generation.
  ```
- **Files**: `.claude/agents/ai-build.md`
- **Done**: ai-build.md contains enumerated list of 14 languages and 15 frameworks. The `{detected_language}` generic pattern is replaced.

### Task 11: Verify no stale references remain
- [x] Grep entire repo for `ruby.md`, `elixir.md`, `universal.md` in contexts/languages paths -- should only appear in spec files, CHANGELOG, and out-of-scope Python code (autodetect.py, sync_command_mirrors.py, test files, injection_patterns.py)
- [x] Verify `injection_patterns.py` ruby reference is UNTOUCHED (security pattern, not language context)
- [x] Verify autodetect.py, sync_command_mirrors.py, test_autodetect.py, test_wizard.py are NOT modified (out of scope)
- **Files**: none modified (verification only)
- **Done**: Grep confirms zero references to ruby.md/elixir.md/universal.md in contexts paths except spec files and out-of-scope code. injection_patterns.py is untouched.

### Task 12: Verify final file counts and consistency
- [x] Count files in `.ai-engineering/contexts/languages/` -- should be 14 (13 original minus 3 deleted plus 1 created plus rust = 14)
- [x] Count files in `src/ai_engineering/templates/.ai-engineering/contexts/languages/` -- should be 14
- [x] Count files in `src/ai_engineering/templates/project/instructions/` -- should be 16 (was 18, minus 2 ruby/elixir)
- [x] Verify all 3 review.md mirrors have identical Step 2b content
- [x] Verify all 3 lang-generic.md mirrors have identical content
- **Files**: none modified (verification only)
- **Done**: All counts match expected values. All mirrors are identical.

## Exports

| Export | Target | Description |
|--------|--------|-------------|
| `contexts/languages/cpp.md` | sub-005 (if exists) | New C++ context file available for review handlers |
| `lang-generic.md` | any sub-spec using review | Generic language handler available for dispatch |
| `CLAUDE.md` context instruction | all agents | All agents now instructed to load contexts before code work |
| `review.md` Step 2b | review workflows | Language handler dispatch is now explicit with fallback |

## Imports

| Import | Source | Description |
|--------|--------|-------------|
| `CLAUDE.md` project-identity instruction | sub-003 | Sub-003 adds project-identity loading. This sub-spec adds context loading AFTER that instruction. |
| `copilot-instructions.md` cleaned refs | sub-003 | Sub-003 fixes framework-contract.md reference. This sub-spec adds context loading instruction. |

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| sub-003 not yet applied when this runs | HIGH | Read files at execution time to find correct insertion points. Do not assume line numbers. |
| Language count discrepancy (13 vs 14) | LOW | Spec says 13 but rust stays. Use 14 in ai-build.md enumeration. Flag in self-report. |
| Python code references to ruby/elixir (autodetect.py, etc.) | MEDIUM | Explicitly OUT OF SCOPE per parent spec. Do not modify. Document in verification. |
| Template instructions directory cleanup | LOW | ruby.instructions.md and elixir.instructions.md not mentioned in sub-spec scope but are direct derivatives. Include deletion. |

## Confidence: 95%

All files identified. Patterns well understood. The only ambiguity is the exact insertion point in CLAUDE.md/copilot-instructions.md which depends on sub-003's changes -- mitigated by reading files at execution time.

## Self-Report

**Status**: COMPLETE (12/12 tasks)
**Confidence**: 100%

### Summary

All 12 tasks executed successfully with zero retries.

### Deletions (Tasks 1-4)
- Deleted 6 language context files: ruby.md, elixir.md, universal.md from both dogfood and template directories
- Deleted 2 instruction files: ruby.instructions.md, elixir.instructions.md from template instructions directory

### Creations (Tasks 5-6)
- Created `cpp.md` (329 lines) in both dogfood and template directories. Covers: modern C++ standards (C++17/20), memory management (RAII, smart pointers), naming conventions, error handling, const correctness, concurrency, move semantics, templates/concepts, common pitfalls (UB), performance, build/tooling (compiler warnings, sanitizers, clang-tidy), testing (Google Test/Catch2), header hygiene, anti-patterns
- Created `lang-generic.md` handler in all 3 IDE mirrors. Follows lang-python.md structure with parameterized language detection, context-file-driven checks, severity mapping, and diagnostic tool cross-reference

### Edits (Tasks 7-10)
- Added Step 2b (Language-Specific Review) to all 3 review.md mirrors with dedicated handler list and generic fallback dispatch
- Added section "### 10. Context Loading" to CLAUDE.md (root + template) after sub-003's project-identity instruction
- Added step 4 "Load contexts" to copilot-instructions.md Session Start Protocol (root + template), fixed duplicate numbering (3,3 -> 3,4,5,6)
- Replaced generic `{detected_language}` in ai-build.md with enumerated list: 14 languages, 15 frameworks

### Verification (Tasks 11-12)
- Grep confirms zero stale references to ruby.md/elixir.md/universal.md outside spec files
- All out-of-scope files (autodetect.py, sync_command_mirrors.py, test_autodetect.py, test_wizard.py, injection_patterns.py) confirmed UNTOUCHED
- File counts: dogfood languages = 14, template languages = 14, template instructions = 16
- All 3 review.md mirrors identical. All 3 lang-generic.md mirrors identical

### Decisions
- Language count is 14 (not 13) because rust.md stays per spec analysis. The parent spec line 219 says "(14)" which is correct
- copilot-instructions.md had duplicate step numbering (two items numbered "3"). Fixed by renumbering to sequential 3,4,5,6 when adding the context loading step
- cpp.md at 329 lines exceeds the 200-line minimum. Depth was warranted given C++ complexity (memory safety, UB, concurrency all need thorough coverage)
