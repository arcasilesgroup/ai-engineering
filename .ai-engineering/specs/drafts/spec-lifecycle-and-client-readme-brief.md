---
title: Spec/Plan Lifecycle Automation and Client-Facing Capability README
status: draft
audience: framework-dev
branch: spec-lifecycle-and-client-readme
length_estimate: large
authoring_style: diagnostic-brief
principles_required:
  - "§10.1 KISS"
  - "§10.4 DRY"
  - "§10.6 SDD"
  - "§10.7 Clean Code"
  - "SSOT-PD (Single Source of Truth Per Datum)"
delivery_mode: autopilot
mantra: "Supersede, don't delete. One ledger, one truth. Greet the client."
---

# Spec/Plan Lifecycle Automation and Client-Facing Capability README

> Combined brief covering two related organization-hygiene concerns inside
> `.ai-engineering/`: (A) the spec/plan lifecycle is structurally sound but
> not wired to fire, so artifacts accumulate and the ledger drifts; (B) the
> installed-shape README is a maintainer reference with stale facts, not the
> client welcome it should be. Both are "where does information live, who is
> it for, how is it maintained" problems.

## 1. Vision

A user finishing a spec leaves the workspace exactly as clean as they found
it: the working buffers (`spec.md`, `plan.md`) reset to placeholders, an
immutable snapshot lands in a predictable archive location, and a single
ledger row appears automatically — no manual `mark_shipped` commit, no orphan
files, no freeform status strings. The lifecycle becomes a closed loop that
runs itself on PR merge, modelled on the proven "supersede, don't delete"
discipline of Python PEPs, Rust RFCs, and Architecture Decision Records.

In parallel, anyone who installs `ai-engineering` opens
`.ai-engineering/README.md` and gets a client welcome: "thanks for installing
— here is everything you can do," a quick-win path, and an auto-generated
catalog of all 53 skills and 9 agents — not a four-tier persistence table that
references a database file deleted three specs ago.

The end state: the lifecycle mechanism that already exists
(`.ai-engineering/scripts/spec_lifecycle.py:72-89`) is fully wired,
self-cleaning, and SSOT-correct; the README is regenerated from the same
capability source the rest of the framework already trusts.

## 2. Scope Boundary

**In scope:**

- Auto-wiring lifecycle transitions (`mark_shipped`, archival, working-buffer
  reset) to PR-merge and cleanup events so the loop runs without manual steps.
- Binding the `_history.md` Status column to the canonical `LifecycleState`
  enum and normalizing the 152 existing freeform rows.
- A single canonical spec identity (resolve `spec-NNN` vs slug) propagated to
  the ledger, sidecars, and archive paths.
- Standardizing the `archive/` layout (one immutable per-spec directory) and
  sweeping the 11 orphan files in `specs/` root plus stale `drafts/`.
- Surfacing the hardcoded retention windows as `manifest.yml` knobs.
- Rewriting `.ai-engineering/README.md` as a client-facing welcome with an
  auto-generated capability catalog, and fixing the stale four-tier /
  `state.db` references.

**Explicitly NOT in scope:**

- The `decision-store.json` backfill mechanics (`ai-eng decision backfill`) —
  decisions reference `spec_id` but their lifecycle is a separate concern.
- The runtime rotation policy itself (`runtime_rotate.py`) — already working;
  only referenced as the precedent retention model.
- The root `README.md` (GitHub landing) — this brief touches only
  `.ai-engineering/README.md` (the post-install client surface).
- Changing the FSM state set or the legal-transition table — the six states
  are correct; the gap is wiring and rendering, not the model.
- Memory/Engram persistence, evals, or any non-spec state plane.

## 3. Diagnostic Snapshot

The lifecycle machinery is **already built and mostly correct** — the failure
is that nothing fires it automatically, two SSOT violations have crept in, and
working artifacts are never reaped. Three decay surfaces, all evidenced below.

**Decay surface 1 — the loop does not run itself.** A spec only advances to
`shipped` when `mark_shipped` is explicitly invoked
(`.ai-engineering/scripts/spec_lifecycle.py:380-398`). Nothing triggers it on
PR merge: the most recent shipped spec was recorded by a *manual* maintenance
commit (`fa2564b5` — "record shipped lifecycle state after PR #536 merge").
`consolidate_shipped` exists precisely to repair this gap
(`.ai-engineering/scripts/spec_lifecycle.py:517`) but must itself be invoked
via `/ai-branch-cleanup --specs` or `ai-eng cleanup specs`
(`src/ai_engineering/cli_commands/cleanup.py:366-401`). The `archive` verb
flips the sidecar JSON state to `ARCHIVED` but **never moves or snapshots the
markdown** (`.ai-engineering/scripts/spec_lifecycle.py:401-409`), so the
`archive/` directory is populated entirely by hand.

**Decay surface 2 — the ledger drifts from the model (SSOT violation).** The
canonical state set is a six-value enum
(`.ai-engineering/scripts/spec_lifecycle.py:72-78`:
`draft / approved / in_progress / shipped / abandoned / archived`). But the
`_history.md` Status column carries **freeform strings that do not exist in
the enum**: `implemented`, `done`, `partial`, `approved`, `draft-deferred`,
`draft-pending-review`, `runtime-landed-docs-deferred`, `abandoned`, `draft`
(`.ai-engineering/specs/_history.md:7-153`). The Shipped column is empty for
most rows even where Status reads `implemented`
(`.ai-engineering/specs/_history.md:7-9`). The ID scheme is inconsistent: 152
rows use numeric IDs (`001`–`146`) but the single newest row is keyed by slug
`github-actions-supply-chain-hardening`
(`.ai-engineering/specs/_history.md:153`) while its own `spec.md` frontmatter
declares `spec: spec-152` (`.ai-engineering/specs/spec.md:1-8`). The ledger ID
no longer equals the spec identity.

**Decay surface 3 — working artifacts are never reaped.** `specs/` root holds
**11 orphan `spec-NNN-*.md` files** that should not be there (`spec-129-…`,
`spec-132-…`, four `spec-144-*`, two `spec-146-*`, `spec-148-…`,
`spec-149-…`, `spec-150-…`) — `/ai-brainstorm` and `/ai-plan` overwrite the
single `spec.md` / `plan.md` (`.claude/skills/ai-brainstorm/SKILL.md:57`,
`.claude/skills/ai-plan/SKILL.md:33`), so these are stale leftovers nothing
clears. `drafts/` has accumulated **23 brief files** with no consumption or
TTL policy. The `state/specs/` sidecars (17) mix two ID schemes — slug-based
(`cli-ux-overhaul.json`) and numeric (`spec-131.json`) — and contain
near-duplicates (`obvious-by-default.json` and
`obvious-by-default-essentials.json`). `archive/` itself is internally
inconsistent: flat files (`spec-128-context-overrides.md`), separate plan
files (`spec-128-plan.md`), and bundled directories (`spec-126-lock-parity/`)
coexist. Only the explicit `--consolidate-spec <slug>` handler ever clears
`spec.md` / `plan.md` to placeholders; the 14-day sweep only ages DRAFTs to
ABANDONED (`.ai-engineering/scripts/spec_lifecycle.py:412-437`, cutoff at
line 419). No retention window is configurable — there are **no lifecycle
keys in the manifest** (`.ai-engineering/manifest.yml` carries brainstorm-gate
config at lines 163-178 but no `lifecycle`/retention block).

**Concern B — the README is a stale maintainer doc, not a client welcome.**
`.ai-engineering/README.md` opens with "Local governance root for a {ai}
engineering workspace" (`.ai-engineering/README.md:1-5`) — addressed to the
operator, not the newly-installed client. It contains a **factually wrong**
"Four-Tier Persistence" section citing `state/state.db` as the Tier-2
canonical store (`.ai-engineering/README.md:39-50`, repeated at line 61 and
line 34), but `state.db` was deleted by spec-148 and the doctrine is now
three-tier (`docs/persistence-doctrine.md:8-20`). There is **no human-readable
catalog** of the 53 skills / 9 agents anywhere a client could read it; the
only enumeration is the machine-readable `framework-capabilities.json`, built
by `write_framework_capabilities()`
(`src/ai_engineering/state/observability.py:1024-1039`) and gitignored.

## 4. Architecture

The change splits cleanly into two concerns sharing one principle —
**SSOT-PD: every datum has exactly one canonical writable store, every other
copy is a labelled rebuildable cache** (`docs/persistence-doctrine.md:8-20`).

### Concern A — Spec/Plan lifecycle automation

```
                       PR merged (gh / git post-merge)
                                  │
                                  ▼
   ┌──────────────────── lifecycle orchestrator ────────────────────┐
   │  spec_lifecycle.py  mark_shipped(spec_id, pr, branch)            │
   │   1. FSM walk  DRAFT→APPROVED→IN_PROGRESS→SHIPPED  (idempotent)  │
   │   2. snapshot  spec.md + plan.md ──► archive/spec-NNN-<slug>/    │  ← NEW: markdown move
   │   3. reset     spec.md, plan.md ──► placeholders                 │  ← NEW: auto-clear
   │   4. append    _history.md row  (Status rendered FROM enum)      │  ← FIX: enum-bound
   │   5. emit      framework_operation/spec_shipped (NDJSON)         │
   └─────────────────────────────────────────────────────────────────┘
                                  │
        /ai-branch-cleanup --specs│  consolidate_shipped() = idempotent safety net
                                  ▼
        sweep: DRAFT→ABANDONED (manifest-tunable TTL) ; orphan reaper
```

**A1. One canonical spec identity.** Pick `spec-NNN` as the primary key (the
`spec.md` frontmatter already declares it). `slug` is secondary metadata. The
ledger, sidecar filenames (`state/specs/spec-NNN.json`), and archive paths
(`archive/spec-NNN-<slug>/`) all key on `spec-NNN`. Hard-rename the existing
slug-based sidecars; de-duplicate the `obvious-by-default*` pair. (Open
decision §9 — numeric vs slug primary.)

**A2. Enum-bound ledger.** `_render_history()` renders the Status column
strictly from the sidecar's `LifecycleState`
(`.ai-engineering/scripts/spec_lifecycle.py:72-78`). A one-shot migration maps
the legacy freeform strings (`done`/`implemented`/`partial` → `shipped`;
`draft-deferred`/`draft-pending-review` → `draft`; etc.) — precedent exists in
the existing `migrate_history()` 5/6→7-column migration
(`.ai-engineering/scripts/spec_lifecycle.py:447`). The freeform delivery-log
prose currently appended below the table
(`.ai-engineering/specs/_history.md:157+`) moves to per-spec archive or to
`state/archive/delivery-logs/` (precedent: spec-122-a relocated
spec-117-progress there — `.ai-engineering/specs/_history.md:363`).

**A3. Auto-wire transitions to events.** `mark_shipped` fires automatically
from the `/ai-pr` post-merge step (the wiring exists in the template but is
not firing on this repo); `consolidate_shipped` runs as the idempotent safety
net inside `/ai-branch-cleanup` (`.claude/skills/ai-branch-cleanup/SKILL.md:90`).
Idempotency is already the design (`consolidate_shipped` checks known IDs
before appending), so a double-fire is a no-op.

**A4. Immutable archival + auto-reset.** Extend the `archive` verb (today only
flips JSON — `.ai-engineering/scripts/spec_lifecycle.py:401-409`) to snapshot
`spec.md` + `plan.md` into a **single per-spec directory**
`archive/spec-NNN-<slug>/{spec.md,plan.md}` (kills the flat-file vs dir vs
`-plan.md` inconsistency), then reset the working buffers to placeholders.
This is the "where does the spec/plan summary live" answer: the frozen archive
copy IS the summary; `_history.md` is the index over it.

**A5. Orphan reaper + drafts TTL.** Define the invariant: `specs/` root holds
ONLY `spec.md`, `plan.md`, `_history.md`, and the `drafts/` + `archive/`
subdirs. A reaper (folded into the existing sweep at
`.ai-engineering/scripts/spec_lifecycle.py:412-437`) moves stray
`spec-NNN-*.md` to their archive directory or deletes them. Consumed briefs
(`/ai-brainstorm --consume`) move out of `drafts/`; unconsumed briefs age out
on a manifest TTL.

**A6. Manifest retention knobs.** Add a `lifecycle:` block to
`.ai-engineering/manifest.yml` (e.g. `draft_ttl_days`, `archive_layout`,
`reap_orphans`) replacing the hardcoded 14-day cutoff
(`.ai-engineering/scripts/spec_lifecycle.py:419`). SSOT for config.

### Concern B — Client-facing capability README

**B1. Rewrite to the welcome model.** Restructure `.ai-engineering/README.md`
on the Astro post-create + Diátaxis pattern: greeting → "what you can do now"
(tutorial/quick-win) → capability catalog (reference) → where to get help. The
maintainer reference (persistence tiers, ownership, sync contract) moves below
the fold or into a linked `MAINTAINERS.md`-style doc — it is not the client's
first need.

**B2. Generated capability catalog (derived cache).** Auto-generate the
53-skill / 9-agent catalog from the existing capability source
(`framework-capabilities.json` via
`src/ai_engineering/state/observability.py:1024-1039`, itself derived from
each `SKILL.md` `description:` field). The README section is a labelled
rebuildable cache, regenerated by `ai-eng install` / `update` / `dev sync` —
SSOT stays in the skill files, never hand-maintained in the README.

**B3. Fix stale facts (straight bug).** Delete the "Four-Tier Persistence"
table and every `state/state.db` reference (`.ai-engineering/README.md:34`,
`39-50`, `61`); align to the three-tier model in
`docs/persistence-doctrine.md`.

## 5. Evidence Catalog

| # | Claim | Citation |
|---|-------|----------|
| 1 | Canonical six-state lifecycle enum | `.ai-engineering/scripts/spec_lifecycle.py:72-78` |
| 2 | Closed legal-transition FSM table | `.ai-engineering/scripts/spec_lifecycle.py:82-89` |
| 3 | `mark_shipped` appends the ledger row | `.ai-engineering/scripts/spec_lifecycle.py:380-398` |
| 4 | `consolidate_shipped` is the manual repair path | `.ai-engineering/scripts/spec_lifecycle.py:517` |
| 5 | `archive` verb flips JSON only, never moves markdown | `.ai-engineering/scripts/spec_lifecycle.py:401-409` |
| 6 | Sweep ages DRAFT→ABANDONED, hardcoded 14-day cutoff | `.ai-engineering/scripts/spec_lifecycle.py:412-437` (line 419) |
| 7 | History migration precedent (`migrate_history`) | `.ai-engineering/scripts/spec_lifecycle.py:447` |
| 8 | Ledger Status column carries non-enum freeform strings | `.ai-engineering/specs/_history.md:7-153` |
| 9 | Ledger ID scheme inconsistent (numeric vs slug) | `.ai-engineering/specs/_history.md:153` |
| 10 | Active spec frontmatter declares `spec: spec-152` | `.ai-engineering/specs/spec.md:1-8` |
| 11 | `/ai-brainstorm` overwrites the single `spec.md` | `.claude/skills/ai-brainstorm/SKILL.md:57` |
| 12 | `/ai-plan` overwrites the single `plan.md` | `.claude/skills/ai-plan/SKILL.md:33` |
| 13 | `ai-eng cleanup specs` delegates to `consolidate_shipped` | `src/ai_engineering/cli_commands/cleanup.py:366-401` |
| 14 | `/ai-branch-cleanup` sweep + consolidate steps | `.claude/skills/ai-branch-cleanup/SKILL.md:64-70`, `:90` |
| 15 | No lifecycle/retention keys in manifest | `.ai-engineering/manifest.yml:163-178` |
| 16 | SSOT-PD doctrine (one writable store per datum) | `docs/persistence-doctrine.md:8-20` |
| 17 | Spec/plan are Tier-3 human doctrine | `docs/persistence-doctrine.md:90-94` |
| 18 | README opening is maintainer-oriented | `.ai-engineering/README.md:1-5` |
| 19 | README stale "Four-Tier" + `state.db` references | `.ai-engineering/README.md:34`, `39-50`, `61` |
| 20 | Capability catalog only exists machine-readable | `src/ai_engineering/state/observability.py:1024-1039` |
| 21 | Delivery-log relocation precedent (spec-117-progress) | `.ai-engineering/specs/_history.md:363` |
| 22 | Manual shipped-state commit proves the wiring gap | git commit `fa2564b5` |

## 6. Roadmap

**M1 — Canonical identity + enum-bound ledger (foundation).**
Resolve `spec-NNN` vs slug; rename sidecars; bind `_render_history()` to the
enum; one-shot migrate the 152 freeform rows; relocate the delivery-log tail.
*Gate:* `_history.md` Status column contains only the six enum values; every
row keyed by `spec-NNN`; no data lost (tail preserved or relocated with
references updated).

**M2 — Auto-wire the loop.**
Fire `mark_shipped` on PR merge; extend `archive` to snapshot markdown + reset
buffers into `archive/spec-NNN-<slug>/`; standardize the archive layout.
*Gate:* a test merge produces a ledger row, an immutable archive directory, and
reset working buffers with zero manual steps; idempotent re-run is a no-op.

**M3 — Orphan reaper + drafts TTL + manifest knobs.**
Sweep the 11 orphan root files; de-duplicate sidecars; add `lifecycle:` manifest
block; wire drafts consumption/TTL.
*Gate:* `specs/` root contains only the four canonical entries + two subdirs;
retention windows read from manifest; sweep dry-run lists exactly the orphans.

**M4 — Client README rewrite.**
Restructure to greeting → quick-win → catalog → help; move maintainer reference
below the fold / to a linked doc; fix the four-tier / `state.db` bug.
*Gate:* README leads with the client welcome; no `state.db` reference remains;
maintainer content still reachable.

**M5 — Generated capability catalog.**
Generate the 53-skill / 9-agent catalog from `framework-capabilities.json`;
wire regeneration into `ai-eng install`/`update`/`dev sync`; add a drift check.
*Gate:* catalog matches the live skill/agent count; `dev sync --check` fails on
drift; SSOT remains the `SKILL.md` descriptions.

## 7. Definition of Done

1. `_history.md` Status column contains **only** the six canonical enum values;
   all rows keyed by `spec-NNN`; Shipped column populated for every shipped row.
2. Merging a spec PR produces — with **zero manual commands** — a ledger row,
   an immutable `archive/spec-NNN-<slug>/{spec.md,plan.md}` snapshot, and reset
   working buffers. Re-running is idempotent.
3. `specs/` root contains only `spec.md`, `plan.md`, `_history.md`, `drafts/`,
   `archive/`. The 11 current orphans are gone; sidecars de-duplicated and
   single-scheme.
4. Retention windows (`draft_ttl_days`, archive layout, reaper toggle) are read
   from `.ai-engineering/manifest.yml`, not hardcoded.
5. `.ai-engineering/README.md` opens as a client welcome, contains an
   auto-generated capability catalog matching the live 53/9 counts, and carries
   **no** `state.db` or "four-tier" reference; the catalog regenerates via
   `ai-eng dev sync` and is drift-gated.
6. All changes covered by tests; `ai-eng dev sync --check` green; CHANGELOG
   documents every hard rename/migration.

## 8. Quality Stamps

- **§10.6 SDD** — this brief precedes the spec; `/ai-brainstorm` consumes it as
  the problem statement, `/ai-plan` decomposes, `/ai-build` or `/ai-autopilot`
  executes.
- **§10.4 DRY** — the README catalog and `_history.md` Status both become
  derived projections of a single source (skill descriptions; the FSM enum),
  eliminating hand-maintained duplicates.
- **SSOT-PD** — every datum gets one canonical writable store; the ledger Status,
  the README catalog, and the archive snapshot are labelled rebuildable caches
  with explicit rebuild paths (`docs/persistence-doctrine.md:8-20`).
- **§10.1 KISS** — no new state model; the fix is wiring + rendering over the
  existing FSM, not a re-architecture.
- **§10.7 Clean Code** — one archive layout, one ID scheme, one ledger Status
  vocabulary; orphans reaped.
- **CONSTITUTION §3** — hard renames/migrations, no backwards-compat shims;
  CHANGELOG records the breakage.

## 9. Open Decisions

1. **Canonical spec identity: numeric `spec-NNN` or slug?** Frontmatter and the
   ledger lean numeric; sidecars and the newest row lean slug. Pick one; the
   other becomes secondary metadata. (Affects A1, M1.)
2. **Archive trigger point:** snapshot + reset on `SHIPPED` (at merge) or only
   on the terminal `ARCHIVED` transition? Earlier reset keeps `specs/` cleaner
   but archives before any post-merge fixups.
3. **Merge-detection mechanism:** `/ai-pr` post-merge step, a git `post-merge`
   hook, or a `SessionEnd`/cleanup-time reconciliation? Trade-off: immediacy vs
   hot-path budget (CLAUDE.md pre-push budget < 5s).
4. **Maintainer reference home:** keep below the fold in the same README, or
   split into a separate `.ai-engineering/MAINTAINERS.md`?
5. **Delivery-log prose destination:** per-spec archive directory vs
   `state/archive/delivery-logs/` (the spec-122-a precedent).
6. **Drafts TTL value** and whether unconsumed briefs are deleted or archived.

## 10. Migration

Per CONSTITUTION §3 — **hard rename, hard migration, no shims.**

- **Sidecar rename** (slug → `spec-NNN.json`): one-shot `git mv`; de-duplicate
  `obvious-by-default*`. CHANGELOG entry.
- **`_history.md` Status normalization:** one-shot migration mapping legacy
  freeform strings to the six enum values, reusing the `migrate_history()`
  pattern (`.ai-engineering/scripts/spec_lifecycle.py:447`). The
  `_split_history()` tail-preservation already exists; the delivery-log prose is
  relocated, not deleted, with references grepped and updated first.
- **Archive layout standardization:** migrate existing flat files and `-plan.md`
  pairs into per-spec directories. Pure file moves; git history preserved.
- **Orphan reap:** the 11 root `spec-NNN-*.md` are moved to their archive
  directory (if a matching shipped spec exists) or deleted (if superseded).
- **README:** straight rewrite; the stale `state.db` table is deleted, not
  deprecated. No shim, no redirect.

No backwards-compatibility layer is introduced anywhere; the breakage is
documented in CHANGELOG and visible in one commit per migration.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Auto-`mark_shipped` fires on the wrong branch / double-fires | Medium | Medium | `consolidate_shipped` is already idempotent (checks known IDs); guard on merged-PR + branch match; dry-run in M2 gate |
| `_history.md` migration drops the freeform delivery-log tail | Low | High | `_split_history()` already preserves the tail; relocate-not-delete; snapshot the file in git before migrating; before/after row-count test |
| Merge-detection on the hot path blows the pre-push budget | Medium | Medium | Run reconciliation at cleanup/SessionEnd time, not pre-push (CLAUDE.md < 5s budget); keep `mark_shipped` off the commit hot path |
| README capability catalog drifts from live skills/agents | Medium | Low | Derived cache regenerated on install/update/sync; `dev sync --check` drift gate (DoD §5) |
| Identity-scheme rename breaks references in skills/tests/docs | Medium | High | Grep all `spec-NNN`/slug references before rename; update in the same commit; CI mirror/cross-ref validators catch stragglers |
| Reaper deletes a file that was actually load-bearing | Low | High | Reaper moves to archive by default, deletes only on confirmed supersession; dry-run lists targets first |

## 12. References

External prior art (every claim sourced):

1. **PEP 1 — PEP Purpose and Guidelines** — explicit status enum (Draft,
   Active, Accepted, Provisional, Deferred, Rejected, Withdrawn, Final,
   Superseded); rejected/superseded records are *retained*, supersession via
   paired `Superseded-By`/`Replaces` headers. https://peps.python.org/pep-0001/
2. **Rust RFCs** — accepted RFCs live permanently in `text/`; implementation
   tracked separately via tracking issues (decision doc decoupled from
   execution tracking). https://github.com/rust-lang/rfcs
3. **Michael Nygard, "Documenting Architecture Decisions"** — ADRs are
   immutable; a reversed decision is kept and marked superseded, never deleted.
   https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions
4. **MADR (Markdown Any Decision Records)** — one file per decision
   (`NNNN-title.md` in `decisions/`), status field includes "superseded by
   ADR-0123". https://adr.github.io/madr/
5. **Keep a Changelog v1.1.0** — "for humans," `Unreleased` section rolling into
   dated blocks; the commit-log-dump anti-pattern.
   https://keepachangelog.com/en/1.1.0/
6. **Conventional Commits v1.0.0** — message structure enabling curated-by-
   construction changelog generation. https://www.conventionalcommits.org/en/v1.0.0/
7. **GitHub Docs — About READMEs** — the five recommended README elements
   (what / why / get started / get help / who maintains).
   https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-readmes
8. **standard-readme** — README section spec and ordering.
   https://github.com/RichardLitt/standard-readme
9. **create-astro / Astro install docs** — the canonical post-install
   "greet + ordered next steps + help pointer" CLI model.
   https://docs.astro.build/en/install-and-setup/
10. **Diátaxis** — four documentation modes (tutorial / how-to / reference /
    explanation); the primary-source justification for not leading a landing
    README with the full reference catalog. https://diataxis.fr/

Internal anchor: `docs/persistence-doctrine.md` is the in-repo analogue of the
PEP/ADR "supersede, don't delete" pattern (SSOT-PD, three-tier files-only).

## 13. Glossary

- **LifecycleState (FSM):** the six canonical spec states and their closed
  legal-transition table (`.ai-engineering/scripts/spec_lifecycle.py:72-89`).
- **Sidecar:** the per-spec JSON state record at `state/specs/<id>.json` holding
  the current lifecycle state, ship date, PR, and branch.
- **Ledger:** `.ai-engineering/specs/_history.md` — the human-readable index of
  completed specs, rendered from sidecars.
- **Working buffer:** the single `spec.md` / `plan.md` files that
  `/ai-brainstorm` and `/ai-plan` overwrite each cycle.
- **Orphan artifact:** a stray `spec-NNN-*.md` left in `specs/` root that no
  longer corresponds to the active working buffer.
- **Supersession:** retaining a superseded document with a forward link rather
  than deleting it (PEP/ADR discipline).
- **Derived cache:** a labelled, rebuildable projection of a canonical source
  (per SSOT-PD) — here, the README catalog and the ledger Status column.
- **Capability catalog:** the human-readable enumeration of the 53 skills and 9
  agents, generated from skill `description:` frontmatter.
- **Diátaxis modes:** tutorial (learning), how-to (task), reference
  (information), explanation (understanding) — the documentation taxonomy.

## 14. Acceptance

- [ ] `_history.md` Status uses only the six enum values; all rows keyed by the
      chosen canonical ID; Shipped populated for shipped rows.
- [ ] PR merge auto-produces: ledger row + immutable `archive/spec-NNN-<slug>/`
      snapshot + reset working buffers, with zero manual commands; idempotent.
- [ ] `specs/` root holds only `spec.md`, `plan.md`, `_history.md`, `drafts/`,
      `archive/`; 11 orphans removed; sidecars single-scheme, de-duplicated.
- [ ] Retention/layout knobs read from `manifest.yml`'s `lifecycle:` block.
- [ ] Archive layout is uniform: one per-spec directory, no stray flat files or
      `-plan.md` pairs.
- [ ] `.ai-engineering/README.md` opens as a client welcome; carries no
      `state.db` / four-tier reference; aligns to the three-tier doctrine.
- [ ] README capability catalog matches live 53/9 counts, regenerates via
      `ai-eng dev sync`, and is drift-gated by `dev sync --check`.
- [ ] CHANGELOG documents every hard rename/migration; all changes tested;
      `ai-eng dev sync --check` green.
