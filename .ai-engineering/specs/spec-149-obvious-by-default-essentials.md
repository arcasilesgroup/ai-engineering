---
spec: spec-149
slug: obvious-by-default-essentials
title: Obvious-by-default essentials (trimmed)
status: approved
effort: small
summary: "Re-scope spec-148 Part B (obvious-by-default conventions, D-148-11..17 — never executed) under a YAGNI lens. KEEP the cheap, real-value items (ai-spec-draft surfacing in §11, dry-run-by-default branch deletion); SIMPLIFY deterministic-done to the one real gap; DEFER security-suppression DEC-binding to its own spec (decision-store.json must be committed first — a Part-A doctrine fix surfaced during build); DROP the gate-theater that enforces conventions this repo already follows (trigger de-collision, §10.x citation CI, naming-grammar CI, branch-cleanup orchestrator merge). Supersedes spec-148 D-148-11 through D-148-17."
supersedes: [spec-148 D-148-11, spec-148 D-148-12, spec-148 D-148-13, spec-148 D-148-14, spec-148 D-148-15, spec-148 D-148-16, spec-148 D-148-17]
---

# Spec 149 — Obvious-by-default essentials (trimmed)

## Summary

spec-148 Part A (files-only persistence) shipped on PR #532. Part B —
the "obvious-by-default conventions" carried from spec-147 (decisions
D-148-11 through D-148-17) — was **never executed**. Before building it
we reviewed it under §10.2 YAGNI / "fewest moving parts", and concluded
that roughly half is **over-engineering**: CI gates and edits that
enforce conventions this repository *already follows*, for speculative
problems with no observed instance. Enforcing "obvious by default" with
gate-theater would itself violate the thesis.

This spec replaces spec-148 Part B with a trimmed set: keep the items
that fix a real, observed problem at low cost; simplify the
deterministic-done work to the single genuine gap; and explicitly drop
the rest with rationale, so no half-built convention machinery is left
behind. Effort drops from **large** to **small**.

The kept work is doc + a small CLI safety default + a security-governance
bind + one quality-loop reproducibility fix. The dropped work touched
~80 files (10 skills × 6 mirror surfaces + 22 §10.x backfills + a naming
gate + a branch-cleanup orchestrator merge) for marginal or zero
real-world value.

## Goals

- **G1 — Visible spec on-ramp.** `ai-spec-draft` appears in the
  CLAUDE.md §11 canonical chain as the optional pre-`/ai-brainstorm`
  step, and the `ai-code` (subcomponent) vs `ai-build` (gateway)
  boundary is stated. Mirrors regenerated; surface count unchanged.
- **G2 — No destructive default.** `ai-eng cleanup branches` with no
  mode flag prints a plan and requires confirmation; it never silently
  sets `merged=True` and deletes. A test asserts a no-flag invocation
  deletes nothing.
- **G3 — (DEFERRED) Security-suppression DEC-binding.** Moved to its own
  spec (`drafts/decision-store-commit-brief.md`): DEC-binding cannot be
  CI-enforced while `decision-store.json` is gitignored. Security
  suppressions remain bound to the required, tracked `spec_ref` +
  `justification` + `expires_at` until the decision store is committed.
- **G4 — Reproducible STOP.** The quality-loop STOP verdict is
  reproducible for an identical diff: the one LLM-judged element
  (quality.md Step 2d remediation-eligibility condition 4 — "does not
  require a product decision …") cannot silently flip auto-pass /
  auto-block. A replay test asserts same diff → same STOP verdict.
- **G5 — Clean de-scope.** spec-148 D-148-11, D-148-12, D-148-14,
  D-148-15 are recorded as superseded/dropped with YAGNI rationale;
  D-148-13/16/17 are re-scoped to the trimmed versions above. CHANGELOG
  documents the de-scope. No partial gate-theater (no orphaned CI test,
  no half-edited skill descriptions) is left in the tree.

## Non-Goals

- **No trigger-phrase de-collision** (drops D-148-11's collision edits).
  No edits to the 10 contested-phrase skill descriptions.
- **No §10.x citation backfill or CI gate** (drops D-148-14). No
  `test_workflow_principle_citation.py`.
- **No naming-grammar CI gate** (drops D-148-15). No
  `test_skill_naming_grammar.py`.
- **No branch-cleanup orchestrator merge** (drops D-148-12). The two
  thin entry points (`maintenance branch-cleanup`, `cleanup branches`)
  stay; they already share every low-level op in `branch_cleanup.py`.
- **No blanket `method: deterministic|llm` tag** on every `/ai-verify`
  Finding — only the one STOP-reproducibility fix (G4). Added only if a
  concrete consumer is identified (none today).
- **No suppression DEC-binding and no decision-store gitignore change.**
  All of D-148-17 (security subset, loader repoint, and the churny
  phased-warning path) is **deferred** to a dedicated spec
  (`drafts/decision-store-commit-brief.md`) — committing
  `decision-store.json` is the Part-A doctrine prerequisite and is out of
  scope here.
- **No change to spec-148 Part A** (files-only persistence is shipped).
- **No new skills, no skill folds/deletes.** Surface count unchanged.

## Decisions

### Kept (real problem, low cost)

### D-149-01 — Surface `ai-spec-draft` in the §11 chain + state the build boundary [carries the cheap half of D-148-11]
Add `ai-spec-draft` to the CLAUDE.md §11 canonical chain as the optional
pre-`/ai-brainstorm` step (research/one-pager hand-off), and document the
`ai-code` (writes a specific subcomponent, no plan required) vs
`ai-build` (gateway that executes an approved plan) boundary. Doc edit +
`scripts/sync_mirrors` regen across the IDE surfaces.
**Rationale**: A real chain gap — `ai-spec-draft` exists but is invisible
in the canonical on-ramp, and the two implementation skills overlap on
"implement this". Pure documentation; near-zero risk; helps routing
without any behavior change.

### D-149-02 — Dry-run-by-default for `cleanup branches` [re-scopes/keeps D-148-16]
`ai-eng cleanup branches` with no mode flag prints a plan and requires
confirmation rather than defaulting to `merged=True` and deleting
(today: `cli_commands/cleanup.py:257-260` sets `merged=True`;
`:297-300` deletes). A test asserts a no-flag invocation deletes nothing.
**Rationale**: A destructive default is the inverse of the pit of
success — the single highest-ROI fix in the original Part B. Real
footgun, small change.

### D-149-03 — DEFERRED: security-suppression DEC-binding [was re-scope of D-148-17]
**Deferred to its own spec** (see
`.ai-engineering/specs/drafts/decision-store-commit-brief.md`). Binding
`nosemgrep_hash` security suppressions to a DEC cannot be CI-enforced
today: the `no_suppression` gate validates `dec_id` against
`decision-store.json`, which spec-148 Part A made **gitignored** (absent
in CI) — binding would fail the gate in CI. The root cause is a Part-A
doctrine flaw (`decision-store.json` holds non-rebuildable risk/flow
decisions yet is classified as a gitignored derived cache; the doctrine
admits the contradiction at `persistence-doctrine.md:120`). Committing the
decision store is the prerequisite, and reversing a merged Part-A
persistence decision deserves its own deliberate spec — not a bolt-on to
this conventions spec.
**Until then**: security suppressions stay bound to the **required,
tracked** `spec_ref` + `justification` + `expires_at` fields in
`suppression-allowlist.yml` (committed, reviewed, present in CI) — the
actual CI-enforceable governance. The dormant `state.db` reference in the
loader is left for the dedicated spec (no entry sets a `dec_id`, so it is
never hit).
**Rationale**: discovered during `/ai-build` that the bind is incompatible
with the gitignored store; surgical-change discipline keeps the Part-A
doctrine fix out of this conventions spec.

### Simplified

### D-149-04 — One STOP-reproducibility fix; no blanket method tags [re-scopes D-148-13]
The quality-loop STOP verdict (`ai-build` handler `quality.md` Step
2c/2e) is already deterministic — it counts blocker/critical/high.
The one LLM-judged element is Step 2d remediation-eligibility condition 4
("the fix does not require a product decision, architecture redesign
…"). Make that condition advisory / operator-confirmable so it cannot
silently flip the auto-pass/auto-block outcome, and add a replay test
asserting same diff → same STOP verdict. DROP the spec-148 plan to tag
every `/ai-verify` Finding with `method: deterministic|llm` (no consumer
identified).
**Rationale**: Fix the narrow real gap (one judgment call that can move
the verdict); skip the broad finding-model change that nothing reads.

### Dropped (YAGNI / over-engineering — superseded with rationale)

### D-149-05 — Drop trigger-phrase de-collision [supersedes D-148-11 collision edits]
Do not edit the 10 contested-phrase skill descriptions. Surface count
and descriptions unchanged (except the D-149-01 §11/boundary doc).
**Rationale**: Speculative — no observed wrong-skill misrouting. The
descriptions already carry "Not for X; use /Y instead" boundaries. ~60
file touches (10 skills × 6 mirror surfaces + a parsing gate) for
marginal triggering precision is unjustified until a real misfire is
seen.

### D-149-06 — Drop the branch-cleanup orchestrator merge [supersedes D-148-12]
Leave `ai-eng maintenance branch-cleanup` and `ai-eng cleanup branches`
as two thin entry points. Do not delegate, do not delete `run_branch_cleanup`.
**Rationale**: They already share every low-level op
(`list_merged_branches`, `list_gone_branches`, `delete_branches`,
`fetch_and_prune`) from `maintenance/branch_cleanup.py`; only the
orchestration differs, and the two orchestrations serve different UX
(targeted `--base/--target` maintenance vs the spec-133 7-mode power
tool). Merging means enriching one command, harmonizing exit codes
(0/1 vs 0/1/2/78), and rewriting ~6 tests — high cost for a cosmetic DRY
win with no behavior gain. Tolerable duplication.

### D-149-07 — Drop the §10.x citation CI gate [supersedes D-148-14]
Do not backfill `§10.x` anchors into the ~22 Workflow-without-citation
skills and do not add `test_workflow_principle_citation.py`.
**Rationale**: A regex asserting a `§10.\d` *exists* in a Workflow is
presence-theater — a skill can cite `§10.1` meaninglessly and pass. It
enforces nothing about correctness or fit, only that a token is present.

### D-149-08 — Drop the naming-grammar CI gate [supersedes D-148-15]
Do not codify the `ai-` + lowercase-kebab + verb|noun grammar in a CI
test (`test_skill_naming_grammar.py`).
**Rationale**: All 53 skills already comply — zero violations. A gate
that enforces an already-universal rule with no history of breakage is
speculative drift-guarding (YAGNI). If a bad name ever lands, add the
gate then.

## Risks

- **Dropping de-collision lets a real misroute slip later** (Low/Low):
  no evidence today; existing "Not for X" boundaries mitigate; revisit
  with a concrete misfire if one is observed.
- **Two branch-cleanup entry points persist** (Low/Low): a mild DRY
  wart; behavior is correct and low-level ops are shared. Documented
  as accepted.
- **Security-suppression bind blocks CI if a current security entry
  cannot get a DEC in this PR** (Low/Med): mitigated by authoring the
  DECs for the known `ssrf-urllib-request` entries within this PR;
  the bind is scoped to `nosemgrep_hash` security rules only.
- **quality.md change touches the build quality gate** (Med/Low):
  advisory-only is the conservative direction (cannot auto-block
  silently); the replay test guards reproducibility; no second
  remediation pass semantics change.
- **Re-scoping a superseded-but-unshipped Part B** (Low/Low): spec-148
  Part B never landed, so there is no migration or rollback — only a
  documentation supersession + CHANGELOG note.

## Open Questions

- **D-149-04 — advisory vs deterministic for Step 2d condition 4**:
  "advisory / operator-confirmable" is simpler and safer; encoding
  "requires a product decision" as a deterministic rule is itself hard
  and may be its own over-engineering. Settle the exact mechanism in
  `/ai-plan` (lean advisory-only).
- **D-149-03 — scope of "security" rules requiring an immediate DEC**:
  just the `nosemgrep_hash` security rules currently present
  (`ssrf-urllib-request`), or any rule whose `pattern` is
  `nosemgrep_hash`? Confirm the predicate in `/ai-plan`.
