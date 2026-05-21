# Brief — Commit the decision store (un-gitignore `decision-store.json`)

> Pre-`/ai-brainstorm` problem brief. Surfaced during the spec-149
> `/ai-build` run (D-149-03 / no_suppression gate), 2026-05-22.

## Problem

`.ai-engineering/state/decision-store.json` is **gitignored**
(`.gitignore:170`) and classified by `docs/persistence-doctrine.md` as a
**derived cache** — rebuildable from spec markdown via
`ai-eng decision backfill`.

But the doctrine contradicts itself. `persistence-doctrine.md:120` (the
decision-store row) states:

> "Risk/flow decision rows written by `ai-eng risk`/`decision record`
> are lifecycle data, **not rebuildable from specs**."

So the **sole copy** of non-rebuildable governance/risk decisions lives in
a gitignored file. A discardable cache cannot be the only witness of
non-rebuildable data (violates the doctrine's own SSOT rule:
"caches are never the primary witness").

## Impact

- Risk acceptances authored via `ai-eng risk accept` are **lost on a
  fresh checkout**, **absent in CI**, and **not team-shared**.
- The `no_suppression` gate validates a suppression's `dec_id` against
  `decision-store.json` (`tools/no_suppression/allowlist.py`,
  `cli.py:168`, run in `ci-check.yml:145`). Because the store is absent
  in CI, **binding a suppression to a DEC fails the gate in CI** — this
  is exactly why spec-149 D-149-03 was dropped.
- The loader still points `_dec_status` at the **deleted** `state.db`
  (Part-A leftover; dormant only because every entry's `dec_id` is empty).

## Design fork (for `/ai-brainstorm`)

- **(A) Commit the whole file** — un-gitignore `decision-store.json`.
  Simple; matches "it's where we save decisions". Risk: **session-flow
  churn** (10+ writers incl. `commands/workflows.py`, `gate.py`,
  `framework_defaults.py`) → noisy commits / merge conflicts.
- **(B) Split the store** — durable governance/risk decisions →
  committed record; ephemeral flow decisions → gitignored derived cache.
  Clean SSOT; more work (model/schema/path split + writer routing).

## Affected surfaces

- `.gitignore:170` (the ignore rule).
- `docs/persistence-doctrine.md` — Tier-2 reclassification + the
  self-contradicting row at line 120.
- `tools/no_suppression/allowlist.py` — repoint `_dec_status` off the
  deleted `state.db` → `decision-store.json`; drop the lingering
  `sqlite3` import; require `dec_id` for `nosemgrep_hash` security
  entries (the spec-149 D-149-03 work, redone once the store is committed).
- `tests/unit/no_suppression/test_allowlist.py` (state.db → file seeding).
- `ai-eng risk accept` / `decision record` write paths.

## Downstream unblock

Enables security-suppression DEC-binding (spec-149 D-149-03, dropped) to
be implemented correctly — the gate can validate DECs in CI once the
store is committed.

## Open questions

- Commit-whole (A) vs split (B)?
- What counts as "flow" (ephemeral) vs "governance/risk" (durable)?
- Churn / merge-conflict mitigation if committed.
- Does committing the hash chain impose commit-time chain-maintenance
  burden, and how does that interact with the audit `verify`?
