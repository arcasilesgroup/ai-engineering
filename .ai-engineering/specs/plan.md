---
plan: spec-168
spec: spec-168
title: Solution-intent discoverability, fail-open/closed doctrine, and TRY-lint fixes
status: approved
pipeline: full
architecture: ad-hoc
execution_route:
  version: 1
  spec: spec-168
  executor: build
  automation: assisted
  concern_count: 3
  estimated_files: 15
  reason: >
    Three cohesive, mostly-mechanical concerns (path reconcile + pointer, one
    doctrine section, two ruff rules + three fixes), already deep-explored with
    patch-ready hunks. Concern count crosses the autopilot guideline, but the
    work is small, tightly related, and patch-ready; autopilot's sub-spec
    decomposition + waves would add ceremony with no value. Build dispatches the
    cheap tier per deterministic patch.
  safe_next_command: "/ai-build"
---

# Plan — spec-168

Executes the slim spec: reconcile the stale `docs/solution-intent.md` references
to the canonical `.ai-engineering/` path (unbreaking the weekly drift runbook),
add a root-discoverable pointer, define the fail-open/closed doctrine once in
`gate-policy.md`, and land `ruff` `TRY004`/`TRY400` + their three fixes. No new
`ARCHITECTURE.md` (D-168-01 is a deliberate no-op).

**Architecture pattern**: ad-hoc (docs + config + three localized correctness
fixes). No new module, no new abstraction.

**Global gate (every phase)**: `ruff check src/ tests/` and the touched tests
stay green; no new lint suppression (§13.2); template twins edited in lockstep.

---

## Phase 0 — Regression guard (RED)

- [x] T-01 — Add a guard test: no tracked file may reference `docs/solution-intent.md`
  - Agent: build
  - Files: `tests/docs/test_solution_intent_path.py` (new)
  - Principles applied: §10.5 TDD (RED before GREEN), §10.7 Clean Code
  - Patch (deterministic): none — assert that `git ls-files` content contains no
    `docs/solution-intent.md` occurrence except in `CHANGELOG.md` (the move-history
    line) and under `.ai-engineering/specs/drafts/` (the unapproved root-move brief).
    Test MUST fail now (stragglers exist) — that RED is the gate.
  - Gate: `pytest tests/docs/test_solution_intent_path.py` is RED with ≥7 hits

---

## Phase 1 — Path reconcile (GREEN for T-01) — D-168-02

- [x] T-02 — Fix the solution-intent SoT table self-reference
  - Agent: build
  - Files: `.ai-engineering/solution-intent.md:783`
  - Principles applied: §10.4 DRY (single canonical path), §13.7 SSOT
  - Patch (deterministic):
    ```diff
    --- a/.ai-engineering/solution-intent.md
    +++ b/.ai-engineering/solution-intent.md
    @@ -783 +783 @@
    -| This document | `docs/solution-intent.md` |
    +| This document | `.ai-engineering/solution-intent.md` |
    ```
  - Gate: `grep -c 'docs/solution-intent.md' .ai-engineering/solution-intent.md` == 0

- [x] T-03 — Fix the architecture-drift runbook (path ×5 + stale section anchor)
  - Agent: build
  - Files: `.ai-engineering/runbooks/architecture-drift.md:12,16,30,208,216`
  - Principles applied: §10.7 Clean Code (correct the broken consumer), §10.1 KISS
  - Patch (deterministic): replace every `docs/solution-intent.md` →
    `.ai-engineering/solution-intent.md` (lines 12, 16, 30, 208, 216) AND fix the
    stale prose anchor `(section 2.2)` → `(section 3.1)` on line 16 — the mermaid
    map lives at §3.1, not §2.2 (verified). Do NOT change the `Last Review:` grep
    (line 4 of the target file still carries `Last Review: 2026-04-29`, so the
    pattern resolves once the path is fixed).
  - Note (out of scope): the subgraph grep extracts layer ids (CLI/Core/…), not
    package names — a pre-existing runbook looseness; leave it.
  - Gate: `grep -c 'docs/solution-intent.md' .ai-engineering/runbooks/architecture-drift.md` == 0

- [x] T-04 — Fix the docs-freshness runbook path
  - Agent: build
  - Files: `.ai-engineering/runbooks/docs-freshness.md:92,97`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): `docs/solution-intent.md` → `.ai-engineering/solution-intent.md` (lines 92, 97)
  - Gate: `grep -c 'docs/solution-intent.md' .ai-engineering/runbooks/docs-freshness.md` == 0

- [x] T-05 — Mirror both runbook fixes into the template twins (lockstep parity)
  - Agent: build
  - Files: `src/ai_engineering/templates/.ai-engineering/runbooks/architecture-drift.md`, `src/ai_engineering/templates/.ai-engineering/runbooks/docs-freshness.md`
  - Principles applied: §10.4 DRY (installer payload parity)
  - Patch (deterministic): apply the identical edits from T-03 + T-04 to the
    `templates/` copies (no CI guard enforces runbook parity — must be manual).
  - Gate: `grep -rc 'docs/solution-intent.md' src/ai_engineering/templates/.ai-engineering/runbooks/` == 0 across both twins

- [x] T-06 — Fix the template manifest comment
  - Agent: build
  - Files: `src/ai_engineering/templates/.ai-engineering/manifest.yml:58`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic):
    ```diff
    -# solution_intent: true — syncs docs/solution-intent.md on architecture changes.
    +# solution_intent: true — syncs .ai-engineering/solution-intent.md on architecture changes.
    ```
  - Gate: Phase-1 gate — T-01 now GREEN (zero stragglers outside CHANGELOG/drafts)

---

## Phase 2 — Root discoverability pointer — D-168-03

- [x] T-07 — Add a Surface Index pointer to the canonical map, regenerate mirrors
  - Agent: build
  - Files: `CANONICAL.md` (Source-of-Truth / Surface Index table), then `ai-eng dev sync`
  - Principles applied: §10.1 KISS (pointer, not duplicate), §13.7 SSOT
  - Patch (deterministic): none — locate the Surface Index / "Source of Truth"
    table in `CANONICAL.md` (mirrored to `CLAUDE.md` §Source of Truth) and add one
    row: `| Architecture / solution intent | .ai-engineering/solution-intent.md |`.
    Edit ONLY `CANONICAL.md` (+ `_CLAUDE_EXTRAS` if needed), never a generated
    mirror; run `ai-eng dev sync` to regenerate CLAUDE.md / AGENTS.md / copilot.
  - Gate: `ai-eng dev sync` clean; `tests/architecture/test_surface_parity.py` (or the mirror-parity suite) green

---

## Phase 3 — Fail-open/closed doctrine (TDD pair) — D-168-04

- [x] T-08 — RED: assert gate-policy.md states the error-handling posture doctrine
  - Agent: build
  - Files: `tests/unit/docs/test_gate_policy_doctrine.py` (new) or extend an existing docs test
  - Principles applied: §10.5 TDD
  - Patch (deterministic): none — assert `.ai-engineering/reference/gate-policy.md`
    contains a posture section naming all four invariants: security/integrity →
    fail **closed**; plumbing → fail **open** + **must log**; never silently
    swallow; never fail-open a security gate. MUST fail now (doctrine absent).
  - Gate: test RED

- [x] T-09 — GREEN: write the doctrine section + cross-links
  - Agent: build
  - Files: `.ai-engineering/reference/gate-policy.md` (new `## Error-handling posture` section, ~1 page, after `## Why this is not configurable`), `CANONICAL.md` §13 cross-link, `.ai-engineering/reference/principles.md` §10 cross-link; `ai-eng dev sync` if CANONICAL touched
  - Principles applied: §10.7 Clean Code, §10.4 DRY (one home, no new orphan doc)
  - Patch (deterministic): none — prose. State the four invariants + name the
    `audit:exempt:…-fail-closed-gates` marker as the escape hatch; cite the
    fail-open-hole precedents (`ci-branch-protection.md`, `supply-chain-control-matrix.md`).
    Do NOT inventory the ~273 call sites; do NOT add a new CI gate.
  - Gate: T-08 GREEN; mirror parity green if CANONICAL changed

---

## Phase 4 — ruff TRY004 + TRY400 (RED → GREEN) — D-168-05

- [x] T-10 — RED: enable the two rules
  - Agent: build
  - Files: `pyproject.toml:107`
  - Principles applied: §10.5 TDD (rule-as-RED), §10.7 Clean Code
  - Patch (deterministic):
    ```diff
    -select = ["E", "F", "W", "I", "UP", "B", "SIM", "C4", "RUF"]
    +select = ["E", "F", "W", "I", "UP", "B", "SIM", "C4", "RUF", "TRY004", "TRY400"]
    ```
  - Gate: `ruff check src/ tests/` RED with exactly 3 errors (TRY004 ×2, TRY400 ×1)

- [x] T-11 — GREEN: fix the two TRY004 wrong-exception-type bugs
  - Agent: build
  - Files: `src/ai_engineering/installer/phases/pipeline.py:220`, `src/ai_engineering/validator/categories/manifest_coherence.py:110`
  - Principles applied: §10.7 Clean Code (correct exception semantics)
  - Patch (deterministic):
    ```diff
    --- a/src/ai_engineering/installer/phases/pipeline.py
    +++ b/src/ai_engineering/installer/phases/pipeline.py
    @@ -220 +220 @@
    -                raise RuntimeError(msg)
    +                raise TypeError(msg)
    ```
    ```diff
    --- a/src/ai_engineering/validator/categories/manifest_coherence.py
    +++ b/src/ai_engineering/validator/categories/manifest_coherence.py
    @@ -110 +110 @@
    -        raise ValueError(f"Manifest payload must be a mapping: {manifest_path}")
    +        raise TypeError(f"Manifest payload must be a mapping: {manifest_path}")
    ```
  - Sub-check: grep callers/tests for `RuntimeError`/`ValueError` expectations on
    these paths; if a test asserts the old type, update it (same failure, corrected
    type). Run the two modules' unit tests.
  - Gate: `ruff check src/ tests/ --select TRY004` clean; affected unit tests green

- [x] T-12 — GREEN: fix TRY400 in BOTH hook-common copies + regenerate the manifest
  - Agent: build
  - Files: `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/hook-common.py:259`, `.ai-engineering/scripts/hooks/_lib/hook-common.py:259`, `.ai-engineering/state/hooks-manifest.json`
  - Principles applied: §10.7 Clean Code (preserve traceback), §10.4 DRY (twin parity)
  - Patch (deterministic) — apply to BOTH files:
    ```diff
    -        logger.error("hook-common: failed to append event: %s", exc)
    +        logger.exception("hook-common: failed to append event: %s", exc)
    ```
    Then re-pin the canonical hook's sha:
    `python .ai-engineering/scripts/regenerate-hooks-manifest.py`
  - Note: the canonical copy is sha-pinned in `hooks-manifest.json`; without the
    regen, integrity `enforce` mode disables the hook. The template copy is the
    installer payload (and what CI `ruff check src/` scans) — edit both in lockstep.
  - Gate: `ruff check src/ tests/` fully clean (0 errors); hook integrity verify passes; hook still runs

---

## Phase 5 — Final gate

- [x] T-13 — Full local verification
  - Agent: verify
  - Files: (read-only)
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): none
  - Gate: `ruff check src/ tests/` clean · `ruff format --check src/ tests/` clean ·
    `uv run ty check --exclude 'src/ai_engineering/templates/**' src/` clean ·
    `python -m spec_lint --check` (spec+plan) clean ·
    `pytest tests/docs tests/unit/docs tests/architecture -q` green ·
    hooks-manifest integrity verify green

---

## Task dependency order

```
T-01 (RED guard)
  └─> T-02 T-03 T-04 ──> T-05 (twins) ──> T-06 ──> [T-01 GREEN]
T-07 (pointer, independent)
T-08 (RED) ──> T-09 (GREEN)
T-10 (enable RED) ──> T-11 (TRY004) , T-12 (TRY400) ──> [ruff GREEN]
ALL ──> T-13 (final gate)
```

---

## Quality Outcome

All 13 tasks complete. Single quality round, fail-loud — **PASS, no
blocker/critical/high findings**.

| Gate | Result |
|---|---|
| `ruff check src/ tests/` | All checks passed (TRY004 ×2 + TRY400 ×1 fixed) |
| `ruff format --check src/ tests/` | clean |
| `ty check --exclude templates src/` | exit 0 (pre-existing `typer.core` warning in untouched `core/cli/decorators.py`) |
| `spec_lint --check` | 6/6, BLOCKERS=0 |
| pytest docs/unit-docs/architecture/installer/validator/hooks | 1171 passed, 0 failed |
| Guard tests (TDD) | T-01 + T-08 written RED, now GREEN |
| Mirror parity (`test_surface_parity`, `test_sync_mirrors`) | green; mirrors carry only the 2 added rows |
| Twin parity (runbooks ×2, hook-common) | byte-identical |
| Hook integrity | `hooks-manifest.json` re-pinned; sha matches edited file |

**Delivery note (excludes):** the commit MUST stage only spec-168 files. Pre-existing
dirty paths NOT part of this work — `observations.yml`, `proposals.md`, `uv.lock`,
`report.md` — must be excluded.
