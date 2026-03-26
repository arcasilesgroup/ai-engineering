---
id: sub-005
parent: spec-080
title: "Build Standards Validation"
status: planning
files: [".claude/skills/ai-code/SKILL.md", ".claude/skills/ai-review/handlers/lang-generic.md"]
depends_on: [sub-004]
---

# Sub-Spec 005: Build Standards Validation

## Scope
Add build-time lightweight self-check to /ai-code that validates critical categories from loaded contexts (naming conventions, anti-patterns, error handling). The self-check produces a compliance trace (category -> checked/deviation) in the task output. Verify ai-review's lang-generic.md and per-language handlers continue full exhaustive validation without regression. Bridge the gap: critical violations caught at write-time, comprehensive validation at review-time.

## Exploration

### Current Architecture

**ai-review validation (review-time, exhaustive):**
- `lang-generic.md` applies 5 categories from loaded context files: naming conventions, idiomatic patterns, anti-patterns, error handling, testing. Each category is checked against every changed line.
- 8 dedicated `lang-{language}.md` handlers exist (cpp, flutter, go, java, kotlin, python, rust, typescript). These provide deep, language-specific checks (e.g., Python handler checks SQL injection via f-strings, mutable defaults, bare except, framework-specific patterns).
- `lang-generic.md` only activates for languages WITHOUT a dedicated handler. Languages with a dedicated handler are skipped by the generic handler entirely.
- All handlers produce structured YAML findings with severity, confidence, self-challenge, and context_rule traceability.
- Review dispatches all handlers as Step 2b (parallel with 8 concern agents), aggregates in Step 3.

**ai-build current state (build-time, no validation):**
- `ai-build.md` has a `code` classify mode that is a single 4-word entry: "Write code following stack standards."
- No self-check procedure exists. No compliance trace is emitted.
- Post-edit validation (Step 4 in ai-build) runs only deterministic linters (ruff, tsc, cargo check, etc.) and an optional Guard advisory. These are tool-based checks, not context-rule checks.
- sub-004 will create `/ai-code` SKILL.md with pre-coding checklist, context loading, and a self-review step. Sub-005 defines what that self-review step validates.

**Context files structure (what gets validated against):**
- 14 language contexts exist: bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, rust, sql, swift, typescript.
- Each context file has sections covering a subset of: naming conventions, code style, anti-patterns, error handling, type safety, testing patterns, performance, security patterns.
- Section naming varies per language (e.g., Python has "Common Anti-Patterns" and "Error Handling" as H2 headers; TypeScript has "Naming Conventions" table, "Common Anti-Patterns" H2, "Error Handling" H2).
- Not all languages have all categories. The self-check must handle missing sections gracefully (report as "not applicable" rather than "checked").

**Self-Report pattern (from phase-implement.md):**
- Agents produce a `## Self-Report` table classifying every piece of work: file/function, classification (real/aspirational/stub/failing/invented/hallucinated), notes.
- The compliance trace for sub-005 is a different artifact -- it reports category-level compliance, not file-level work classification. Both are structured tables appended to task output.

### Gap Analysis

| Concern | Build-time (current) | Build-time (proposed) | Review-time (unchanged) |
|---------|---------------------|----------------------|------------------------|
| Naming conventions | None | Lightweight check: verify new names follow context file conventions | Full line-by-line check + severity mapping |
| Anti-patterns | None | Flag code matching anti-patterns listed in loaded context | Full check + framework-specific anti-patterns |
| Error handling | None | Verify error handling follows documented conventions | Full check + severity escalation for bare catches |
| Idiomatic patterns | None | Not in scope (review-only) | Full check via lang-generic categories |
| Testing patterns | None | Not in scope (review-only) | Full check via lang-generic categories |
| Security patterns | None | Not in scope (dedicated ai-security skill) | Security agent + lang-specific handlers |

### Design Decisions

**D1: Three critical categories only.** The parent spec explicitly names "naming conventions, anti-patterns, error handling" as the build-time self-check scope. Idiomatic patterns and testing patterns remain review-only to keep build-time checks lightweight and fast.

**D2: Compliance trace, not YAML findings.** The build-time self-check produces a compact compliance trace (category -> checked/deviation), not the full YAML findings format used by review handlers. This keeps build output readable and avoids duplicating review's structured format.

**D3: Context-section mapping is best-effort.** The self-check maps context file H2 headers to the three critical categories. If a context file lacks a relevant section (e.g., bash.md might not have "Naming Conventions"), the trace reports "n/a" for that category. No false compliance claims.

**D4: No regression to review handlers.** This sub-spec does NOT modify lang-generic.md or any lang-{language}.md handler. The only change to lang-generic.md is adding a comment clarifying its role as the exhaustive review-time counterpart to build-time checks. Review handlers continue unchanged.

**D5: Compliance trace format.** Modeled after the Self-Report table from phase-implement.md but adapted for category-level reporting:

```markdown
### Compliance Trace

| Category | Status | Details |
|----------|--------|---------|
| Naming conventions | checked | All new names follow {lang}.md conventions |
| Anti-patterns | deviation | `bare except` at line 42 matches python.md anti-pattern |
| Error handling | checked | Error handling follows documented conventions |
```

Status values: `checked` (validated, no issues), `deviation` (violation found, details column explains), `n/a` (context file has no rules for this category).

### File Ownership

| File | Action | Reason |
|------|--------|--------|
| `.claude/skills/ai-code/SKILL.md` | MODIFY | Add self-check procedure and compliance trace format to the skill created by sub-004 |
| `.claude/skills/ai-review/handlers/lang-generic.md` | MODIFY | Add clarifying comment documenting its role as exhaustive review-time validation (no behavioral change) |

### Boundaries

- Does NOT create ai-code/SKILL.md (sub-004 creates it).
- Does NOT modify any per-language review handler (lang-python.md, lang-typescript.md, etc.).
- Does NOT add runtime enforcement or tool execution -- the self-check is instruction-based (the agent validates its own output against loaded context rules).
- Does NOT change ai-build.md post-edit validation (linter/Guard steps remain independent).
