# Handler: Compliance Trace

## Purpose

Self-review protocol for build-time compliance checking. Lightweight check covering 3 critical categories. Full exhaustive validation (5 categories including idiomatic patterns and testing) is deferred to /ai-review.

## 6a. Identify applicable context file

For each file touched, identify the language from its extension (same mapping as lang-generic.md Step 1). The applicable context file `.ai-engineering/contexts/languages/{lang}.md` was already loaded in Step 0.

## 6b. Map categories to context file sections

Scan the loaded context file's H2 headers (`##`) to locate the relevant sections for each category. Not all languages have all sections -- report `n/a` when the context file lacks a matching section.

| Category | Match H2 headers containing | Example headers |
|----------|----------------------------|-----------------|
| Naming conventions | "naming", "conventions", "style" | `## Naming Conventions`, `## Code Style` |
| Anti-patterns | "anti-pattern" | `## Common Anti-Patterns`, `## Anti-Patterns` |
| Error handling | "error handling", "error", "exception" | `## Error Handling`, `## Exception Handling` |

If a context file has no H2 header matching a category, that category is `n/a` for the language.

## 6c. Check each category

1. **Naming conventions** -- verify all new identifiers (functions, variables, classes, constants) follow the casing, prefixes, suffixes, and forbidden patterns documented in the matched section.
2. **Anti-patterns** -- verify no new code matches any anti-pattern explicitly listed in the matched section.
3. **Error handling** -- verify error handling in new code follows the conventions documented in the matched section (e.g., specific exception types, error propagation patterns, logging requirements).

## 6d. Produce the compliance trace

```
### Compliance Trace

| Category | Status | Details |
|----------|--------|---------|
| Naming conventions | checked | All new names follow {lang}.md conventions |
| Anti-patterns | checked | No anti-patterns from {lang}.md detected |
| Error handling | n/a | {lang}.md has no error handling section |
```

Status values:
- `checked` -- validated against loaded context, no violations found
- `deviation` -- violation found; Details column names the specific rule and location
- `n/a` -- loaded context file has no section for this category

## 6e. Deviation-found behavior

If any category has status `deviation`, fix the violation before proceeding to post-edit validation. After fixing, update the compliance trace to record the fix:

```
| Anti-patterns | deviation (fixed) | bare except at line 42 -- fixed to except ValueError per python.md |
```

Do not proceed with a `deviation` status that has not been fixed. If a deviation is intentional and cannot be fixed, document the justification in the Details column and escalate to the user for approval.
