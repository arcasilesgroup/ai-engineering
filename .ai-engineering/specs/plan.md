---
title: "Plan — spec-176 instinct-corpus unicode-escaping churn fix"
spec: spec-176
slug: instinct-corpus-unicode-churn
status: approved
pipeline: hotfix
execution_route:
  version: 1
  spec: spec-176
  executor: build
  automation: build
  concern_count: 1
  estimated_files: 5
  reason: "Single-concern hotfix: add allow_unicode=True to the corpus safe_dump sites (3 surfaces) + regen sha-pinned hooks-manifest + revert the corpus + 2 regression tests. Mechanical but touches a sha-pinned hook (manifest regen) and a dual-writer twin."
  safe_next_command: "/ai-build"
safe_next_command: "/ai-build"
---

# Plan — spec-176: instinct-corpus unicode-escaping churn fix

## Architecture

Pattern: `ad-hoc` one-flag fix. `yaml.safe_dump(data, sort_keys=False)` →
`yaml.safe_dump(data, sort_keys=False, allow_unicode=True)` at the corpus-dump
sites, mirrored across the hook lib + its install-template twin + the pip twin.
No logic change; the spec-162 idempotency guard and `updatedAt` semantics are
untouched.

## Phases

### Phase 1 — fix the serializer (all 3 surfaces)

- [x] T-1 — `allow_unicode=True` on the hook `_dump_yaml_or_json` + template twin
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/_lib/instincts.py:243`, `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/instincts.py:243`
  - Principles applied: §10.1 KISS, §10.4 DRY (byte-identical twin)
  - Patch (deterministic):
    ```diff
    -        payload = yaml.safe_dump(data, sort_keys=False)
    +        payload = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    ```
  - Gate: both files identical; `grep allow_unicode` present at line 243 in each.

- [x] T-2 — `allow_unicode=True` on the pip-twin writer
  - Agent: build
  - Files: `src/ai_engineering/state/instincts.py:75`, `src/ai_engineering/state/instincts.py:150`
  - Principles applied: §10.4 DRY (dual-writer parity), §10.1 KISS
  - Patch (deterministic):
    ```diff
    -        yaml.safe_dump(default_instincts_document(), sort_keys=False),
    +        yaml.safe_dump(default_instincts_document(), sort_keys=False, allow_unicode=True),
    ```
    ```diff
    -        yaml.safe_dump(document, sort_keys=False),
    +        yaml.safe_dump(document, sort_keys=False, allow_unicode=True),
    ```
  - Gate: both pip-twin dump sites carry `allow_unicode=True`.

### Phase 2 — integrity + corpus reconcile

- [x] T-3 — Regenerate the hooks-manifest (instincts.py sha-pinned)
  - Agent: build
  - Files: `.ai-engineering/state/hooks-manifest.json`
  - Principles applied: §10.6 SDD (integrity contract)
  - Patch (deterministic): N/A — run the regen script (`regenerate-hooks-manifest.py` via `run-hook.sh`, NOT bare python3 3.9 — datetime.UTC).
  - Gate: `hooks-manifest.json` `instincts.py` sha == file sha; commit-msg `hook-integrity` PASS.

- [x] T-4 — Restore observations.yml to the literal baseline
  - Agent: build
  - Files: `.ai-engineering/observations/observations.yml`
  - Principles applied: §10.1 KISS
  - Patch (deterministic): N/A — `git checkout HEAD -- .ai-engineering/observations/observations.yml`.
  - Gate: `git diff` on the file is empty (clean).

### Phase 3 — regression tests

- [x] T-5 — Add the literal-unicode + idempotent regression test (both suites)
  - Agent: build
  - Files: `tests/unit/test_lib_instincts.py`, `tests/unit/test_instinct_state.py`
  - Principles applied: §10.5 TDD
  - Patch (deterministic): N/A — judgment. Save a corpus whose entry contains `—` and `§`; assert the on-disk text contains literal `—`/`§` and NOT `—`/`\xA7`; assert a second identical save leaves the file byte-unchanged (idempotent guard holds).
  - Gate: both new tests fail BEFORE T-1/T-2 (RED), pass after (GREEN).

### Phase 4 — verify

- [x] T-6 — Verify
  - Agent: verify
  - Files: the instinct test suites (read-only)
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Gate: `pytest tests/unit/test_lib_instincts.py tests/unit/test_instinct_state.py tests/unit/hooks/test_instincts_lib_robustness.py -q` green; `ai-eng gate run --mode=local` 0 findings; a manual round-trip (`_save_instincts_document` on the HEAD corpus) leaves observations.yml byte-identical.

## Gate Criteria (plan-level)

- All 4 corpus `safe_dump` sites carry `allow_unicode=True`; hook lib == template twin.
- hooks-manifest regenerated; hook-integrity green.
- observations.yml clean (literal baseline); a re-dump of the unchanged corpus is byte-stable.
- Both instinct suites green; gate clean.

## Quality Outcome

T-1..T-6 complete. Verified deterministically (round-trip proof + regression tests); LLM review skipped as disproportionate for a one-flag serialization fix with an executable proof.

- **Implementation:** `allow_unicode=True` on all 4 corpus `safe_dump` sites (hook `_lib/instincts.py:243` + template twin + pip twin `state/instincts.py:75,150`); hooks-manifest regenerated (sha MATCH verified); `observations.yml` reverted to the literal baseline; regression tests in both suites.
- **Definitive proof:** re-dumping the REAL committed `observations.yml` through the fixed writer is **byte-IDENTICAL** (no churn) — the root cause is gone. `observations.yml` is no longer dirty in the working tree.
- **Tests:** 78 instinct-suite + 309 hooks + 2 new spec-176 (literal-unicode + idempotent) green. `ai-eng gate run --mode=local` → 0 findings. No suppressions.
- **Nothing excluded:** the fix made `observations.yml` clean, so there is no pre-existing churn to carry — this PR is fully self-contained.

## Notes

- Deliver-time (D-176-04): close PR #597 as superseded — it committed the escaped corpus.
- Non-Goals: idempotency guard (spec-162), updatedAt semantics, the NDJSON observe path untouched.
