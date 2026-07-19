---
name: ai-engineering-issue
description: "Files an upstream bug or improvement report against `arcasilesgroup/ai-engineering` (the framework repo) with strict seven-vector redaction, mandatory human confirmation, and an archived sanitized copy. Trigger for 'report this upstream', 'file an ai-engineering bug', 'this looks like a framework bug', 'tell anthropic / arcasiles about this'. Not for your own project's board (use /ai-issue); not for security disclosure (use the private channel listed in CONSTITUTION.md)."
effort: mid
argument-hint: "<short-title> [--include <file:line> ...]"
tags: [security, support, upstream, redaction, framework]
requires:
  bins:
    - gh
---


# Upstream Bug Report

Files a bug/improvement against the ai-engineering framework with strict redaction and explicit consent: runs the shared redactor in strict mode, renders the body for review, requires a typed `confirm` token, then shells `gh issue create --repo arcasilesgroup/ai-engineering`. A sanitized copy is archived under `.ai-engineering/support/upstream-reports/`.

```
/ai-engineering-issue "<short-title>"
/ai-engineering-issue "<short-title>" --include path/to/file.py:42
```

## Workflow

Principles: §10.4 DRY (single redactor service `_shared/redactor.py:redact`, D-134-09 — no per-skill regex sprawl); §13.4 anonymous content (no PII / machine paths / operator names reach the upstream repo, enforced before render).

1. **Preflight auth.** `gh auth status`. On failure, refuse with the fix hint and exit non-zero.
2. **Capture context.** Read active spec frontmatter, latest `framework-events.ndjson` tail (≤10 entries), any `--include` targets, plus the title from `$ARGUMENTS`. Coerce to text.
3. **Strict redaction.** Call `python -c "from ai_engineering._shared.redactor import redact; print(redact(text, strictness='strict'))"`. Strict mode applies all seven vectors (see table).
4. **Compose body.** Upstream-report template: summary (≤3 sentences), reproduction steps, expected vs actual, environment metadata (redacted values only), references (commit SHA + spec ID + framework version from `manifest.yml`).
5. **Render preview.** Print the full composed body. The render uses the SAME string that will be posted — no second pass between confirmation and `gh issue create`.
6. **Confirmation gate.** Prompt: "type `confirm` to file, or anything else to abort." Any input other than the literal `confirm` → exit non-zero "report not filed". Mandatory — automated callers must also pass `confirm`. Rejects empty input, `y`, `yes`, quoted/capitalized variants. No `--force` flag. If the preview shows a missed leak: abort, edit the source context, re-invoke.
7. **Submit.** `gh issue create --repo arcasilesgroup/ai-engineering --title <t> --body <redacted> --label "ai-engineering,bug"`. Capture URL.
8. **Archive.** Write the redacted body to `.ai-engineering/support/upstream-reports/{date}-{slug}.md` (slug = kebab-case title, ≤50 chars). Append a `Submitted-Issue:` trailer with the step-7 URL. Audit via `framework_event kind=upstream_bug_filed`.

## Sanitization Vectors

Strict mode (`_shared.redactor.redact(text, strictness="strict")`) enforces seven patterns. Verify each against the rendered preview before confirming.

| Vector | Pattern | Replacement |
|--------|---------|-------------|
| 1. secret | `api_key|token|secret|password|authorization|credentials|auth` + value ≥4 chars | `key + sep + [REDACTED]` |
| 2. user-home path | `/Users/<user>/...` | `$HOME/...` |
| 3. private path | `/private/<segment>/...` | `[REDACTED-PATH]` |
| 4. email | `local@host.tld` | `[REDACTED-EMAIL]` |
| 5. GitHub token | `gh[psouar]_<36+chars>` | `[REDACTED-GH-TOKEN]` |
| 6. username / hostname CLI | `whoami=|hostname=|user_name=` assignments | `key=[REDACTED-USER]` / `[REDACTED-HOST]` |
| 7. state.db SQL | line containing both `state.db` AND a SQL keyword | `[REDACTED-DB]` |

Redaction is best-effort regex. Reviewers MUST still scan the preview for context-specific leaks (project names, customer references, business logic) before typing `confirm`.

## Examples

User: "report upstream — the `/ai-build` skill hangs when the patch block is empty"

```
/ai-engineering-issue "/ai-build hangs on empty patch block"
```

Runs `gh auth status` (green), captures the last 10 framework events + active spec frontmatter, redacts everything strict (a `/Users/...` path becomes `$HOME/...`), renders the preview, waits for `confirm`. On `confirm`, files the issue and archives the sanitized copy. Any other input aborts with "report not filed".

## Integration

Called by: user directly (after they encounter a framework bug). Reads: `.ai-engineering/manifest.yml`, `.ai-engineering/state/framework-events.ndjson` (tail), active spec frontmatter, optional `--include` targets. Writes: `.ai-engineering/support/upstream-reports/{date}-{slug}.md`. Audited: `framework_event kind=upstream_bug_filed`. Pairs with: `_shared/redactor.py` (single redaction service per D-134-09). See also: `/ai-issue` (project-board issues, no redaction).

$ARGUMENTS
