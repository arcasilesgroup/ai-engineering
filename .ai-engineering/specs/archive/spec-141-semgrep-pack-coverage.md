---
spec: spec-141
slug: semgrep-pack-coverage
title: Semgrep Pack Coverage Restoration — Two-Tier Scan, Real YAML, `nosemgrep_hash` Suppression Parity
status: approved
effort: medium
branch: claude/review-spec-drafts-DX2pD
source_brief: .ai-engineering/specs/drafts/semgrep-pack-coverage-brief.md
target_dispatch: /ai-build
chains_after: spec-140
mantra: "Real syntax, real budget, real coverage — no invented YAML, no network on the hot path."
date_approved: 2026-05-16
auto_approved: true
auto_approval_reason: operator invoked --no-hitl autonomous run; smallest most-isolated spec in the batch; external research already settled the syntactical decisions
summary: Restore semgrep pack coverage via a two-tier scan model — pre-push runs only in-tree rules under 5 s; CI runs the four community packs (`p/python`, `p/owasp-top-ten`, `p/security-audit`, `p/bash`) via repeated `--config` flags (the canonical Semgrep multi-pack syntax); namespace the 9 in-tree rule IDs with `aieng.<area>.` prefix; add `nosemgrep_hash` to `.ai-engineering/suppression-allowlist.yml`; teach `no_suppression` module to recognise `# nosemgrep:` markers; rewrite `.ai-engineering/contexts/semgrep-update-model.md` to describe documented Semgrep syntax (no invented `extends:` / `@<version>` claims); add a drift regression test that forbids `extends:` or `@1.` patterns from re-entering the doc. Closes the silently-broken pack coverage that was lost in the dogfood-parity commit `3758d58a`.
---

# spec-141 — Semgrep Pack Coverage Restoration

> Mantra: **Real syntax, real budget, real coverage — no invented YAML, no network on the hot path.**

## Summary

The repo's semgrep posture is incoherent: `.ai-engineering/contexts/semgrep-update-model.md` documents an `extends:` block with `p/<name>@1.96.0` version pins — neither of which is valid Semgrep YAML. Git archaeology shows the `extends:` block was added in commit `b0cf6fe4` (2026-05-07) and removed five days later in `3758d58a` (2026-05-12) as a side-effect of the dogfood-parity commit. The removal was unintentional. The doc still describes the removed (and never-valid) syntax. The live `.semgrep.yml` and its template are byte-equivalent (sha256 `c35552d8f2bafcf5dfdf0ed1638a1331c3ec9078f96987b6ef20fafc8ad58a1a`) and carry only 9 hand-written Python rules. The `.ai-engineering/suppression-allowlist.yml` pattern enum lacks a `nosemgrep` family — every `# nosemgrep:` marker is invisible to the Article VII enforcement pipeline. This spec lands a single coherent two-tier scan model: pre-push runs only the 9 in-tree rules under the 5-second hot-path budget (with `--baseline-commit` for incremental scope); CI runs the four community packs via repeated `--config` flags (the canonical Semgrep multi-pack syntax); `# nosemgrep:` markers become first-class citizens of the allowlist + DEC pipeline; the in-tree rule IDs are namespaced with `aieng.<area>.` to prevent collisions with community-pack rule IDs; the doc is rewritten to describe documented Semgrep behaviour; a drift regression test forbids `extends:` and `@1.` patterns from re-entering the doc.

## Goals

1. **Pre-push gate ≤ 5 s.** On a 50-file representative diff on a clean clone, `.semgrep.yml` scan with `--baseline-commit $(git merge-base HEAD origin/main)` completes in ≤ 5 s.
2. **CI semgrep job ≤ 120 s.** `.github/workflows/ci-check.yml` runs `.semgrep.yml` + `p/python` + `p/owasp-top-ten` + `p/security-audit` + `p/bash` via repeated `--config` flags; total job wall-clock ≤ 120 s.
3. **Dogfood parity preserved.** Live `.semgrep.yml` and `src/ai_engineering/templates/project/.semgrep.yml` remain byte-equivalent (sha256 match per `tests/integration/test_dogfood_parity.py:41-77`).
4. **Rule IDs namespaced.** All 9 in-tree rule IDs carry the `aieng.<area>.` prefix.
5. **`nosemgrep_hash` in suppression allowlist.** Added to `.ai-engineering/suppression-allowlist.yml` pattern enum.
6. **`# nosemgrep:` markers DEC-enforced.** `no_suppression.cli.run_check` recognises the family and routes through the same Article VII allowlist + DEC pipeline as `# noqa` and `# nosec`.
7. **Doc rewritten.** `.ai-engineering/contexts/semgrep-update-model.md` references only documented Semgrep syntax (`--config`, vendoring, CLI version pin).
8. **Drift test added.** `tests/unit/contexts/test_semgrep_update_model_drift.py` fails if `extends:` or `@1.` patterns reappear in the doc.
9. **CHANGELOG entry under BREAKING — rule IDs.** Documents the rename mapping.

## Non-Goals

- Replacing Semgrep with another SAST tool.
- Adding JavaScript / TypeScript / Go / Rust packs (manifest declares `stacks: [python]` only).
- Authoring a custom community pack from scratch.
- Self-hosting a Semgrep registry mirror.
- Touching the gitleaks gate (separate posture).

## Decisions

- **D-141-01 — Vendor vs registry.** Registry with CLI version pin in CI workflow + GH Actions cache keyed by Semgrep CLI version. Resolves brief D-A.
  *Rationale*: vendoring adds repo weight (low single-digit MB per pack); registry keeps config small and pack updates flow through CLI upgrades.

- **D-141-02 — Registry failure policy.** Fail-closed (current Semgrep default, exit 2). CI badge surfaces "registry failure" distinctly from "real finding". Resolves brief D-B.
  *Rationale*: this is a security gate; transient outage is preferable to silently degraded coverage.

- **D-141-03 — Rule ID rename breaking surface.** Hard rename (CONSTITUTION.md §3); CHANGELOG under BREAKING documents the mapping. Resolves brief D-C.
  *Rationale*: no external consumer of these rule IDs is known; the rename is the only way to prevent silent dedup with community-pack rule IDs.

- **D-141-04 — Operator opt-in `--full` mode on pre-push.** No. Resolves brief D-D.
  *Rationale*: YAGNI — `ai-eng gate pre-push` exists for the default path; full-pack coverage is a CI responsibility per the two-tier model; operators wanting paranoid pre-push can invoke `semgrep --config p/python ...` directly.

- **D-141-05 — Quarterly bump cadence.** Manual via CHANGELOG-driven CLI version pin update. Resolves brief D-E.
  *Rationale*: dependabot's automatic PR cadence (weekly) is too aggressive for a security gate where every bump can surface findings that block PRs; quarterly manual triage is more sustainable.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tier-2 CI surfaces a flood of pack findings that block all PRs | High | High | Land Tier-2 in a separate commit AFTER triage; risk-accept the residue via `ai-eng risk accept` with proper DEC rows |
| Semgrep registry transient failure breaks CI | Medium | Medium | GH Actions cache; CI badge surfaces registry failure distinctly |
| Rule-ID collision after namespacing | Low | Low | Grep `semgrep/semgrep-rules` for any rule ID starting with `aieng.` — confirm none |
| `--baseline-commit` subtly skips checks on large diffs | Low | Medium | CI runs full unscoped scan anyway; pre-push is the convenience, CI is the authority |
| Doc rewrite introduces new claims that themselves drift | Low | Low | Drift regression test forbids `extends:` and `@1.` patterns |
| Semgrepignore v2 default (since v1.117.0) changes which files are scanned | Medium | Low | Compare scan target list between current and post-change CI runs |
| In-tree rule rename breaks an unknown downstream consumer | Low | Medium | CHANGELOG entry under BREAKING; ask in operator channel before merge |

## References

- doc: .ai-engineering/specs/drafts/semgrep-pack-coverage-brief.md
- doc: Semgrep "Run rules" — https://semgrep.dev/docs/running-rules
- doc: Semgrep CLI reference — https://semgrep.dev/docs/cli-reference
- doc: Offline cache request — https://github.com/semgrep/semgrep/issues/3147
- doc: OWASP Top 10 2025 coverage — https://semgrep.dev/blog/2026/owasp-top-10-2025-whats-new/
- doc: CONSTITUTION.md §13 hard rule #1 (secrets / SAST gate)
- doc: CLAUDE.md "Hot-Path Discipline" section
- doc: .ai-engineering/contexts/gate-policy.md

## Open Questions

None — all five D-* decisions in the brief are resolved as D-141-01 through D-141-05.
