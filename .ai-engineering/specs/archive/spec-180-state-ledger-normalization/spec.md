---
spec: spec-180
title: Normalize spec-state ledger and dogfood template parity
status: in-progress
effort: large
summary: Reconcile the 40 spec-state sidecars to their true state via multi-signal evidence, guard the ledger in CI, fix the sweep that mislabels shipped specs and dumps on main, and guard template↔project parity — so a team of humans and agents share one trustworthy source of truth.
---

# spec-180 — Normalize spec-state ledger and dogfood template parity

## Summary

The git-tracked spec-state ledger (`.ai-engineering/state/specs/*.json`) is
badly out of sync with reality: of 40 sidecars, 20 are `shipped`, but 8
`approved` and 11 `draft` are stuck non-terminal — and many of those actually
shipped (spec-131/132/133/145/148 are referenced 6–8× each as live decisions in
CLAUDE.md / reference docs; their sidecars were simply never `mark_shipped`).
Because the ledger is tracked AND drifted, every cleanup sweep re-flips the
stale drafts to `abandoned` (mislabeling shipped specs) and dumps the change
uncommitted onto protected `main` — the recurring "something always stays
changed and then you delete it" loop. ai-engineering is built for team and
multi-agent work where humans and agents must stay aligned on what is being
developed, so the lifecycle ledger must be a SHARED, COMMITTED, TRUSTWORTHY
source of truth — not hidden, and not drifting. Separately, the dogfooded
`.ai-engineering/` tree must faithfully mirror to the installable template so a
fresh install matches the project that produced it; several mirror surfaces
(e.g. `scripts/`) have no parity guard today.

## Goals

- Every one of the 40 sidecars resolves to a state that matches hard evidence
  (a merged PR, an `archive/` snapshot, or live `D-NNN`/`spec-NNN` references in
  canonical docs/code); no sidecar contradicts reality after this spec.
- A CI guard fails the build if any sidecar's state contradicts its evidence
  (e.g. a `shipped` with no PR/archive, or a `draft` whose decisions are live),
  so the shared ledger cannot silently drift again.
- The cleanup sweep never (a) flips a sidecar to `abandoned` without a
  shipped-detection pass, nor (b) leaves uncommitted tracked changes on a
  protected branch — it either routes changes through a branch/PR or refuses.
- The installable template (`src/ai_engineering/templates/.ai-engineering/`)
  faithfully mirrors the consumer-shipped dogfood surfaces, enforced by a parity
  guard; project-specific data (the live spec slot, sidecars, gitignored state)
  is explicitly excluded from the mirror.
- One-time data fixes land: spec-152's missing `archive/` snapshot and the
  `spec-158.json`↔slug-`spec-159` id mismatch are resolved.

## Non-Goals

- Building multi-agent coordination FEATURES on top of the ledger (a shared
  "who's working on what" surface) — this spec makes the ledger trustworthy;
  coordination tooling is a future direction.
- Changing the persistence model: sidecars STAY git-tracked (the team/agent
  alignment requirement rules out gitignoring them or making them per-install).
- Migrating away from files-only persistence or touching the NDJSON audit chain.
- Reformatting or rewriting the content of already-correct shipped sidecars or
  their archived spec/plan snapshots.
- Interactive per-spec adjudication — reconciliation runs autonomously and emits
  a report (operator reviews post-hoc, not inline).

## Decisions

### D-180-01 — Tracked, reconciled, guarded ledger (not gitignored)

The sidecar JSONs remain the git-tracked canonical source of truth for spec
lifecycle state. Reconcile them to reality once, then guard them.

**Rationale**: ai-engineering targets team and multi-agent-company work where
humans and agents must stay aligned on in-flight and shipped developments. That
alignment requires ONE shared, committed ledger every actor reads — gitignoring
the sidecars (per-install local state) or hiding in-flight states would give
each agent a private, divergent view and defeat alignment. The churn is not
cured by hiding the ledger but by making it correct and keeping it correct.

### D-180-02 — One spec, three concerns (multi-concern → autopilot route)

Deliver ledger reconciliation, the sweep fix, and template↔project parity as one
coherent spec rather than sequencing them.

**Rationale**: all three serve a single outcome — one trustworthy shared source
of truth that a team and its agents stay aligned on. They share the same data
surfaces (`state/specs`, `specs/archive`, `_history.md`, the template mirror) and
land most coherently together. The breadth routes execution through
`/ai-autopilot` (multi-wave) rather than a single `/ai-build`.

### D-180-03 — Autonomous reconciliation via a three-signal evidence test

Reconciliation runs without an interactive gate and emits a report. A stale
sidecar is classified `shipped` when ANY of three signals holds — a merged PR
resolvable by slug/branch/spec-id (via `gh`), an existing `archive/<spec>/`
snapshot, or live `D-NNN-*`/`spec-NNN` references in canonical docs/code; it is
classified `abandoned` ONLY when ALL THREE are absent AND the spec is superseded
(or older than the sweep threshold). Terminal states are never downgraded.

**Rationale**: the operator chose a no-prompt autonomous pass, but a naive
"PR-found-else-abandoned" rule is exactly what mislabeled shipped specs and
caused this work. Widening the shipped test to three independent signals makes
the autonomous pass robust against thin-evidence false-abandons while still
requiring zero prompts; the emitted report plus the D-180-04 guard catch any
residual error.

### D-180-04 — CI guard: ledger state must match evidence

Add a CI/test guard that fails when any sidecar's state contradicts its
evidence — a non-terminal sidecar whose spec is demonstrably shipped, a
`shipped` sidecar with neither PR nor archive, or an `archived`/`shipped`
id↔slug mismatch.

**Rationale**: reconciling once without a guard guarantees re-drift the next time
a spec ships via a flow that forgets to `mark_shipped`. The guard converts the
ledger from "hopefully current" to "provably consistent," which is the contract
a multi-actor team relies on.

### D-180-05 — Sweep is mislabel-safe and never dumps on a protected branch

Fix `spec_lifecycle.py sweep` / the `/ai-branch-cleanup` sweep so it (a) runs the
D-180-03 shipped-detection before ever marking a stale sidecar `abandoned`, and
(b) never leaves uncommitted tracked changes on a protected branch — it routes
any state write through a branch/PR or refuses with a clear message.

**Rationale**: the sweep's blind "old draft → abandoned + write-in-place" is the
direct mechanism of the recurring churn (it mislabeled spec-131/132/133/148 and
dumped them on `main` twice in recent sessions). The guard (D-180-04) defends the
data; this fixes the actor that corrupts it.

### D-180-06 — Template↔project parity for consumer-shipped surfaces, guarded

Audit and close drift between the dogfooded `.ai-engineering/` tree and the
installable template for the surfaces a consumer is meant to receive (e.g.
`scripts/`, `overrides/`, `runbooks/`, `reference/`, `policies/`, `security/`,
`manifest.yml`, `LESSONS.md`, `README.md`), and add a parity guard. Project-
specific data — the live spec slot (`specs/spec.md`/`plan.md`), the sidecars,
`archive/`, and gitignored runtime/state — is explicitly EXCLUDED from the mirror
(the template ships placeholders, never the dogfood's own specs).

**Rationale**: "dogfood updated template ↔ project" means a fresh install must
match the project that produced it. Some mirror surfaces (notably `scripts/`)
have no CI parity guard today, so silent drift ships broken installs. A guard
makes parity a build invariant; excluding project-specific data keeps the
template clean.

### D-180-07 — One-time data fixes

Generate the missing `archive/` snapshot for spec-152, and resolve the
`spec-158.json` record whose `slug` reads `spec-159` (id↔slug mismatch).

**Rationale**: these are concrete inconsistencies the audit surfaced; leaving
them would trip the D-180-04 guard on its first run.

## Risks

- **R1 — autonomous reconciliation mislabels a thin-evidence spec.** *Mitigation:*
  the three-signal test (D-180-03) plus the generated report plus the D-180-04
  guard (which fails CI on any state↔evidence contradiction) provide three
  independent catches before a wrong label can persist.
- **R2 — the reconciliation produces a large one-time sidecar diff.** *Mitigation:*
  land it as its own clearly-scoped commit ("reconcile ledger to evidence") with
  the report attached, so the audit history is legible.
- **R3 — the template-parity guard is too strict and flags intentional
  divergence.** *Mitigation:* scope the guard to consumer-shipped surfaces with an
  explicit exclude-list for project-specific data; normalize (not byte-equal)
  where a surface legitimately differs (e.g. line endings).
- **R4 — a sidecar's "live decision references" signal yields a false positive**
  (a doc mentions a superseded spec). *Mitigation:* require the reference to be a
  decision anchor (`D-NNN-*`) or an explicit shipped marker, not any mention; the
  report lists the evidence per spec for audit.

## References

- doc: docs/persistence-doctrine.md
- doc: .ai-engineering/specs/_history.md
- doc: .ai-engineering/scripts/spec_lifecycle.py
- doc: src/ai_engineering/templates/.ai-engineering
