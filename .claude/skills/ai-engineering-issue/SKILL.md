---
name: ai-engineering-issue
description: "Files an upstream bug or improvement report against `arcasilesgroup/ai-engineering` (the framework repo) with strict seven-vector redaction, mandatory human confirmation, and an archived sanitized copy. Trigger for 'report this upstream', 'file an ai-engineering bug', 'this looks like a framework bug', 'tell anthropic / arcasiles about this'. Not for your own project's board (use /ai-issue); not for security disclosure (use the private channel listed in CONSTITUTION.md)."
effort: mid
model_tier: sonnet
argument-hint: "<short-title> [--include <file:line> ...]"
tags: [security, support, upstream, redaction, framework]
requires:
  bins:
    - gh
---


# Upstream Bug Report

Files a bug or improvement against the ai-engineering framework with strict redaction and explicit consent. Runs the shared redactor in strict mode, renders the body for review, requires a typed `confirm` token, then shells `gh issue create --repo arcasilesgroup/ai-engineering`. A sanitized copy is archived under `.ai-engineering/support/upstream-reports/` for post-hoc audit.

```
/ai-engineering-issue "<short-title>"
/ai-engineering-issue "<short-title>" --include path/to/file.py:42
```

## Quick Start

1. Confirm authentication: `gh auth status` must succeed.
2. Invoke the skill with a short title. Optionally pass `--include` references to file:line locations whose surrounding context the skill captures (already redacted before display).
3. Review the rendered preview. The skill displays the exact body that would be posted publicly. Type `confirm` to proceed; type anything else to abort.
4. On confirmation, the skill shells `gh issue create --repo arcasilesgroup/ai-engineering` with the redacted body and labels `ai-engineering,bug`.
5. The sanitized body is also archived to `.ai-engineering/support/upstream-reports/{YYYY-MM-DD}-{slug}.md`.

## Workflow

Principles applied: §10.4 DRY (single redactor service `_shared/redactor.py:redact` per D-134-09 — no per-skill regex sprawl); §13.4 anonymous content (no PII / no machine paths / no operator names ever lands in the upstream repo, enforced before render not just after click).

1. **Preflight auth.** `gh auth status`. On failure, refuse with the remediation hint and exit non-zero.
2. **Capture context.** Read the active spec frontmatter, the latest `framework-events.ndjson` tail (≤10 entries), any `--include` targets, plus the user-supplied title from `$ARGUMENTS`. Coerce everything to text.
3. **Strict redaction.** Call `python -c "from ai_engineering._shared.redactor import redact; print(redact(text, strictness='strict'))"` (or import directly in skill orchestration). Strict mode applies all seven vectors — see the Sanitization Vectors section.
4. **Compose body.** Use the upstream-report template: summary (≤3 sentences), reproduction steps, expected vs actual, environment metadata (only redacted values), references (commit SHA + spec ID + framework version from `.ai-engineering/manifest.yml`).
5. **Render preview.** Print the full composed body to the operator. The render uses the SAME string that will be posted — there is no second pass between confirmation and `gh issue create`.
6. **Human-confirmation gate.** Prompt: "type `confirm` to file this issue, or anything else to abort". On any input other than the literal token `confirm`, exit non-zero with the message "report not filed". This step is mandatory — automated callers must also pass `confirm` explicitly.
7. **Submit.** `gh issue create --repo arcasilesgroup/ai-engineering --title "<t>" --body "<redacted>" --label "ai-engineering,bug"`. Capture the returned issue URL.
8. **Archive.** Write the redacted body to `.ai-engineering/support/upstream-reports/{date}-{slug}.md`. Slugify the title (kebab-case, ≤50 chars). Append a `Submitted-Issue:` trailer with the URL from step 7. Audit via `framework_event kind=upstream_bug_filed`.

## Sanitization Vectors

Strict mode (`_shared.redactor.redact(text, strictness="strict")`) enforces seven patterns. Reviewers may check each against the rendered preview before confirming.

| Vector | Pattern | Replacement |
|--------|---------|-------------|
| 1. secret | `api_key|token|secret|password|authorization|credentials|auth` + value ≥4 chars | `key + sep + [REDACTED]` |
| 2. user-home path | `/Users/<user>/...` | `$HOME/...` |
| 3. private path | `/private/<segment>/...` | `[REDACTED-PATH]` |
| 4. email | `local@host.tld` | `[REDACTED-EMAIL]` |
| 5. GitHub token | `gh[psouar]_<36+chars>` | `[REDACTED-GH-TOKEN]` |
| 6. username / hostname CLI | `whoami=|hostname=|user_name=` assignments | `key=[REDACTED-USER]` / `[REDACTED-HOST]` |
| 7. state.db SQL | line containing both `state.db` AND a SQL keyword | `[REDACTED-DB]` |

The redactor is best-effort regex. Reviewers MUST still scan the preview for context-specific leaks (project names, customer references, business logic) before typing `confirm`.

## Human Confirmation Gate

A typed `confirm` token is required. The skill rejects every other input including empty input, "y", "yes", quoted forms, capitalized variants. This is intentional — operators must read the rendered preview, not muscle-memory through it.

If the preview shows a leak the redactor missed, abort with anything other than `confirm`, edit the source context, and re-invoke. There is no `--force` flag.

## Examples

### Example 1 — file a framework bug

User: "report upstream — the `/ai-build` skill hangs when the patch block is empty"

```
/ai-engineering-issue "/ai-build hangs on empty patch block"
```

Skill runs `gh auth status` (green), captures the last 10 framework events plus active spec frontmatter, redacts everything with strict mode (the spec frontmatter contains a `/Users/...` path that becomes `$HOME/...`), renders the preview, waits for `confirm`. On `confirm`, files the issue and archives the sanitized copy.

### Example 2 — abort on preview

User: "actually that body has my customer's project name in it — abort"

```
abort
```

Skill exits non-zero with "report not filed". No issue is created. The operator edits the source context (removes the customer reference) and re-invokes the skill.

## Quick Reference

| Goal | Command |
|------|---------|
| File an upstream bug | `/ai-engineering-issue "<title>"` |
| Include specific files | `/ai-engineering-issue "<title>" --include src/foo.py:42` |
| Abort during preview | type anything other than `confirm` |

## Common Mistakes

- Confusing this skill with `/ai-issue` — that one creates issues on **your project's** board with no redaction. This skill targets the framework's upstream repo and applies strict redaction.
- Skipping the preview — there is no automated mode. The skill refuses to submit without a typed `confirm`.
- Assuming redaction is bulletproof — regex is best-effort. Always read the preview.

## Integration

Called by: user directly (after they encounter a framework bug). Reads: `.ai-engineering/manifest.yml`, `.ai-engineering/state/framework-events.ndjson` (tail), active spec frontmatter, optional `--include` targets. Writes: `.ai-engineering/support/upstream-reports/{date}-{slug}.md`. Audited: `framework_event kind=upstream_bug_filed`. Pairs with: `_shared/redactor.py` (single redaction service per D-134-09). See also: `/ai-issue` (project-board issues, no redaction).

$ARGUMENTS
