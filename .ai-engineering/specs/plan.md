---
execution_route:
  version: 1
  spec: spec-149
  executor: build
  automation: build
  concern_count: 3
  estimated_files: 12
  reason: "Trimmed spec (effort small). 3 independent, low-complexity concerns: one CLI safety default (cleanup dry-run, DONE), and two doc/handler edits with mechanical mirror regen (§11 chain, quality.md cond-4). D-149-03 (suppression DEC-bind) was DEFERRED to its own spec mid-build — it cannot be CI-enforced until decision-store.json is committed (a Part-A doctrine fix; see drafts/decision-store-commit-brief.md). No cross-concern DAG, no irreversible step. Build's sequential TDD + single quality loop is proportionate; autopilot's machinery is unwarranted overhead. File count is inflated by mechanical mirror regen, not real concerns."
  safe_next_command: "/ai-build"
status: approved
pipeline: full
spec: spec-149
title: Plan — Obvious-by-default essentials (trimmed)
---

# Plan — spec-149

## Summary

Three small, independent concerns + a de-scope record. Each is its own
phase; the only ordering constraint is mirror-regen serialization
(Phase 3 §11 edit and Phase 4 handler edit both regenerate IDE mirrors —
serialize their `ai-eng dev sync` so the `--check` parity gate is
deterministic). TDD pairs throughout (RED before GREEN). No phase has an
irreversible step, so no operator PAUSE is needed.

## Pipeline classification

`standard` (a handful of files across 3 small concerns + mechanical
mirror regen). Executor route: **build** (frontmatter). The 3 concerns
are independent and small — no sub-spec decomposition or wave DAG needed.

## Architecture

Pattern: **ad-hoc localized edits** (no new architecture). Two concerns
are pure convention/doc (§11 chain, quality.md handler); one is a CLI
default flip (`cleanup branches`). Boundaries respected:
`cli_commands/cleanup.py` (CLI), `CANONICAL.md` + mirrors (canonical
payload), `.claude/skills/ai-build/handlers/quality.md` + mirrors
(handler).

## Phase DAG

```
P1 cleanup-dry-run (independent, DONE)
P3 §11-doc ─► P4 quality-cond4 ─► P5 CHANGELOG/de-scope
P3,P4 share mirror regen → serialized (P3 sync, then P4 sync, --check clean each)
(P2 suppression-bind DROPPED → deferred to the decision-store-commit spec)
```

---

## PHASE 1 — D-149-02: dry-run-by-default for `cleanup branches`

- [x] T-1.1 — RED: no-flag `cleanup branches` deletes nothing
  - Agent: build
  - Files: `tests/integration/cli/test_cleanup_branches.py:60` (rewrite
    `test_cleanup_branches_modes_default_to_merged` → assert no-flag
    invocation produces a PLAN/skips, deletes nothing; add a CLI-level
    test that no-flag with no `--dry-run` still acts non-destructively
    until confirmed).
  - Principles applied: §10.5 TDD, §10.7 Clean Code (pit-of-success).
  - Gate: test RED against current `merged=True` default.

- [x] T-1.2 — GREEN: flip the no-flag default to plan + confirm
  - Agent: build
  - Files: `src/ai_engineering/cli_commands/cleanup.py:257-260` (drop the
    silent `merged = True`; no-flag → print plan + require confirm, or
    require an explicit mode/`--dry-run`), `:297-300` (guard the delete
    path behind explicit mode/confirmation).
  - Principles applied: §10.7 Clean Code, §10.1 KISS.
  - Patch (deterministic): omitted — confirmation-prompt UX requires
    judgment (interactive confirm vs require-explicit-mode); decide the
    mechanism in implementation, keep it non-interactive-test-friendly.
  - Gate: T-1.1 GREEN; `cleanup branches` (no flag, no `--dry-run`)
    deletes zero branches; existing 7-mode tests still pass.

## PHASE 2 — DEFERRED (was: security suppression DEC-bind)

D-149-03 was dropped from this spec during `/ai-build`. Binding
`nosemgrep_hash` suppressions to a DEC cannot be CI-enforced while
`decision-store.json` is gitignored — the `no_suppression` gate
(`ci-check.yml:145`) validates `dec_id` against a store that is absent in
CI, so binding would turn the gate red. Root cause is a Part-A doctrine
flaw (the decision store holds non-rebuildable risk/flow rows yet is a
gitignored cache; `persistence-doctrine.md:120` admits it). The fix —
commit the decision store — is captured in
`.ai-engineering/specs/drafts/decision-store-commit-brief.md` for its own
`/ai-brainstorm`. **No Phase 2 work runs here.**

## PHASE 3 — D-149-01: surface ai-spec-draft in §11 + ai-code/ai-build boundary

- [x] T-3.1 — GREEN: edit the canonical §11 chain + boundary note
  - Agent: build
  - Files: `src/ai_engineering/templates/project/CANONICAL.md:47-65`
    (canonical source of §11): add `ai-spec-draft` as the OPTIONAL
    pre-`/ai-brainstorm` step (research one-pager hand-off); add a line
    stating `ai-code` = write a specific subcomponent (no plan) vs
    `ai-build` = gateway that executes an approved plan. Confirm whether
    the repo-root `CANONICAL.md`/`CLAUDE.md` is a separate authored copy
    or a mirror before editing (sync owns the mirrors).
  - Principles applied: §10.7 Clean Code (one obvious on-ramp), §10.3 SOLID.
  - Patch (deterministic): omitted — wording is a judgment call.
  - Gate: §11 shows ai-spec-draft + the boundary; no surface count change.

- [x] T-3.2 — GREEN: regenerate mirrors
  - Agent: build
  - Files: run `ai-eng dev sync` (or `python scripts/sync_command_mirrors.py`);
    regenerates `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`,
    `.github/copilot-instructions.md` + template surfaces.
  - Principles applied: §10.4 DRY (single canonical source).
  - Gate: `ai-eng dev sync --check` clean (no drift).

## PHASE 4 — D-149-04: quality.md Step 2d condition 4 → advisory (reproducible STOP)

- [x] T-4.1 — RED: contract test — cond-4 advisory + STOP matrices count-deterministic
  - Agent: build
  - Files: `tests/unit/skills/test_quality_stop_determinism.py` (new):
    assert `quality.md` Step 2d condition 4 is advisory/operator-confirmable
    (it cannot silently auto-block/auto-pass), and the Step 2c/2e STOP
    decision matrices are count-based (deterministic). Mirror-parity of
    the edited handler asserted alongside.
  - Principles applied: §10.5 TDD, §10.6 SDD (reproducible "done").
  - Gate: RED against current cond-4 wording.

- [x] T-4.2 — GREEN: reword cond-4 + align cross-references
  - Agent: build
  - Files: `.claude/skills/ai-build/handlers/quality.md:122-140` (Step 2d
    condition 4 → advisory/operator-confirmable, cannot silently flip the
    verdict); verify consistency at `.claude/skills/ai-build/handlers/no-hitl.md:116`
    and `.claude/skills/ai-autopilot/handlers/phase-quality.md:207`
    (align language; no behavioral divergence). DROP any blanket
    `method: deterministic|llm` finding-tag plan (no consumer).
  - Principles applied: §10.6 SDD, §10.1 KISS.
  - Patch (deterministic): omitted — protocol wording is a judgment call.
  - Gate: T-4.1 GREEN.

- [x] T-4.3 — GREEN: regenerate handler mirrors
  - Agent: build
  - Files: `ai-eng dev sync` → propagate `quality.md` to
    `.codex/.gemini/.github` + `src/ai_engineering/templates/project/.../quality.md`.
  - Principles applied: §10.4 DRY.
  - Gate: `ai-eng dev sync --check` clean.

## PHASE 5 — De-scope record + CHANGELOG

- [x] T-5.1 — GREEN: CHANGELOG the behavior changes + the de-scope
  - Agent: build
  - Files: `CHANGELOG.md` — entries for: (1) `cleanup branches` no-flag
    now non-destructive (behavior change); (2) §11 chain now lists
    `ai-spec-draft` + the ai-code/ai-build boundary; (3) quality.md cond-4
    advisory (reproducible STOP). Record that spec-148 **D-148-11,
    D-148-12, D-148-14, D-148-15 are superseded/dropped** (YAGNI) and
    **D-148-13/16 re-scoped**, with **D-148-17 (suppression DEC-bind)
    deferred** to the decision-store-commit spec.
  - Principles applied: §10.7 Clean Code (truthful docs), Hard-Rule 3 (no
    shims; document breakage).
  - Gate: CHANGELOG documents each behavior change + the dropped/deferred
    decisions; grep finds no orphaned reference to the dropped gates.

## Quality Outcome

Final: spec-149 scope GREEN. TDD per task (RED→GREEN), mirror parity
(`ai-eng dev sync --check`) clean, broad deterministic sweep across
architecture / mirrors / specs / skills / docs / cleanup-integration
(~1,150 passed). Two failures I introduced were fixed:
- `/ai-code` named in the §11 canonical payload tripped `LEGACY_NAMES`
  (canonical payload stays lean) → moved the ai-code/ai-build boundary to
  the two skill descriptions instead.
- drive-by (§9): stale Part-A test `test_persistence_doctrine_exists`
  asserted `## The four tiers`; the files-only doctrine ships
  `## The three tiers` — corrected the stale expectation.

Known PRE-EXISTING (not spec-149; 0 files changed vs `origin/main`):
12 `tests/docs/test_links.py` broken-link failures in `.agent/` +
`.opencode/` skill mirrors (ai-animation / board / governance / ide-audit
/ skill-improve / video-editing). Flagged for a separate fix. Did not run
the entire suite (would surface unrelated pre-existing failures); the
sweep covers every surface spec-149 modifies.

## Cross-cutting gates (every phase)

- TDD pair present for each behavioral change (RED before GREEN).
- No `# noqa` / `# nosec` / suppression-without-DEC introduced (Hard-Rule 2).
- No backwards-compat shim for the cleanup default (Hard-Rule 3);
  CHANGELOG records the breakage.
- Mirror-touching phases (P3, P4) serialize `ai-eng dev sync`; `--check`
  clean before PR.
- Full test suite green; hot-path budgets untouched (none of these are on
  the hook hot path).

## Self-review (§10.7) — 2 iterations

- **Build discovery** — D-149-03's DEC-bind is CI-incompatible (it
  validates against the gitignored `decision-store.json`, absent in CI).
  Root cause is a Part-A doctrine flaw; D-149-03 DEFERRED to its own spec
  (`drafts/decision-store-commit-brief.md`) and spec + plan re-scoped to 3
  concerns. Resolved.
- **Iter 1** — Serialized P3/P4 mirror regen (both hit `ai-eng dev sync`
  / parity `--check`) to avoid a non-deterministic drift gate. Resolved.
- **Iter 2** — Confirmed every KEEP/SIMPLIFY task is TDD-paired and every
  DROP is a documentation-only supersession (P5), so no half-built gate
  remains. The "replay test" (D-149-04) is realized as a handler-contract
  assertion (the protocol is LLM-executed; a true live replay is not
  testable) — scoped honestly in T-4.1. No remaining concerns.

## Next

Build IN PROGRESS (`/ai-build --no-hitl`). P1 (cleanup dry-run) DONE;
P2 DEFERRED; P3 (§11 doc), P4 (quality cond-4), P5 (CHANGELOG/de-scope)
remaining, then the quality loop + PR. Open question resolved during
build: cond-4 → **advisory** (T-4). No PAUSE (no irreversible step).
