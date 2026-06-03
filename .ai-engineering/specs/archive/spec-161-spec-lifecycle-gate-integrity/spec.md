---
spec: spec-161
slug: spec-lifecycle-gate-integrity
title: "Spec-lifecycle approval gate + integrity hardening"
status: approved
effort: medium
branch: null
date_approved: 2026-06-03
target_dispatch: /ai-autopilot
mantra: "One canonical state store. The gate reads the source of truth. Numbering and reconcile never lie about what is merged."
summary: >
  Close the spec-lifecycle approval-gate gap and three integrity defects in one
  subsystem pass. Mint an approve verb (DRAFT to APPROVED, the FSM already
  permits it) that writes the canonical sidecar and mirrors the status field
  into spec.md frontmatter; wire /ai-brainstorm Step 9 to call it; add a hard
  /ai-plan gate that blocks on a non-approved spec by reading the canonical
  sidecar state. Fix the archive-blind next-number scan so start_new never
  re-mints a number already taken by an archive directory; make reconcile
  classify merge state via gh PR state so a squash-merged spec whose local
  branch was pruned is still consolidated. Add a start verb wired into
  /ai-build, and reconcile the installer spec ledger-id (158) vs
  archive-dir-id (159) data mismatch. Closes issues 550, 551, and 574.
---

# spec-161 — Spec-lifecycle approval gate + integrity hardening

## Summary

The spec-lifecycle subsystem (`.ai-engineering/scripts/spec_lifecycle.py` plus
the `/ai-brainstorm`, `/ai-plan`, `/ai-build`, `/ai-branch-cleanup` skills) has
a missing approval gate and three integrity defects, all verified against the
live `0.10.1` code. Three upstream issues report them:

- **#550** — `spec_lifecycle.py` exposes no `approve` command. The FSM already
  declares `DRAFT → {APPROVED, ABANDONED}` as a legal transition
  (`spec_lifecycle.py:84-91`), but no CLI verb reaches `APPROVED`. Nothing in
  the canonical chain ever transitions a spec out of `draft`.
- **#551** — `/ai-plan` claims to operate on "an approved spec" but never reads
  the `state`/`status` field and never blocks. A spec stuck in `draft`
  decomposes into a plan unchallenged. The gate the docs promise does not exist.
- **#574 Bug 1** — `_scan_spec_numbers` (`spec_lifecycle.py:779`) computes the
  next spec number from live sidecars + the `_history.md` ledger but ignores
  `.ai-engineering/specs/archive/spec-NNN-*/` directory names. A number whose
  only surviving trace is its archive dir can be silently re-minted (the
  spec-159 collision that forced a manual bump to spec-160).
- **#574 Bug 2** — `reconcile_merged` classifies merge state with local git
  refs (`git branch --merged`, `git rev-list`). In `ai-eng cleanup all` the
  branch-prune phase runs before the specs phase, so a squash-merged spec's
  local branch is already gone → reconcile reports it "unmerged" → consolidation
  is skipped. A GitHub-UI-merged spec never gets its `_history.md` row.

These are one coherent subsystem pass. #550 and #551 are a single mechanism:
without an `approve` verb nothing reaches `approved`, so the #551 gate could
never pass. #574's two bugs share the `spec_lifecycle.py` numbering/reconcile
surface. Shipping them together avoids four separate touches of the same file
and the same four skills.

### Current-state evidence

| Concern | File:line | Verified state |
|---|---|---|
| `approve` verb | `spec_lifecycle.py` subparsers (L1365-1402) | Absent. `APPROVED` enum + `DRAFT→APPROVED` transition already exist (L76, L85). |
| Plan gate | `.claude/skills/ai-plan/SKILL.md` | No `state:`/`status:` read, no block. |
| Brainstorm approval wiring | `.claude/skills/ai-brainstorm/SKILL.md:60` | Step 9 STOPs; never calls a lifecycle approve. |
| Archive-blind numbering | `spec_lifecycle.py:779-815` | Scans sidecars + ledger only; `_ARCHIVE_DIR_RE` (L1101) already parses `spec-NNN-<slug>` but is used only by `migrate_ids`. |
| Reconcile merge classify | `spec_lifecycle.py:915-978`, `cli_commands/cleanup.py:366-393` | `_branch_is_merged` needs a live local ref; `_resolve_merged_pr` (L981) already queries `gh` by head branch (survives prune). |
| State stores | `state/specs/<slug>.json` `state` + `spec.md` frontmatter `status` | Two writable stores, different vocab (`in_progress`/`shipped` vs `in-progress`/`done`). Doctrine names the sidecar canonical (`docs/persistence-doctrine.md:66-71`). |

## Goals

1. **Approve verb (#550).** `spec_lifecycle.py approve <spec_id>` transitions
   the canonical sidecar `DRAFT → APPROVED`, emits a `spec_approved` framework
   event, mirrors `status: approved` into `spec.md` frontmatter, and exits `0`.
   Idempotent: re-approving an already-APPROVED record is a no-op `0`. Illegal
   source states (SHIPPED/ARCHIVED/ABANDONED) raise via the existing FSM
   validator.
2. **Brainstorm wiring (#550 + Q4).** `/ai-brainstorm` Step 9 calls `approve`
   at the existing explicit operator-approval gate so specs reach `approved`
   organically in the canonical chain. Fail-open: a non-zero `approve` logs and
   does not block the STOP.
3. **Plan gate (#551).** `/ai-plan` reads the **canonical sidecar** lifecycle
   state for the active spec and HARD-BLOCKS (no `plan.md` written, non-zero
   exit, the issue's exact error text) when state is a known non-approved value.
   Fail-open (loud warning + proceed) only when state is genuinely
   indeterminable (no sidecar AND no frontmatter `status`).
4. **Archive-blind numbering (#574 Bug 1).** `_scan_spec_numbers` additionally
   parses `archive/spec-(\d+)-*` directory names so `_next_spec_number` never
   re-mints an archived number. Reuse the existing `_ARCHIVE_DIR_RE` /
   `_archive_dir` helpers.
5. **Reconcile via gh (#574 Bug 2).** `reconcile_merged` classifies merge state
   via `gh pr list --head <branch> --state merged` (ordering-independent,
   survives branch prune), falling back to the existing local-ref check when
   `gh` is absent. A UI-merged, locally-pruned spec consolidates correctly.
6. **Start verb (Q4).** `spec_lifecycle.py start <spec_id>` transitions
   `APPROVED → IN_PROGRESS` (FSM already legal), mirrors `status: in-progress`
   into frontmatter; `/ai-build` Step 1 calls it (fail-open).
7. **Installer id reconciliation (#574 Bug 1b).** One-time data fix: align the
   installer spec's `_history.md` ledger id (spec-158) with its archive
   dir/branch/PR id (spec-159-installer-parity). No code path depends on the
   choice; pick the id its archive dir/branch/PR already carry and correct the
   single divergent surface, documented in CHANGELOG.
8. **Tests.** RED-first coverage for every verb and gate in
   `tests/unit/specs/test_spec_lifecycle.py` (+ the plan/brainstorm/build skill
   gate behaviors where unit-testable) and the cleanup reconcile path.

## Non-Goals

- **No second state store and no inversion of the canonical store.** The sidecar
  JSON stays the SoT (doctrine). Frontmatter `status:` stays a derived mirror.
  We do not move lifecycle state into `spec.md`.
- **No new `state.db` / SQLite revival.** Files-only, per persistence-doctrine.
- **No `--force` / escape-hatch flag on the `/ai-plan` gate.** The only bypass
  is approving the spec (the intended path). Indeterminable-state fail-open is
  not an operator-facing override.
- **No backfill of historical drafts to `approved`.** Existing `draft` sidecars
  stay as-is; only the forward path changes.
- **No reordering of the `cleanup all` composite phases.** Q3 chose the
  localized gh-classification fix; composite resequencing is explicitly out.
- **No board/work-item state changes** beyond the existing `/ai-board sync`
  calls already wired into the skills.
- **No change to `mark_shipped`'s force-walk semantics.** It keeps advancing
  from any non-terminal state to SHIPPED.

## Decisions

### D-161-01 — Sidecar JSON is the canonical lifecycle-state store

Frontmatter `status:` is its mirror. `approve` and `start` write the sidecar
first (atomic, under `artifact_lock`), then best-effort mirror the frontmatter;
the `/ai-plan` gate reads the sidecar. (Q1.)
**Rationale**: `docs/persistence-doctrine.md:66-71` already names the per-spec
sidecar the canonical source-of-truth for lifecycle state; making frontmatter
canonical would contradict the doctrine and re-create the Hard-Rule-#7
dual-writable-store violation.

### D-161-02 — State-to-status vocabulary mapping

Canonical sidecar `state` maps to frontmatter `status`: draft to draft, approved
to approved, in_progress to in-progress, shipped to done. The mirror writer
applies this table; the gate compares on the canonical `state` value (approved).
**Rationale**: the two stores use different vocabularies (the schema frontmatter
enum vs the FSM enum), so a fixed table is required to keep the human mirror
faithful without leaking FSM identifiers into spec docs.

### D-161-03 — `/ai-plan` gate is fail-loud on a known non-approved state

Fail-open only on indeterminate plumbing. Resolution order: (a) sidecar SoT for
the active spec (resolve id via `spec.md` frontmatter `spec:` then `slug:`);
(b) if no sidecar, frontmatter `status:`; (c) if neither resolves, emit a loud
warning and proceed. A resolved non-approved state blocks with the issue-551
error text and writes no `plan.md`. (Q2.)
**Rationale**: blocking the real defect (a draft spec) closes issue 551, while
fail-open-on-indeterminate honors the framework's fail-open-on-plumbing
philosophy and avoids a new permanent-lockout class.

### D-161-04 — `reconcile_merged` gains a gh PR-state classifier

The gh check is the primary merge signal; the local-ref check is the fail-open
fallback. `gh pr list --head <branch> --state merged` returning one or more rows
means merged; `gh` absent or erroring falls back to `_branch_is_merged`. The
existing `_history.md` idempotency guard is unchanged (no double-ship). (Q3.)
**Rationale**: the prune-before-reconcile ordering lives in the `cleanup all`
composite, and gh PR state survives a pruned local branch, so a localized
gh-aware classifier fixes the root cause without awkward composite resequencing.

### D-161-05 — `_scan_spec_numbers` includes `archive/spec-NNN-*` dir numbers

Reuse `_ARCHIVE_DIR_RE` and `_archive_dir`; union the archive numbers into the
existing sidecar+ledger set before `max()`. (Bug 1.)
**Rationale**: an archived spec whose only surviving trace is its archive
directory must still anchor the next number, or `start_new` silently re-mints a
taken id (the spec-159 collision).

### D-161-06 — `approve` and `start` are idempotent and FSM-guarded

Re-issuing the target verb on a record already in the target state is a no-op
exit 0; illegal source states raise via `transition()`.
**Rationale**: matches the established idempotency contract of the other
lifecycle verbs and keeps the pure FSM the single gate for legal moves.

### D-161-07 — Installer id reconciliation adopts the dir/branch/PR id

The archive dir, git branch, and PR all say `spec-159-installer-parity`; the
lone `_history.md` row says spec-158. Correct the ledger row to spec-159.
**Rationale**: three durable artifacts already carry 159, so correcting the
single divergent ledger cell is the least-churn way to restore one id per spec.

### D-161-08 — `/ai-brainstorm` and `/ai-build` lifecycle calls are fail-open

A non-zero `approve`/`start` logs and never blocks the user-facing flow.
**Rationale**: consistent with the brainstorm Step 0 bootstrap; the HARD gate is
`/ai-plan` reading the resulting state, not the write succeeding, so lifecycle
plumbing can never wedge the chain.

## Risks

- **R-161-01 — Active-spec resolution ambiguity.** Sidecars are keyed by slug
  (new) or `spec-NNN` (migrated). The gate must resolve `spec.md` → the right
  sidecar. *Mitigation*: try frontmatter `spec:` id, then `slug:`; the existing
  `_spec_frontmatter_id` (L1129) already reads `spec:`. Indeterminate ⇒ D-161-03
  fail-open (no false lockout).
- **R-161-02 — Gate fail-open re-opening #551.** If fail-open triggers whenever a
  sidecar is missing, a missing-sidecar path could bypass the gate. *Mitigation*:
  fail-open requires BOTH sidecar AND frontmatter `status` to be absent — the
  #551 scenario (sidecar present, state=draft) always blocks.
- **R-161-03 — `gh` unavailable or unauthenticated in CI.** gh-classification
  returns no rows → falls back to the local-ref check → if the branch is also
  pruned, the spec is reported unmerged (status quo, not a regression).
  *Mitigation*: documented fail-open; consolidation remains idempotent on the
  next run once refs/gh recover.
- **R-161-04 — Frontmatter mirror drift.** If the sidecar write succeeds but the
  frontmatter mirror fails, the human-facing `status:` lags the SoT.
  *Mitigation*: SoT is authoritative; the gate reads the sidecar, so drift never
  changes gate behavior; mirror write is logged on failure.
- **R-161-05 — Hooks-manifest / mirror-parity churn.** Editing the four skills +
  `spec_lifecycle.py` touches canonical surfaces that have byte-parity mirrors
  and (for hooks-adjacent scripts) integrity manifests. *Mitigation*: run
  `ai-eng dev sync` + regenerate any affected manifest; CI parity tests gate it.
- **R-161-06 — `approve` mutating `spec.md` during an active session.** Writing
  frontmatter mid-brainstorm could race the skill's own writes. *Mitigation*:
  `approve` runs at Step 9 (post-draft, pre-STOP) when no other writer is active;
  sidecar write is under `artifact_lock`.
- **R-161-07 — Installer id reconciliation hits a frozen-ledger invariant.**
  `_history.md` rows are described as "frozen records." *Mitigation*: treat the
  spec-158→spec-159 correction as a one-time documented data fix in CHANGELOG,
  not a routine mutation; verify no test pins the spec-158 row text.
