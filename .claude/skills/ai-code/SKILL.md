---
name: ai-code
description: "Writes production code that satisfies stack-context standards on the first pass: interface-first design, backward-compatibility checks, lightweight self-review. Trigger for 'implement this', 'write the code for', 'add X to Y', 'build this function', 'make this work'. Not for tests; use /ai-test instead. Not for debugging; use /ai-debug instead. Not for refactoring; use /ai-simplify instead. Not for schema work; use /ai-schema instead. Not for executing an approved plan end-to-end; use /ai-build (the gateway)."
effort: mid
argument-hint: "[task description or file:target]"
---

# Code

Writes code that satisfies loaded context standards on the first pass — lightweight self-review at build-time; full validation deferred to `/ai-review`.

## Workflow

Principles applied: §10.1 KISS (write the minimal code that satisfies the requirement); §10.3 SOLID (define the interface before the implementation).

Step 0 — load contexts: read `.ai-engineering/manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` per stack + `.ai-engineering/overrides/_shared/conventions.md`; load `.ai-engineering/team/*.md`.

1. **Pre-coding checklist** — (a) restate the task in one sentence; (b) identify target files (modify vs create); (c) grep for similar implementations to match conventions; (d) read `.ai-engineering/state/decision-store.json` for relevant architectural decisions.
2. **File placement** — new files follow existing project structure (never invent paths); tests mirror source (`src/foo/bar.py` -> `tests/foo/test_bar.py`); never create top-level files without explicit instruction; if unsure, follow 3 similar files.
3. **Interface-first** — define public interfaces (protocols, abstract classes, type signatures) and document the contract (inputs, outputs, errors, side effects) before implementing; check touched modules' existing contracts first. Skip for trivial changes (single-function additions, config updates).
4. **Write code** — implement to all loaded standards + `.ai-engineering/reference/operational-principles.md`. Minimal code only.
5. **Backward compatibility** — public signature change: add a deprecation path or confirm the break is intentional; config format: parse backward-compatible; renamed exports: grep for and update every caller. Skip for internal/private code.
6. **Self-review** — run the compliance trace per `.ai-engineering/overrides/_shared/compliance-trace.md`.

## Common Mistakes

- Writing code before loading contexts (standards drift).
- Inventing new file paths instead of following existing project structure.
- Self-reviewing against general knowledge instead of loaded context rules.

## Examples

### Example — extend a module with backward compatibility

User: "add a `--strict` flag to the validate command without breaking existing callers"

```
/ai-code "add --strict flag to validate command, preserve existing behavior"
```

Loads stack context, places the change by mirroring existing structure, greps for callers, defines an additive flag whose default matches current behavior, runs the backward-compatibility check, then the compliance trace.

## Integration

Called by: `ai-build` agent, `/ai-build`, user directly. Calls: stack-specific linters (post-edit validation via `ai-build` Step 4). Transitions to: `/ai-test` (GREEN), `/ai-verify` (quality), `/ai-review` (review). See also: `/ai-test`, `/ai-debug`, `/ai-simplify`.

$ARGUMENTS
