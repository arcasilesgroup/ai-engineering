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

> **spec-119 D-119-05** This handler emits structured violation envelopes
> per `.ai-engineering/schemas/lint-violation.schema.json`. The markdown
> table below is a *derived view* rendered through
> `src/ai_engineering/lint_violation_render.py:render_table`. The
> canonical form is the JSON envelope:
>
> ```json
> {
>   "rule_id": "stable-kebab-id",
>   "severity": "error | warning | info",
>   "expected": "concrete representation",
>   "actual": "concrete representation",
>   "fix_hint": "one-line directive",
>   "file": "optional/path",
>   "line": 42
> }
> ```
>
> Tools that consume compliance results MUST read the structured form
> directly. The markdown table is only for human review.

Status values:
- `checked` -- validated against loaded context, no violations found
- `deviation` -- structured violation envelope written to the compliance trace. The envelope's `severity` field maps to the legacy table's status: `error` was `deviation`, `warning` was `risk`, `info` was `note`.
- `n/a` -- loaded context file has no section for this category

## 6e. Deviation-found behavior

If any envelope has `severity: error`, fix the violation before proceeding to post-edit validation. After fixing, append a `resolved: true` flag and a `resolution_note` field to the envelope so the audit chain records the fix.

```
| Anti-patterns | deviation (fixed) | bare except at line 42 -- fixed to except ValueError per python.md |
```

Do not proceed with an unresolved `severity: error` envelope. If a violation is intentional and cannot be fixed, set `severity` to `info` and use `fix_hint` to document the justification; the `/ai-review` skill will surface the entry as accepted-risk for human review.
