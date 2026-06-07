---
spec: spec-168
title: Solution-intent discoverability, fail-open/closed doctrine, and TRY-lint fixes
status: in-progress
effort: small
summary: Close the real architecture-doc gaps without duplicating the existing matklad map — reconcile stale solution-intent.md path references (unbreaking the weekly drift runbook), add a root discoverability pointer, define the fail-open/closed doctrine once in gate-policy.md, and fix 3 TRY-lint bugs.
---

# Solution-intent discoverability, fail-open/closed doctrine, and TRY-lint fixes

## Summary

An external regex scorecard graded the repo C and flagged "Architectural
Documentation" as the weak spot. An adversarial audit (6-agent panel, grounded
in the repo) found that the obvious response — author an `ARCHITECTURE.md` —
would **duplicate a matklad-style layered module map that already exists** at
`.ai-engineering/solution-intent.md` §3.1 (the very source of the four enforced
`import-linter` contracts, CI-gated by `tests/architecture/test_hexagonal.py`).
Authoring a second copy would violate Hard Rule §13.7 (Single Source of Truth
Per Datum) — the precise failure the repo's governance exists to prevent.

The scorecard FAIL is therefore a **discoverability false-positive** with one
genuine bug behind it: `CHANGELOG.md:1851` records a deliberate move of the doc
from `docs/solution-intent.md` to `.ai-engineering/solution-intent.md`, but a
handful of references were never updated — including the **architecture-drift
runbook**, which `cat`s/greps the now-nonexistent `docs/` path on its weekly
run, so drift detection silently no-ops. Two further real gaps survive the audit:
the **fail-open/fail-closed error doctrine** governs ~273 source files (and an
`audit:exempt:…-fail-closed-gates` marker) yet is *defined nowhere*; and three
genuine `TRY` correctness bugs sit latent in the tree. This spec closes exactly
those real gaps — no new architecture doc, no metric-gaming.

## Goals

- No new `ARCHITECTURE.md` is authored; the existing `solution-intent.md` §3.1
  remains the single architecture map.
- Every stale `docs/solution-intent.md` reference is reconciled to the canonical
  `.ai-engineering/solution-intent.md`: the doc's own Source-of-Truth table, the
  `docs-freshness` and `architecture-drift` runbooks, **their `templates/`
  twins (lockstep parity)**, and the `templates/.ai-engineering/manifest.yml`
  comment.
- The weekly architecture-drift runbook resolves and reads the real file again
  (its section anchor / grep pattern verified against `solution-intent.md`).
- The architecture map is **discoverable from the repo root** via a one-line
  pointer (README and/or CANONICAL Surface Index) — no content duplicated.
- The **fail-open/fail-closed doctrine** is stated once, in `gate-policy.md`:
  security/integrity boundaries fail closed; plumbing fails open **and must
  log**; never silently swallow; never fail-open a security gate; the
  `audit:exempt` convention is the named escape hatch.
- `ruff` `lint.select` gains exactly **`TRY004` + `TRY400`**; the 3 violations
  are fixed and `ruff check` passes clean.
- No new lint suppression (§13.2); no second source of truth (§13.7).

## Non-Goals

- **Authoring a root `ARCHITECTURE.md`** — duplicates `solution-intent.md` §3.1
  (§13.7). Replaced by a pointer only.
- **Re-narrating the 4 import-linter contracts in prose** — already stated in
  `pyproject.toml` comments, DEC-029, the `test_hexagonal.py` docstring, and
  `solution-intent.md` §3.1. Highest rot-risk item; cut.
- **Relocating solution-intent to repo root as `SOLUTION-INTENT.md`** — that is
  a separate, unapproved draft brief
  (`specs/drafts/prune-contexts-docs-research-evals-brief.md`); out of scope here.
- **ty CI gate** (already blocking at `ci-check.yml:267`), **ADRs/`docs/adr`**
  (decision-store is the layer), **conventional-commit CI** (§13.6 hook),
  **API-doc gen / mutation / fuzz** (low-ROI metric-gaming).
- **The 117-site `BLE001` blind-except sweep** and `TRY003`/`EM101`/`EM102`/
  `TRY300` style rules.
- **Inventorying the ~273 fail-open/closed call sites** or adding a new CI gate
  to enforce the doctrine — that catalog would be the real drift surface.

## Decisions

### D-168-01 — Do not author ARCHITECTURE.md; the existing solution-intent map stands

**Decision**: Author no new architecture document. `.ai-engineering/solution-intent.md`
§3.1 remains the canonical matklad-style layered module map.

**Rationale**: §3.1 already bins all ~33 packages into the six named layers that
*are* the source for the four `[tool.importlinter]` forbidden contracts
(DEC-029), mechanically enforced by `test_hexagonal.py`. A second doc would be a
copy to keep in sync — a direct §13.7 violation, and the audit scored it 2/10
with high over-engineering risk. The scorecard cannot see `.ai-engineering/`, so
its FAIL is a detection blind spot, not a missing artifact.

### D-168-02 — Reconcile stale `docs/solution-intent.md` references to the canonical path

**Decision**: Update the stragglers left by the `CHANGELOG.md:1851` move
(`docs/` → `.ai-engineering/`) to the canonical `.ai-engineering/solution-intent.md`:
the doc's SoT table (line 783), `runbooks/docs-freshness.md`,
`runbooks/architecture-drift.md`, the two `templates/.ai-engineering/runbooks/`
twins, and the `templates/.ai-engineering/manifest.yml` comment.

**Rationale**: This is a real latent bug, not cosmetics — the architecture-drift
runbook `cat`s and greps a nonexistent path on its weekly run, so drift
detection has been silently no-op'ing. The file is in the correct place; the
references are stale. Template twins are updated in lockstep because no CI guard
enforces runbook mirror parity.

### D-168-03 — Add a root-level discoverability pointer, not a doc

**Decision**: Add a one-line pointer to `.ai-engineering/solution-intent.md`
from a root-discoverable surface (README "Architecture" line and/or the CANONICAL
Surface Index), via `CANONICAL.md` + `ai-eng dev sync` (never hand-editing a
generated mirror).

**Rationale**: The only genuine residue of the scorecard FAIL is that a newcomer
landing at the repo root cannot find the map (it lives under `.ai-engineering/`).
A pointer closes that front-door gap with zero content duplication — the
honest, non-over-engineered form of "ARCHITECTURE.md."

### D-168-04 — Define the fail-open/closed doctrine once, in gate-policy.md

**Decision**: State the doctrine in `.ai-engineering/reference/gate-policy.md` as
one section: security/integrity boundaries fail **closed**; framework plumbing
fails **open and must log**; never silently swallow; a security gate that cannot
run is a fail-open hole (a bug); the `audit:exempt` marker is the named escape
hatch. Cross-link from CANONICAL §13 and `principles.md`. Do **not** spawn a new
reference file.

**Rationale**: The audit confirmed a real keystone gap — the doctrine governs
~273 files and is *referenced* as settled law in four docs, yet **defined
nowhere** (`principles.md` §10 has no error doctrine; `gate-policy.md`, the
natural home for gate posture, never states the rule), and an
`audit:exempt:…-fail-closed-gates` marker points at no written doctrine. Folding
into the existing `gate-policy.md` closes the latent-bug surface without adding a
fifth orphan doc to keep in sync.

### D-168-05 — Enable ruff TRY004 + TRY400 only; fix 3 violations; reject BLE001 and style rules

**Decision**: Add `TRY004` and `TRY400` to `ruff` `lint.select`, fix the 3
violations, and explicitly do not enable `BLE001`, `TRY003`, `EM101`, `EM102`,
or `TRY300`.

**Rationale**: The three are verified genuine correctness bugs — `TRY004` raises
the wrong exception type for invalid-type input (`installer/phases/pipeline.py`,
`validator/categories/manifest_coherence.py`), `TRY400` drops a traceback via
`logging.error` in an `except` (`hook-common.py`) — and they mechanically encode
the fail-loud half of the doctrine in D-168-04. `BLE001` (117 hits) targets the
intentional fail-open plumbing layer; enforcing it would require `# noqa` that
§13.2 forbids. `TRY003/EM/TRY300` are pure style with no correctness yield.

## Risks

- **R1 — Template-mirror parity.** Runbook edits must be byte-mirrored under
  `src/ai_engineering/templates/.ai-engineering/runbooks/`; no CI guard enforces
  runbook parity. *Mitigation:* plan enumerates and edits both copies in
  lockstep.
- **R2 — `gate-policy.md` may not be the natural home for a cross-cutting
  doctrine.** It governs gate posture; the doctrine is broader. *Mitigation:* if
  it does not fit cleanly, a tight single `reference/` doc is the fallback —
  one home either way; decide in plan.
- **R3 — The drift runbook's anchor may also be stale.** It cites a "mermaid
  module graph (section 2.2)" but the map is at §3.1 in the current file.
  *Mitigation:* plan verifies the runbook's section anchor and grep pattern
  against `solution-intent.md`, not just the path string.
- **R4 — CANONICAL edit without mirror regen reds the parity gate.**
  *Mitigation:* edit `CANONICAL.md`, run `ai-eng dev sync`; never hand-edit
  `CLAUDE.md` or another generated mirror.
- **R5 — TRY004/TRY400 may surface outside `src/`.** *Mitigation:* `tests/` is
  confirmed clean for both; run full `ruff check` during planning and fix or
  scope explicitly — no blanket ignore.

## References

- doc: report.md (AI Harness Scorecard, 2026-06-03)
- doc: .ai-engineering/solution-intent.md (§3.1 layered module map — canonical)
- doc: .ai-engineering/runbooks/architecture-drift.md (broken-path consumer)
- doc: .ai-engineering/reference/gate-policy.md (doctrine home)
- doc: CHANGELOG.md (line 1851 — the docs/ → .ai-engineering/ move)
