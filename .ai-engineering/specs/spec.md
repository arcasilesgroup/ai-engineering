---
spec: spec-176
slug: instinct-corpus-unicode-churn
title: "Fix instinct-corpus unicode-escaping churn (allow_unicode)"
status: in-progress
audience: framework-dev
summary: >-
  The instinct corpus writer dumps observations.yml with yaml.safe_dump WITHOUT
  allow_unicode=True, so every genuine write re-escapes literal unicode (— → —,
  § → \xA7) and diverges from the committed literal-unicode baseline — leaving
  observations.yml perpetually dirty after /ai-pr and /ai-branch-cleanup. Fix:
  allow_unicode=True on all corpus safe_dump sites (hook + template twin + pip
  twin), regen the hooks-manifest, re-commit the corpus literal, close the
  superseded sweep PR #597.
---

# Fix instinct-corpus unicode-escaping churn (allow_unicode)

## Summary

`observations.yml` shows as Modified in the working tree after almost every
`/ai-pr` and `/ai-branch-cleanup`, and we have been excluding it from PRs all
along instead of fixing it.

Root cause (diagnosed): the committed corpus stores unicode **literally** (`—`,
`§`), but BOTH corpus writers call `yaml.safe_dump(...)` **without
`allow_unicode=True`**:

- `.ai-engineering/scripts/hooks/_lib/instincts.py:243` (`_dump_yaml_or_json`,
  used by `_save_instincts_document:398`) + its install template twin.
- `src/ai_engineering/state/instincts.py:75,150` (the pip twin writer).

`safe_dump` defaults to `allow_unicode=False`, which ESCAPES non-ASCII
(`—`→`—`, `§`→`\xA7`). So whenever a genuine observation change triggers a
write, the writer re-dumps the WHOLE corpus escaped → it diverges from the
literal baseline → a large, never-reconciling diff. spec-162 only added the
content-idempotency guard (skip no-op writes — which works, it compares parsed
dicts); it never fixed the serialization. The escaping surfaces on every session
that records a real observation.

Fix: emit literal unicode (`allow_unicode=True`) so writer output matches the
committed form; regen the sha-pinned hooks-manifest; re-commit the corpus
literal; close the now-superseded sweep PR #597 (it committed the escaped form).

## Goals

- All corpus `yaml.safe_dump` calls pass `allow_unicode=True`, in lockstep:
  hook `_lib/instincts.py`, its template twin, and the pip twin
  `src/ai_engineering/state/instincts.py`.
- `hooks-manifest.json` regenerated (instincts.py is sha-pinned) so the integrity
  gate stays green.
- `observations.yml` restored to its literal-unicode committed form (working-tree
  churn reverted).
- A regression test in both instinct test suites: a corpus containing `—`/`§`
  writes LITERAL unicode (no `—`/`\xA7`), and a second identical save is a
  no-op (idempotent).
- PR #597 closed as superseded.

## Non-Goals

- No change to the spec-162 content-idempotency guard (it works — compares parsed
  dicts, escaping-immune).
- No change to the `updatedAt` bump semantics (only advances on real change today).
- No change to the gitignored observe-event NDJSON path or the consolidation flow.
- No reformat of unrelated corpus content beyond the unicode round-trip.

## Decisions

### D-176-01 — Add `allow_unicode=True` to every corpus safe_dump

Pass `allow_unicode=True` at `_lib/instincts.py:243`, the byte-identical template
twin `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/instincts.py:243`,
and the pip twin `src/ai_engineering/state/instincts.py:75,150`.

**Rationale:** the committed corpus is literal unicode; `safe_dump`'s default
escaping diverges from it on every write. `allow_unicode=True` makes the emitter
match the baseline, so genuine writes produce minimal diffs and no whole-corpus
re-escape churn. Smallest correct fix (§10.1 KISS).

### D-176-02 — Regenerate the hooks-manifest

`_lib/instincts.py` is sha-pinned; editing it changes the sha. Regenerate
`hooks-manifest.json` so `run_hook_safe` integrity stays green.

**Rationale:** hook-integrity is a standing contract; a stale sha would disable
the hook (per the editing-guard-self-disables-via-integrity class).

### D-176-03 — Restore observations.yml to the literal baseline

Revert the working-tree `observations.yml` to HEAD (already literal). The
session's pending observations live in the gitignored event NDJSON, not the
corpus, so nothing is lost.

**Rationale:** reconcile the diverged working tree; the fixed writer keeps it
literal going forward.

### D-176-04 — Close PR #597 as superseded

PR #597 (chore/session-watch-sweep) committed the escaped corpus — the bug's
output. Close it; re-consolidation after this fix will produce a clean literal
corpus if/when needed.

**Rationale:** merging #597 would persist the escaped form; this fix supersedes
it. No shim (CONSTITUTION §3).

### D-176-05 — Regression test in both suites

Add a test (hook suite `tests/unit/test_lib_instincts.py` + pip suite
`tests/unit/test_instinct_state.py`): save a corpus containing `—`/`§`, assert
the on-disk bytes contain literal `—`/`§` and NOT `—`/`\xA7`, and that a
second identical save does not change the file (idempotent).

**Rationale:** pin the fix so a future `safe_dump` regression (dropping
`allow_unicode`) fails a test (§10.5 TDD).

## Risks

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Hook twin / manifest drift leaves hooks broken | Medium | Medium | D-176-02 manifest regen + byte-identical twin; hook-integrity gate on commit. |
| Existing escaped corpus on other branches (#597) | Low | Low | D-176-04 close #597; literal is the canonical form. |
| Dual-writer parity missed (hook vs pip twin) | Medium | Low | D-176-01 fixes all 3 surfaces; D-176-05 tests both suites. |
| `allow_unicode=True` changes some other dumped field unexpectedly | Low | Low | Round-trip test asserts content stable, only escaping changes. |
