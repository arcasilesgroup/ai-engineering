---
execution_route:
  version: 1
  spec: spec-153
  executor: autopilot
  automation: hitl
  concern_count: 3
  estimated_files: 30
  reason: >
    Three concerns (spec/plan lifecycle automation, the .ai-engineering/ post-install
    client manual, the root GitHub landing) across six dependency-ordered waves with
    schema/state/public-surface changes and a parallelizable catalog-generator track.
    Multi-concern, ~30 files, DAG wave execution with parallel agents — /ai-autopilot
    is the executor.
  safe_next_command: "/ai-autopilot"
spec: spec-153
title: "Plan — Spec/Plan Lifecycle Automation and Client-Facing Capability READMEs"
status: draft
pipeline: full
total: 28
completed: 0
---

# Plan — Spec/Plan Lifecycle Automation and Client-Facing Capability READMEs

## Architecture

Pattern: **Hexagonal (ports-and-adapters)** — already the established shape of
`.ai-engineering/scripts/spec_lifecycle.py:1-25` (pure `LifecycleState` domain +
FSM table, filesystem infrastructure writers, a thin CLI application layer). This
plan preserves that split: new lifecycle behavior lands as application verbs over
the existing domain; the capability-catalog generator is a new read-only adapter
over the skill/agent files; the manifest `lifecycle:` block is config injected
through the existing `ManifestConfig` port. No new architectural seams.

Two evidence-driven scope corrections from `/ai-plan` exploration:

- **D-153-02 is mostly already satisfied.** `mark_shipped` and `_history_row_for`
  already render the Status cell from `record.state.value`
  (`spec_lifecycle.py:386,470`). The freeform `done`/`partial` strings are legacy
  rows preserved verbatim by `_migrate_rows` (`spec_lifecycle.py:258-286`). The only
  ledger work is correcting the one slug-keyed row, which falls out of the sidecar
  rename + re-render (Wave 2), plus a regression test.
- **D-153-03 gap is precise.** `/ai-pr` step 11 (`ai-pr/SKILL.md:67-70`) and
  `/ai-branch-cleanup` Phase 5 (`ai-branch-cleanup/SKILL.md:88-91`) only append rows
  for sidecars **already** in SHIPPED. Nothing auto-transitions IN_PROGRESS→SHIPPED
  on a merged branch. The backstop (Wave 4) adds merged-branch detection that calls
  `mark_shipped`.

## Design

`--skip-design` (implicit): both README surfaces are Markdown documentation, not UI
components. `handlers/design-routing.md` keyword set (React/CSS/animation/layout) does
not match. No `design-intent.md` produced. Recorded reason: documentation surfaces,
no interface design.

## Dependency DAG

```
Wave 1 (config/schema) ──┐
                         ├─► Wave 3 (archival+reaper) ──► Wave 4 (merge wiring)
Wave 2 (identity+ledger)─┘
Wave 5 (catalog generator, parallel) ──► Wave 6 (README content)
```

Waves 1+2 are independent and can run concurrently. Wave 3 depends on both. Wave 4
depends on Wave 3 (mark_shipped now snapshots). Wave 5 is independent of 1-4 and runs
in parallel. Wave 6 depends on Wave 5. Final gate (T-28) depends on all.

---

## Wave 1 — Config foundation (schema-first) [D-153-08]

> Schema MUST precede the manifest key: `manifest.schema.json` root sets
> `additionalProperties: false` (`.ai-engineering/schemas/manifest.schema.json:387`),
> so a `lifecycle:` key fails `ai-eng validate` until the schema declares it.

- [ ] T-1 — RED: lifecycle config parses + validates
- Agent: build
- Files: `tests/unit/config/test_manifest.py:131`, `tests/unit/test_doctor_phases_governance.py:87`
- Principles applied: §10.5 TDD, §10.6 SDD
- Patch (deterministic): none — test bodies require judgment (assert `LifecycleConfig` defaults `draft_ttl_days==30`, `reap_orphans` bool, `archive_layout=="per-spec-dir"`; assert `ManifestConfig.model_validate` accepts a `lifecycle` block; assert doctor `manifest-valid` passes with the block present).
- Gate: new tests fail (RED) for the right reason — `lifecycle` attribute / schema key absent.

- [ ] T-2 — GREEN: declare `lifecycle` block in manifest JSON schema
- Agent: build
- Files: `.ai-engineering/schemas/manifest.schema.json:314-388`
- Principles applied: §10.3 SOLID (open/closed — additive optional block)
- Patch (deterministic): none — mirror the `brainstorm` block shape (object, `properties` for `draft_ttl_days:{type:integer}`, `archive_layout:{type:string,enum:["per-spec-dir"]}`, `reap_orphans:{type:boolean}`, `additionalProperties:false`); add `lifecycle` to root `properties` only, NOT to the `required` array (lines 372-386).
- Gate: `ai-eng validate` manifest-coherence PASS with a `lifecycle` block present.

- [ ] T-3 — GREEN: `LifecycleConfig` Pydantic model + field on `ManifestConfig`
- Agent: build
- Files: `src/ai_engineering/config/manifest.py:272-370`
- Principles applied: §10.3 SOLID, §10.7 Clean Code
- Patch (deterministic): none — add `class LifecycleConfig(BaseModel)` with `draft_ttl_days:int=30`, `archive_layout:str="per-spec-dir"`, `reap_orphans:bool=True`; add `lifecycle: LifecycleConfig = Field(default_factory=LifecycleConfig)` to `ManifestConfig` (matches `BrainstormConfig` pattern).
- Gate: T-1 model tests GREEN.

- [ ] T-4 — GREEN: add `lifecycle:` block to manifest.yml + template mirror
- Agent: build
- Files: `.ai-engineering/manifest.yml:178`, `src/ai_engineering/templates/project/.ai-engineering/manifest.yml`
- Principles applied: §10.4 DRY (SSOT for retention config)
- Patch (deterministic):
  ```diff
  @@ manifest.yml (append after the brainstorm: block, ~line 178) @@
  +
  +# Spec lifecycle retention + archival knobs (spec-153 D-153-08).
  +lifecycle:
  +  draft_ttl_days: 30        # DRAFT sidecars older than this sweep to ABANDONED
  +  archive_layout: per-spec-dir  # archive/spec-NNN-<slug>/{spec.md,plan.md}
  +  reap_orphans: true        # sweep stray spec-*.md from specs/ root
  ```
- Gate: `ai-eng validate` PASS; T-1 doctor test GREEN.

**Wave 1 gate:** `pytest tests/unit/config/test_manifest.py` green; `ai-eng validate` PASS.

---

## Wave 2 — Identity + ledger [D-153-01 / D-153-02 / D-153-05 / D-153-09 / D-153-10]

- [ ] T-5 — RED: numeric identity + slug-resolution + enum-bound ledger
- Agent: build
- Files: `tests/unit/specs/test_spec_lifecycle.py`
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert: `start_new` sets `spec_id` matching `^spec-\d+$` while preserving `slug`; the minted number is `max(existing)+1`; `_load_state` resolves a record by slug when the id is non-numeric (fallback); a freshly shipped row's Status cell equals `LifecycleState.SHIPPED.value`.
- Gate: tests fail (RED) — `start_new` currently sets `spec_id=slug` (`spec_lifecycle.py:337`).

- [ ] T-6 — GREEN: numeric minting in `start_new`
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py:331-349`
- Principles applied: §10.1 KISS, §10.5 TDD
- Patch (deterministic): none — add `_next_spec_number(project_root)` (scan `_history_spec_ids` + sidecar `spec_id`s, parse `spec-(\d+)`, return max+1); set `spec_id=f"spec-{n:03d}"` in the new `SpecRecord` while keeping `slug=slug`. Keep `_find_by_slug` idempotency. Mint under the existing `specs-history` lock (D-153-05).
- Gate: T-5 minting assertions GREEN.

- [ ] T-7 — GREEN: slug-fallback resolver in `_load_state`
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py:171-198`
- Principles applied: §10.3 SOLID (one resolution port)
- Patch (deterministic): none — when `_sidecar_path(spec_id)` misses, fall back to `_find_by_slug`; raise only if both miss. Lets existing callers that pass a slug (consolidate-spec handler) keep working after the rename.
- Gate: T-5 resolver assertion GREEN.

- [ ] T-8 — RED+GREEN: sidecar id-migration verb
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py` (+ `tests/unit/specs/test_spec_lifecycle.py`)
- Principles applied: §10.5 TDD, §10.7 Clean Code
- Patch (deterministic): none — add `migrate_ids(project_root, *, dry_run)`: for each sidecar whose `spec_id` is non-numeric, derive `spec-NNN` (from spec.md frontmatter `spec:` when the slug matches, else next number), rewrite `spec_id`, `git mv` to `spec-NNN.json`, de-duplicate the `obvious-by-default`/`obvious-by-default-essentials` pair (keep the richer record, drop the stale). Register the CLI subparser (`spec_lifecycle.py:531-571`).
- Gate: migration test GREEN; dry-run lists 17 sidecars + the dedup.

- [ ] T-9 — GREEN: run id-migration + re-render ledger
- Agent: build
- Files: `.ai-engineering/state/specs/*.json`, `.ai-engineering/specs/_history.md`
- Principles applied: §10.6 SDD
- Patch (deterministic): none — execution task: `python .ai-engineering/scripts/spec_lifecycle.py migrate_ids` then `migrate-history`. The slug-keyed row `github-actions-supply-chain-hardening` (`_history.md:153`) becomes `spec-152` via re-render. This spec's own sidecar becomes `spec-153.json`.
- Gate: every `_history.md` ID cell matches `^spec-\d+$` or a legacy numeric; no slug-named sidecar remains; `spec-153.json` present.

- [ ] T-10 — GREEN: relocate freeform delivery-log prose out of the ledger
- Agent: build
- Files: `.ai-engineering/specs/_history.md:157-`, new `.ai-engineering/state/archive/delivery-logs/`
- Principles applied: §10.4 DRY (ledger is an index, not a log dump)
- Patch (deterministic): none — move the post-table prose blocks (spec-105/106/107/115-119 retros) into `state/archive/delivery-logs/spec-<NNN>.md`; grep the repo for references to those blocks and update before moving (precedent: spec-122-a, `_history.md:363`). `_split_history` preserves the tail until it is relocated.
- Gate: `_history.md` ends at the table; relocated files exist; no dangling references; before/after row count unchanged.

**Wave 2 gate:** `pytest tests/unit/specs/test_spec_lifecycle.py` green; ledger all-numeric; zero slug sidecars.

---

## Wave 3 — Archival + reaper [D-153-04 / D-153-06 / D-153-07] (dep: W1, W2)

- [ ] T-11 — RED: snapshot-on-ship + reset + reaper + root invariant
- Agent: build
- Files: `tests/unit/specs/test_spec_lifecycle.py`
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert: `mark_shipped` copies `spec.md`+`plan.md` into `archive/spec-NNN-<slug>/` and overwrites both working buffers with the placeholder; re-running is a no-op; `sweep` with `reap_orphans` moves a stray `specs/spec-999-x.md` into archive and leaves `{spec.md,plan.md,_history.md}` untouched.
- Gate: tests fail (RED) — `archive()` only flips state today (`spec_lifecycle.py:401-409`).

- [ ] T-12 — GREEN: snapshot + working-buffer reset at SHIPPED
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py:352-398`
- Principles applied: §10.1 KISS, §10.8 Hexagonal
- Patch (deterministic): none — add `_snapshot_and_reset(project_root, record)`: `mkdir archive/spec-NNN-<slug>/`, copy current `specs/spec.md`+`plan.md` in, then `_atomic_write` both buffers to the placeholder. Call it from `mark_shipped` after the SHIPPED write. ARCHIVED stays a no-file-move terminal marker (D-153-04). Placeholder content: `# (no active spec)\n\nRun /ai-brainstorm to start one.\n`.
- Gate: T-11 snapshot+reset assertions GREEN.

- [ ] T-13 — GREEN: orphan reaper folded into `sweep`, retention from manifest
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py:412-437`
- Principles applied: §10.4 DRY (retention via manifest, not constant)
- Patch (deterministic): none — read `draft_ttl_days`/`reap_orphans` from the manifest `lifecycle:` block (fail-open to 14/true); after the DRAFT→ABANDONED pass, when `reap_orphans`, move stray `specs/spec-*.md` (anything not in `{spec.md,plan.md,_history.md}` and not under `drafts/`/`archive/`) into its `archive/spec-NNN-<slug>/`, defaulting to move (never delete unless superseded). Extend the `spec_sweep` event detail with `reaped`.
- Gate: T-11 reaper assertion GREEN.

- [ ] T-14 — GREEN: migrate existing archive to the uniform per-spec-dir layout
- Agent: build
- Files: `.ai-engineering/specs/archive/**`
- Principles applied: §10.7 Clean Code (one layout)
- Patch (deterministic): none — `git mv` existing flat `spec-NNN-*.md` and `spec-NNN-plan.md` pairs into `archive/spec-NNN-<slug>/{spec.md,plan.md}`; normalize the already-bundled dirs (`spec-126-lock-parity/`, `spec-144-…/`) to the same shape.
- Gate: every entry under `archive/` is a `spec-NNN-<slug>/` directory; no flat files; no `-plan.md`.

- [ ] T-15 — GREEN: reap the 11 current `specs/` root orphans
- Agent: build
- Files: `.ai-engineering/specs/spec-129-*.md`, `spec-132-*`, `spec-144-*` (×4), `spec-146-*` (×2), `spec-148-*`, `spec-149-*`, `spec-150-*`
- Principles applied: §10.6 SDD
- Patch (deterministic): none — run the T-13 reaper (or one-shot `git mv`) to move each into its archive directory; delete only if confirmed superseded by an existing archive entry.
- Gate: `ls .ai-engineering/specs/` returns exactly `spec.md plan.md _history.md drafts archive`.

**Wave 3 gate:** `specs/` root invariant holds; archive uniform; `pytest tests/unit/specs/` green.

---

## Wave 4 — Merge wiring [D-153-03] (dep: W3)

- [ ] T-16 — RED: merged-branch backstop auto-marks SHIPPED
- Agent: build
- Files: `tests/integration/test_cli_command_modules.py:882`, `tests/unit/specs/test_spec_lifecycle.py`
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert: `reconcile_merged` finds an IN_PROGRESS/APPROVED sidecar whose `branch` is merged into the default branch and calls `mark_shipped` (idempotent); a sidecar with an unmerged branch is untouched.
- Gate: tests fail (RED) — no reconcile path exists.

- [ ] T-17 — GREEN: `reconcile_merged` verb
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py`
- Principles applied: §10.8 Hexagonal (git as adapter), §10.1 KISS
- Patch (deterministic): none — `reconcile_merged(project_root)`: for each non-terminal sidecar with a `branch`, check `git branch --merged <default>` / squash-merge emptiness (mirror `ai-branch-cleanup/SKILL.md:54-56` classification); if merged, resolve PR via `gh pr list --head <branch> --state merged` (fail-open to `—`) and call `mark_shipped`. Register the CLI subparser. Stays off the pre-push hot path (cleanup-time only).
- Gate: T-16 GREEN.

- [ ] T-18 — GREEN: wire reconcile into `/ai-branch-cleanup` + `ai-eng cleanup specs`
- Agent: build
- Files: `.claude/skills/ai-branch-cleanup/SKILL.md:88-91`, `src/ai_engineering/cli_commands/cleanup.py:366-380`
- Principles applied: §10.6 SDD
- Patch (deterministic): none — Phase 5 calls `reconcile_merged` BEFORE `consolidate_shipped` (so a merged-but-unshipped spec is marked, then its row appended); `cleanup_specs_cmd` runs `reconcile_merged` then `consolidate_shipped`. Fail-open preserved.
- Gate: `ai-eng cleanup specs --dry-run` lists merged-unshipped candidates.

- [ ] T-19 — GREEN: `/ai-pr` passes the numeric spec id at merge
- Agent: build
- Files: `.claude/skills/ai-pr/SKILL.md:67-70`
- Principles applied: §10.6 SDD
- Patch (deterministic): none — step 11 resolves the canonical `spec-NNN` from spec.md frontmatter (not the slug) and passes it to the shared `mark_shipped` handler; note the `/ai-branch-cleanup` reconcile as the backstop for non-`/ai-pr` merges.
- Gate: prose review; mirror parity in T-20.

- [ ] T-20 — GREEN: regenerate IDE mirrors for changed skills
- Agent: build
- Files: `.codex/`, `.agents/`, `.github/`, `src/ai_engineering/templates/project/**` (ai-pr, ai-branch-cleanup mirrors)
- Principles applied: §10.4 DRY (one canonical payload)
- Patch (deterministic): none — `ai-eng dev sync` after T-18/T-19 SKILL.md edits.
- Gate: `ai-eng dev sync --check` PASS.

**Wave 4 gate:** backstop test green; a test merge transitions to SHIPPED with zero manual commands.

---

## Wave 5 — Capability catalog generator [D-153-12 / D-153-15] (parallel with W1-4)

> No `description` field exists in the catalog models (`CapabilityDescriptor`,
> `SkillEntry`). Source descriptions from `.claude/skills/ai-*/SKILL.md` frontmatter
> at generation time. No marker-section precedent exists — establish it.

- [ ] T-21 — RED: generator emits catalog + drift gate fails on mismatch
- Agent: build
- Files: new `tests/unit/test_capability_catalog.py`
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert: the generator reads all 53 skill `description:` frontmatter + 9 agents and renders a markdown table between `<!-- catalog:start -->`/`<!-- catalog:end -->`; the drift check fails when the rendered count diverges from `len(DEFAULT_SKILLS_REGISTRY)` / agent count.
- Gate: tests fail (RED) — generator absent.

- [ ] T-22 — GREEN: `gen_capability_catalog.py` generator
- Agent: build
- Files: new `scripts/gen_capability_catalog.py`
- Principles applied: §10.8 Hexagonal (read-only adapter), §10.1 KISS
- Patch (deterministic): none — read `.claude/skills/ai-*/SKILL.md` frontmatter (`name`, `description`) + `.claude/agents/ai-*.md`; render a grouped markdown catalog; expose `render_section()` (returns the marker-delimited block) and `apply_to(path)` (idempotent in-place replacement between markers). Stdlib only.
- Gate: T-21 render assertions GREEN.

- [ ] T-23 — GREEN: wire generator into `dev sync` + install/update
- Agent: build
- Files: `src/ai_engineering/cli_commands/dev_sync.py:27-80`, `src/ai_engineering/installer/service.py:497`, `src/ai_engineering/installer/phases/state.py:83`
- Principles applied: §10.4 DRY (generated alongside framework-capabilities.json)
- Patch (deterministic): none — call `gen_capability_catalog.apply_to(.ai-engineering/README.md)` wherever `write_framework_capabilities` runs, and inside `dev_sync_cmd`.
- Gate: `ai-eng dev sync` rewrites the catalog section; re-run is a no-op diff.

- [ ] T-24 — GREEN: drift gate covers README counts
- Agent: build
- Files: `tools/skill_domain/validator_counter_accuracy.py:44`, `scripts/sync_mirrors/core.py`
- Principles applied: §10.5 TDD, §10.7 Clean Code
- Patch (deterministic): none — extend counter-accuracy `_instruction_files()` to parse the `N skills · M agents · K surfaces` pattern in both READMEs and the catalog marker block; `ai-eng dev sync --check` fails on catalog or count drift.
- Gate: a deliberately wrong count makes `dev sync --check` and `ai-eng validate` FAIL.

**Wave 5 gate:** `pytest tests/unit/test_capability_catalog.py` green; `dev sync --check` catches drift.

---

## Wave 6 — README content [D-153-11 / D-153-13 / D-153-14] (dep: W5)

- [ ] T-25 — GREEN: `.ai-engineering/README.md` → post-install client manual
- Agent: build
- Files: `.ai-engineering/README.md:1-95`, `src/ai_engineering/templates/project/.ai-engineering/README.md`
- Principles applied: §10.7 Clean Code, Diátaxis (tutorial + reference separation)
- Patch (deterministic): none — restructure to: welcome ("thanks for installing — here's what you can do") → quick-win path → the `<!-- catalog:start/end -->` generated section (53 skills / 9 agents with how-to) → a short maintainer pointer linking `docs/persistence-doctrine.md` + `CONSTITUTION.md`. DELETE the "Four-Tier Persistence" table and every `state/state.db` reference (`:34,:39-50,:61`) per D-153-14; align to three-tier doctrine.
- Gate: no `state.db`/"four-tier" string remains; catalog section present; `ai-eng doctor` governance-templates check PASS.

- [ ] T-26 — GREEN: root `README.md` de-drift counts
- Agent: build
- Files: `README.md:26,30`
- Principles applied: §10.4 DRY
- Patch (deterministic): none — wire the `53 skills · 9 agents · 6 surfaces` tagline (line 30) and banner alt text (line 26) to the T-24 drift gate (marker or generated values). Getting-started (`:34-52`) verified crystal-clear — left intact. Absolute `raw.githubusercontent` image URLs preserved.
- Gate: T-24 drift gate green against live counts.

- [ ] T-27 — GREEN: CHANGELOG entries for the hard migrations
- Agent: build
- Files: `CHANGELOG.md`
- Principles applied: Keep a Changelog; CONSTITUTION §3 (document breakage)
- Patch (deterministic): none — record: numeric spec-id rename, sidecar migration, archive layout change, orphan reap, delivery-log relocation, `.ai-engineering/README.md` rewrite + `state.db` reference removal, manifest `lifecycle:` block.
- Gate: CHANGELOG documents every operator-visible breakage.

- [ ] T-28 — VERIFY: final acceptance sweep
- Agent: verify
- Files: (read-only) `.ai-engineering/specs/`, both READMEs, `tests/`
- Principles applied: §10.6 SDD, §10.4 Goal-Driven Execution
- Patch (deterministic): none — read-only assertion of every spec Acceptance item: `specs/` root invariant, all-numeric ledger, archive uniform, catalog matches counts, no `state.db` refs, `ai-eng dev sync --check` green, full `pytest` green.
- Gate: all DoD/Acceptance checks pass; no blocker/critical/high findings.

**Wave 6 gate:** full quality loop green; spec-153 Acceptance checklist satisfied.

---

## Notes for the executor

- **Schema-first ordering is load-bearing** (Wave 1 before any manifest key) —
  `additionalProperties:false` at the schema root breaks `ai-eng validate` otherwise.
- **`mark_shipped` is the chokepoint** — Wave 3 adds the snapshot/reset; Wave 4 adds
  the auto-trigger. Both lean on its existing idempotency (`spec_lifecycle.py:355-366`),
  so re-runs stay safe.
- **Mirror parity**: any `.claude/skills/**` edit (T-18, T-19) requires `ai-eng dev
  sync` (T-20) and passes `dev sync --check`.
- **Open Questions** (defer to execution / operator): `draft_ttl_days` default (30);
  maintainer pointer vs separate `MAINTAINERS.md`; catalog inline vs linked include —
  the plan assumes inline-generated.
