---
total: 3
completed: 0
---

# Plan: sub-005 Build Standards Validation

## Plan

### T-5.1: Add self-check procedure and compliance trace to ai-code/SKILL.md

**Imports**: ai-code/SKILL.md (created by sub-004)

Locate the self-review step in ai-code/SKILL.md (sub-004 creates this skill with a self-review placeholder). Replace or enrich it with a concrete self-check procedure covering the three critical categories.

**Procedure to add (as a new step or enrichment of existing self-review step):**

1. After writing code and before post-edit validation, the agent performs a self-check against the loaded context files.
2. For each file touched, identify the language from extension (same mapping as lang-generic.md Step 1).
3. Read the applicable `.ai-engineering/contexts/languages/{lang}.md` (already loaded in Step 0 by sub-003's context loading enforcement).
4. Check three critical categories by scanning the context file for matching H2 sections:
   - **Naming conventions**: match against sections containing "naming", "conventions", "style" in the header. Verify all new identifiers (functions, variables, classes, constants) follow the documented patterns.
   - **Anti-patterns**: match against sections containing "anti-pattern" in the header. Verify no new code matches any listed anti-pattern.
   - **Error handling**: match against sections containing "error handling", "error", "exception" in the header. Verify error handling follows documented conventions.
5. Produce a compliance trace table in the task output.

**Compliance trace format to add to the skill:**

```markdown
### Compliance Trace

| Category | Status | Details |
|----------|--------|---------|
| Naming conventions | checked/deviation/n/a | Explanation or "All new names follow {lang}.md conventions" |
| Anti-patterns | checked/deviation/n/a | Explanation or "No anti-patterns from {lang}.md detected" |
| Error handling | checked/deviation/n/a | Explanation or "Error handling follows {lang}.md conventions" |
```

Status values:
- `checked` -- validated against loaded context, no violations found
- `deviation` -- violation found; Details column names the specific rule and location
- `n/a` -- loaded context file has no section for this category

**If deviation is found**: the agent MUST fix the deviation before proceeding to post-edit validation. The compliance trace records the fix: `deviation (fixed) -- original: bare except at line 42, fixed to except ValueError`.

**Files:**
- `.claude/skills/ai-code/SKILL.md`

**Done:**
- [ ] T-5.1 ai-code/SKILL.md contains a "Self-Check Against Loaded Contexts" step with the three-category procedure
- [ ] T-5.1 ai-code/SKILL.md contains the compliance trace format (table with Category, Status, Details)
- [ ] T-5.1 Status values (checked, deviation, n/a) are documented with clear definitions
- [ ] T-5.1 Deviation-found behavior is documented (fix before proceeding, record fix in trace)
- [ ] T-5.1 Category-to-header mapping logic is documented (how to find naming/anti-pattern/error sections in arbitrary context files)

### T-5.2: Add role clarification comment to lang-generic.md

Verify that lang-generic.md's existing 5-category exhaustive check (naming conventions, idiomatic patterns, anti-patterns, error handling, testing) remains intact and unchanged. Add a brief clarifying comment at the top of its Purpose or Integration section that documents the division of responsibility between build-time and review-time validation.

**Comment to add (after the existing Purpose paragraph):**

```
Note: Build-time validation in /ai-code performs a lightweight self-check of 3 critical categories (naming conventions, anti-patterns, error handling) as a first line of defense. This handler provides the exhaustive review-time validation of all 5 categories, including idiomatic patterns and testing -- the comprehensive second pass that catches anything build-time missed.
```

**Files:**
- `.claude/skills/ai-review/handlers/lang-generic.md`

**Done:**
- [ ] T-5.2 lang-generic.md contains a note clarifying its role as exhaustive review-time counterpart to build-time checks
- [ ] T-5.2 All 5 existing categories in Step 2 (naming, idiomatic, anti-patterns, error handling, testing) are unchanged
- [ ] T-5.2 No behavioral change to lang-generic.md -- output format, severity mapping, and procedure remain identical

### T-5.3: Validate no regression in per-language review handlers

Read each of the 8 dedicated per-language handlers to confirm they are NOT affected by sub-005 changes. Produce a verification note confirming each handler's check categories remain intact.

This is a read-only verification task. No files are modified.

**Handlers to verify:**
- lang-python.md (6 steps: detect, critical, high, medium, framework, diagnostics)
- lang-typescript.md
- lang-go.md
- lang-rust.md
- lang-java.md
- lang-kotlin.md
- lang-cpp.md
- lang-flutter.md

**Files:**
- (none modified -- read-only verification)

**Done:**
- [ ] T-5.3 All 8 per-language handlers verified: no modifications needed, all check categories intact
- [ ] T-5.3 Verification note appended to Self-Report confirming no regression

## Confidence Assessment

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| Scope clarity | 95% | Parent spec explicitly names 3 categories and compliance trace format. No ambiguity in what to build |
| Dependency risk | 75% | Depends on sub-004 creating ai-code/SKILL.md with a self-review placeholder. If sub-004 omits the placeholder or structures the skill differently, T-5.1 may need adaptation |
| Implementation complexity | 90% | Purely instructional changes to prompt files. No code, no runtime, no schema changes. The self-check is agent behavior defined in markdown |
| Regression risk | 95% | T-5.2 and T-5.3 are explicitly designed to verify no regression. lang-generic.md gets only a clarifying comment. Per-language handlers are untouched |
| Overall | 89% | High confidence. The only risk is sub-004's output shape |

## Exports

- Compliance trace format in ai-code/SKILL.md (Category/Status/Details table with checked/deviation/n/a statuses)

## Imports

- ai-code/SKILL.md (from sub-004) -- the skill file must exist with a self-review step that T-5.1 enriches

## Self-Report
[EMPTY -- populated by Phase 4]
