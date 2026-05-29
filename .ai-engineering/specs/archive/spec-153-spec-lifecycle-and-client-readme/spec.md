---
spec: spec-153
title: Spec/Plan Lifecycle Automation and Client-Facing Capability READMEs
status: draft
effort: large
summary: "Close the spec/plan lifecycle loop (auto-archive + working-buffer reset on merge, enum-bound numeric ledger, orphan reaping) and align both READMEs to their audiences: GitHub landing and a generated post-install capability manual."
---

# Spec/Plan Lifecycle Automation and Client-Facing Capability READMEs

## Summary

The spec/plan lifecycle machinery is already built and structurally sound — a
six-state FSM, per-spec JSON sidecars, an `_history.md` ledger renderer, and
CLI verbs (`mark_shipped`, `archive`, `sweep`, `consolidate_shipped`) — but
**nothing fires it automatically**, two SSOT violations have crept in, and
working artifacts are never reaped. The most recent spec was recorded as
shipped by a manual maintenance commit (`fa2564b5`); `spec.md`/`plan.md`
linger after merge (this very spec overwrote a shipped spec-152 still sitting
in the working buffer); the `_history.md` Status column carries freeform
strings divorced from the state enum; eleven orphan `spec-NNN-*.md` files sit
loose in `specs/` root; the sidecars use two competing ID schemes. Separately,
the two README surfaces do not match their audiences: the root `README.md` is a
solid GitHub landing but hardcodes drift-prone capability counts, and
`.ai-engineering/README.md` is a maintainer reference carrying a factually
stale persistence claim (`state/state.db`, deleted by spec-148) rather than the
post-install operational manual an installed client needs to exploit the
framework. This spec closes the lifecycle loop, restores one canonical
identity and one ledger vocabulary, reaps orphans, and turns both READMEs into
their intended surfaces.

## Goals

- The lifecycle loop runs without manual steps: merging a spec PR auto-runs
  `mark_shipped`, snapshots `spec.md`+`plan.md` into an immutable archive
  directory, resets the working buffers to placeholders, and appends one ledger
  row — verifiable by a test merge producing all four effects with zero manual
  commands, idempotent on re-run.
- There is exactly one canonical spec identity (numeric `spec-NNN`); the
  ledger, sidecars, and archive paths all key on it; `start_new` mints the next
  number atomically.
- The `_history.md` Status column for every NEW row renders strictly from the
  six-value `LifecycleState` enum; historical rows remain verbatim; the single
  slug-keyed row is corrected to `spec-152`.
- `specs/` root contains only `spec.md`, `plan.md`, `_history.md`, `drafts/`,
  and `archive/`; the eleven current orphans are gone; sidecars are
  single-scheme and de-duplicated; `archive/` uses one uniform per-spec-directory
  layout.
- Retention windows (draft TTL, archive layout, orphan-reap toggle) are read
  from a `manifest.yml` `lifecycle:` block, not hardcoded.
- `.ai-engineering/README.md` is a simple, complete post-install client manual:
  a generated catalog of all 53 skills and 9 agents with how-to entries, no
  stale `state.db`/four-tier reference, aligned to the three-tier doctrine.
- The root `README.md` keeps its crystal-clear getting-started path and has its
  hardcoded `53 · 9 · 6` counts wired to the same drift gate as the manual
  catalog, so the numbers cannot silently rot.
- All capability catalogs are derived rebuildable caches (SSOT remains the
  skill/agent files); `ai-eng dev sync --check` fails on drift.

## Non-Goals

- Changing the `LifecycleState` state set or the legal-transition table — the
  six states are correct; the work is wiring and rendering, not re-modelling.
- Rewriting the root `README.md` from scratch — it is already a strong landing;
  scope is verify-getting-started + de-drift counts + minor polish only.
- The `decision-store.json` backfill mechanics (`ai-eng decision backfill`) —
  decisions reference `spec_id` but their lifecycle is a separate concern.
- The `runtime_rotate.py` rotation policy itself — already working; referenced
  only as the retention-model precedent.
- Memory/Engram persistence, evals, or any non-spec state plane.
- Lossy rewriting of the 152 historical ledger rows (explicitly preserved as
  immutable records).

## Decisions

- **D-153-01 — Numeric `spec-NNN` is the one canonical spec identity; slug is a
  secondary descriptor.**
  **Rationale**: the `D-NNN-NN` decision-ID convention,
  branch names (`spec-152-…`), `CHANGELOG`, and 152 of 153 `_history` rows
  already key numeric; choosing numeric aligns the majority surface and
  preserves the decision-ID scheme. Slug remains the human-readable tag in
  archive directory names and the `slug:` frontmatter field.
- **D-153-02 — Freeze historical `_history.md` rows; bind only NEW rows to the
  enum; correct the one slug-keyed row to `spec-152`.**
  **Rationale**: the brief's
  own governing precedents (PEP 1, ADRs) treat published records as immutable;
  remapping freeform strings (`partial`, `runtime-landed-docs-deferred`) onto
  six enum values is lossy. New rows render from the sidecar `LifecycleState`;
  the table carries mixed vocabulary only during the transition tail.
- **D-153-03 — Merge wiring is `/ai-pr` mark (primary) + `/ai-branch-cleanup`
  idempotent reconcile (backstop).**
  **Rationale**: `/ai-pr` holds the PR number
  and branch at merge time and can mark immediately; `/ai-branch-cleanup`
  detects merged-but-unmarked specs and auto-marks as the idempotent safety net
  that also catches manual GitHub merges. Both run off the pre-push hot path
  (CLAUDE.md budget). A native git `post-merge` hook is rejected (wrong layer,
  no PR context, fires on every pull).
- **D-153-04 — Snapshot `spec.md`+`plan.md` into `archive/spec-NNN-<slug>/` and
  reset the working buffers to placeholders at the SHIPPED transition; ARCHIVED
  remains a logical terminal marker with no additional file movement.**
  **Rationale**: clearing at merge directly eliminates the lingering-buffer pain;
  keeping ARCHIVED as a bookkeeping-only terminal honors the Non-Goal of not
  changing the FSM.
- **D-153-05 — `start_new` mints the next `spec-NNN` from the max of the ledger
  + sidecars, written atomically under the existing `specs-history` lock.**
  **Rationale**: a numeric canonical ID requires a central counter; the lock and
  tempfile+`os.replace` pattern already exist in `spec_lifecycle.py`. Collision
  risk in parallel work is low and serialized by the lock.
- **D-153-06 — One uniform archive layout: `archive/spec-NNN-<slug>/{spec.md,
  plan.md}`; migrate existing flat files and `-plan.md` pairs into it.**
  **Rationale**: the current mix of flat files, separate plan files, and bundled
  directories is the inconsistency the spec exists to remove.
- **D-153-07 — An orphan reaper folds into the existing `sweep`; the `specs/`
  root invariant is `{spec.md, plan.md, _history.md, drafts/, archive/}`.**
  **Rationale**: a single enforced invariant is the simplest durable guard against
  re-accumulation. The reaper moves stray files to their archive directory by
  default and deletes only on confirmed supersession.
- **D-153-08 — A `manifest.yml` `lifecycle:` block (e.g. `draft_ttl_days`
  default 30, `archive_layout`, `reap_orphans`) replaces the hardcoded 14-day
  sweep cutoff.**
  **Rationale**: SSOT-PD — retention is config and belongs in the
  one config store, not in source constants.
- **D-153-09 — Freeform delivery-log prose moves out of `_history.md` to
  `state/archive/delivery-logs/`.**
  **Rationale**: the ledger is an index over
  shipped specs, not a log dump; the spec-122-a relocation of
  `spec-117-progress` is the established precedent.
- **D-153-10 — Sidecars are renamed slug→`spec-NNN.json` and de-duplicated
  (the `obvious-by-default` / `obvious-by-default-essentials` pair).**
  **Rationale**: one identity scheme (D-153-01) implies one sidecar naming scheme.
- **D-153-11 — `.ai-engineering/README.md` becomes the post-install client
  manual: a generated catalog of the 53 skills + 9 agents with concise how-to
  entries; maintainer plumbing (ownership boundaries, persistence tiers, sync
  contract) is trimmed to a short pointer linking `docs/persistence-doctrine.md`
  and `CONSTITUTION.md`.**
  **Rationale**: the operator's intent is a quick, complete
  reference an installed client uses to exploit the framework — not internal
  governance mechanics.
- **D-153-12 — Both README capability catalogs are derived rebuildable caches
  generated from `framework-capabilities.json` / skill descriptions,
  regenerated on `ai-eng install`/`update`/`dev sync`, and drift-gated by
  `dev sync --check`.**
  **Rationale**: SSOT-PD — the skill/agent files are the
  source; no count or description is hand-maintained in a README.
- **D-153-13 — Root `README.md` scope is bounded to: verify the getting-started
  path is crystal-clear (it is) and wire the hardcoded `53 · 9 · 6` counts
  (banner alt text + tagline) to the D-153-12 drift gate; no full rewrite.**
  **Rationale**: the landing already satisfies the operator's GitHub-visitor
  requirements; the only rot risk is the static counts.
- **D-153-14 — Delete the stale "Four-Tier Persistence" table and every
  `state/state.db` reference in `.ai-engineering/README.md`; align to the
  three-tier doctrine.**
  **Rationale**: `state.db` was deleted by spec-148; the
  claim is factually wrong today. Hard delete, no deprecation shim
  (CONSTITUTION §3).
- **D-153-15 — The README catalog is generated by a script that reads the skill
  and agent files as source, invoked by `ai-eng dev sync`.**
  **Rationale**: the
  generation path itself must be a single tool so both READMEs and any future
  surface stay byte-consistent; mirrors the existing `sync_mirrors` model.

## Risks

- **Auto-`mark_shipped` fires on the wrong branch or double-fires.** Likelihood
  medium, impact medium. Mitigation: `consolidate_shipped` is already
  idempotent (checks known IDs before appending); guard the `/ai-pr` mark on a
  confirmed-merged PR + branch match; the M2 gate runs a dry-run first.
- **Numeric counter collision in parallel spec work.** Likelihood low, impact
  medium. Mitigation: minting is serialized under the existing `specs-history`
  lock and reads the live max at mint time; sequential spec cadence makes
  contention rare.
- **`_history.md` migration drops the freeform delivery-log tail.** Likelihood
  low, impact high. Mitigation: the existing `_split_history()` already
  preserves the tail; the prose is relocated, not deleted, with references
  grepped and updated first; a before/after row-count test guards it.
- **Identity-scheme rename breaks references in skills, tests, or docs.**
  Likelihood medium, impact high. Mitigation: grep all `spec-NNN` and slug
  references before renaming; update them in the same commit; the CI
  cross-reference and mirror validators catch stragglers.
- **README capability catalog drifts from the live skill/agent set.**
  Likelihood medium, impact low. Mitigation: the catalog is a derived cache
  regenerated on install/update/sync and gated by `dev sync --check`.
- **The orphan reaper deletes a still-load-bearing file.** Likelihood low,
  impact high. Mitigation: the reaper moves to archive by default and deletes
  only on confirmed supersession; a dry-run lists targets before any action.
- **"Both READMEs" scope balloons the spec.** Likelihood medium, impact medium.
  Mitigation: root README is bounded to verify + de-drift (D-153-13), not a
  rewrite; the heavy work stays on concerns A and B.

## References

- doc: .ai-engineering/specs/drafts/spec-lifecycle-and-client-readme-brief.md
- doc: docs/persistence-doctrine.md
- doc: https://peps.python.org/pep-0001/
- doc: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
- doc: https://adr.github.io/madr/
- doc: https://keepachangelog.com/en/1.1.0/
- doc: https://diataxis.fr/

## Open Questions

- Exact `draft_ttl_days` default — provisionally 30; confirm at `/ai-plan`.
- Whether trimmed maintainer plumbing in `.ai-engineering/README.md` becomes a
  short in-file pointer (current D-153-11 default) or a dedicated
  `MAINTAINERS.md` — defaulted to pointer; revisit if the pointer proves too
  thin.
- Whether the generated catalog lives inline in the README or in a generated
  include the README links — defaulted to inline-generated section; confirm at
  `/ai-plan`.
