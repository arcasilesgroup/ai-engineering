---
spec: runbook-template-parity
slug: runbook-template-parity
title: "Runbook header translations: template parity + cross-IDE"
status: in-progress
effort: small
summary: "Complete PR #585 by translating the 14 template runbook twins to match the live repo and adding a repo↔template byte-parity CI guard; deliver on the PR #585 fork branch."
---

# Runbook header translations: template parity + cross-IDE

## Summary

PR #585 (`eramos/ai-engineering:feat_translations`) translates three Spanish
section headers to English across the 14 runbook files under
`.ai-engineering/runbooks/`:

- `## Objetivo` → `## Objective`
- `## Precondiciones` → `## Prerequisites`
- `## Procedimiento` → `## Procedure`

These three are the *only* Spanish headers present (verified by accent/keyword
sweep — no residual remains). However the PR edits the **live repo copies
only**. Each runbook has a byte-identical twin under
`src/ai_engineering/templates/.ai-engineering/runbooks/` that ships to every
downstream install via `ai-eng install`. The PR leaves those twins in Spanish,
so installs of every IDE would still receive Spanish headers — the change is
not yet cross-IDE.

There is no CI guard enforcing repo↔template runbook byte-parity today
(`validate_runbooks` only asserts files exist), so this drift is silent — the
same gap class previously seen with `.ai-engineering/scripts/*` template twins.

This spec completes PR #585 by (1) applying the identical three-header
translation to the 14 template twins so installs match the live repo, and
(2) adding a CI parity guard so repo↔template runbook drift can never ship
silently again. Delivery is a commit pushed directly onto the PR #585 fork
branch (`maintainerCanModify: true`), keeping it a single PR under the original
author.

## Goals

- Translate the same three headers (`Objetivo`→`Objective`,
  `Precondiciones`→`Prerequisites`, `Procedimiento`→`Procedure`) in all 14
  template runbooks so each template twin is byte-identical to its live repo
  counterpart after PR #585.
- Add a CI test asserting every `.ai-engineering/runbooks/*.md` is
  byte-identical to its `src/ai_engineering/templates/.ai-engineering/runbooks/`
  twin (extending `tests/unit/test_runbook_contracts.py`, which already imports
  both roots and lists all 14 runbooks).
- Land the fix as a commit on the existing PR #585 fork branch — one PR, single
  author, complete change.

## Non-Goals

- Translating any content other than the three named headers (no body prose,
  no frontmatter, no other files). PR #585 already covers the live copies.
- Mirroring runbooks to per-IDE surfaces (`.codex/`, `.github/`, `.agents/`).
  Runbooks are IDE-agnostic and live only under the shared `.ai-engineering/`
  tree plus its install template; "cross-IDE" here means install/template
  parity, not per-IDE duplication.
- Generalising the parity guard to other template trees (scripts, hooks already
  have their own parity tests). Scope is runbooks only.
- Opening a separate upstream branch or second PR.

## Decisions

### D-runbook-template-parity-01 — Translate the 14 template twins to match the live repo copies

Apply the identical three-header substitution to every file under
`src/ai_engineering/templates/.ai-engineering/runbooks/*.md` so each twin equals
its `.ai-engineering/runbooks/` counterpart byte-for-byte after PR #585's live
edits.

**Rationale**: The template tree is what `ai-eng install` ships to downstream
projects regardless of IDE. Leaving it Spanish means the PR's intent (English
consistency, noticed during the workshop) never reaches installs. Byte-parity
with the live copy is the established contract for the runbook twins.

### D-runbook-template-parity-02 — Add a repo↔template runbook byte-parity CI guard

Extend `tests/unit/test_runbook_contracts.py` with a test that, for each of the
14 runbooks, asserts `RUNBOOK_ROOT/<name>.md` and `TEMPLATE_ROOT/<name>.md`
have identical bytes; fail loud with the offending filename(s).

**Rationale**: The drift PR #585 introduced was silent — no gate caught the
template twin lagging the live copy. A byte-parity assertion closes the gap
permanently at near-zero cost, reusing the roots and runbook list the test
module already defines. This is the runbook analogue of the existing hook/script
template-parity tests.

### D-runbook-template-parity-03 — Deliver as a commit on the PR #585 fork branch

Push the template translations + parity guard onto
`eramos/ai-engineering:feat_translations` (`maintainerCanModify: true`) rather
than opening a new branch/PR.

**Rationale**: The operator asked to "fix this PR." A single PR keeps authorship
and review history intact, and the parity guard will run against the combined
(live + template) change in one CI pass — proving completeness before merge.

## Risks

- **Template twin not byte-identical after edit** — a stray whitespace or
  line-ending difference would make D2's guard fail. Mitigation: apply the
  substitution mechanically and run the new parity test locally before pushing.
- **Parity guard surfaces *other* pre-existing drift** — if any of the 14 twins
  already differs beyond the three headers, the new test will flag it. This is
  desirable (it is the bug the guard exists to catch) but may expand the diff.
  Mitigation: a pre-flight `diff` over all 14 pairs confirmed they are currently
  identical, so post-translation they will match.
- **Pushing to a fork branch requires maintainer push access** — verified
  `maintainerCanModify: true`. If push is rejected, fall back to a new upstream
  branch (the rejected delivery option) without changing D1/D2.
- **Missing CHANGELOG entry** — header translation is not user-facing runtime
  behavior; no CHANGELOG entry required, consistent with PR #585's own scope.
