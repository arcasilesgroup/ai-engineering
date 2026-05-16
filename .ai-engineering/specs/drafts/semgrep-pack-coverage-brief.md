---
title: Semgrep Pack Coverage Restoration
status: draft
audience: framework-dev
branch: spec-128/context-overrides-refactor
length_estimate: medium (single spec, single PR, 6-8 files touched)
authoring_style: spec brief — diagnostic + architecture + open decisions
principles_required:
  - "§10.1 KISS (smallest config that delivers; no invented syntax)"
  - "§10.2 YAGNI (only Python-relevant packs — manifest.yml stack is python-only)"
  - "§10.5 TDD (regression test forbids invented YAML reappearing in doc)"
  - "§10.7 Clean Code (config + doc + suppression-allowlist tell the same true story)"
delivery_mode: single-PR
mantra: "Real syntax, real budget, real coverage — no invented YAML, no network on the hot path."
---

# Semgrep Pack Coverage Restoration — Brief

> **Status:** Draft brief, ready for `/ai-brainstorm` → `/ai-plan`.
> **Branch:** `spec-128/context-overrides-refactor` (current; brief lands as a separate spec).
> **Origin:** Operator triage on 2026-05-16 surfaced that `.ai-engineering/contexts/semgrep-update-model.md` documents pack-extending behaviour that the live `.semgrep.yml` no longer carries — and external research revealed the documented syntax was never real Semgrep YAML.
> **North Star:** A pre-push gate that catches what Semgrep actually catches today, runs in under 5 seconds on the hot path, runs full community-pack coverage in CI, and whose config + doc + suppression-allowlist tell the same true story.

---

## 1. Vision

The semgrep posture of this repository is **honest**: every claim in `.ai-engineering/contexts/semgrep-update-model.md` corresponds to a documented Semgrep behaviour; every rule in `.semgrep.yml` runs on the pre-push hot path inside the 5-second SLO; every community-pack rule (`p/python`, `p/owasp-top-ten`, `p/security-audit`, `p/bash`) runs in CI as a backstop and contributes to gate verdict; every `# nosemgrep:` marker in code routes through the same allowlist + DEC pipeline as `# noqa` and `# nosec`. There is one config format, one doc, one allowlist enum — all aligned with the upstream Semgrep contract.

## 2. Scope Boundary

**IN scope:**

- Re-architect Semgrep invocation into two tiers: pre-push (hot, narrow, in-tree rules only) and CI (cold, full, community packs).
- Rewrite `.semgrep.yml` (live + template) using real Semgrep syntax (no `extends:`, no `@<version>` pack pinning).
- Extend `.github/workflows/ci-check.yml` to run repeated `--config p/...` flags for full pack coverage.
- Add a `nosemgrep_hash` pattern family to `.ai-engineering/suppression-allowlist.yml` and teach the `no_suppression` module to recognise `# nosemgrep:` markers.
- Rewrite `.ai-engineering/contexts/semgrep-update-model.md` to describe documented Semgrep behaviour, not invented syntax.
- Namespace the 9 in-tree rules with an `aieng.<area>.` prefix to prevent collisions with community-pack rule IDs.
- Add a doc-drift regression test that fails if the forbidden patterns (`extends:`, `@1.`) reappear in `semgrep-update-model.md`.

**OUT of scope:**

- Replacing Semgrep with another SAST tool.
- Adding JavaScript / TypeScript / Go / Rust packs (the manifest declares `stacks: [python]` only).
- Authoring a custom community pack from scratch.
- Self-hosting a Semgrep registry mirror.
- Touching the gitleaks gate (separate posture).

## 3. Diagnostic Snapshot

Codebase state confirmed via the parallel research dispatch:

- `.semgrep.yml:1-138` and `src/ai_engineering/templates/project/.semgrep.yml:1-138` are byte-equivalent (sha256 `c35552d8f2bafcf5dfdf0ed1638a1331c3ec9078f96987b6ef20fafc8ad58a1a`); both contain 9 hand-written Python rules and **no `extends:` block**.
- `tests/integration/test_dogfood_parity.py:41-77` enforces sha256 byte-equivalence between live and template. The semgrep pair is registered at line 45.
- Pre-push gate runs `semgrep --config .semgrep.yml --error .` via `CheckConfig(name="semgrep", cmd=[...])` at `src/ai_engineering/policy/checks/stack_runner.py:209-213`, registered under the `"common"` stack key (runs regardless of language stack).
- Gate dispatch path: `.git/hooks/pre-push` → `ai-eng gate pre-push` → `src/ai_engineering/cli_commands/gate.py:118-127` → `src/ai_engineering/policy/gates.py:320-347`.
- CI backstop: `.github/workflows/ci-check.yml:615-636` reruns the identical command and adds a 50% skip-ratio sanity check. No other workflow references semgrep.
- Hot-path budget: pre-push under 5 seconds per `CLAUDE.md` "Hot-Path Discipline" section. `.ai-engineering/contexts/gate-policy.md:53` records that full-source semgrep "needs holding 30+ s" — confirming any naïve pack invocation will blow the budget.
- `.ai-engineering/contexts/semgrep-update-model.md:10-18` documents an `extends:` block with `p/<name>@1.96.0` pins.
- Git archaeology: `extends:` was **added** in commit `b0cf6fe4` (2026-05-07) and **removed** in commit `3758d58a` (2026-05-12, 5 days later) as a side-effect of the dogfood-parity commit. The removal was an unintentional regression — not a deliberate policy decision.
- Risk-acceptance gap: `.ai-engineering/suppression-allowlist.yml:22-26` pattern enum is `nosonar | noqa | nosec | type_ignore | pragma_no_cover | ts_ignore | nolint_hash | nolint_slash | eslint_disable_hash | eslint_disable_slash | sonar_multicriteria` — **`nosemgrep` is absent**. Today, a `# nosemgrep:` marker is invisible to the Article VII enforcement pipeline.
- Stack coverage: `.ai-engineering/manifest.yml:20` declares `stacks: [python]`. No JS, TS, or other languages are wired.

External research delivered three structural corrections to the prior framing:

- `extends:` is **not** a documented Semgrep top-level YAML key. The canonical mechanism for combining packs is **repeated `--config` flags** (https://semgrep.dev/docs/running-rules) or a multi-document YAML at a URL.
- Pack version pinning like `p/python@1.96.0` is **not** documented Semgrep syntax. Pack aliases resolve to the live HEAD of `semgrep/semgrep-rules`; reproducibility requires either pinning the Semgrep CLI version or vendoring the pack YAML into the repo (https://semgrep.dev/docs/cli-reference).
- No first-class offline cache for registry packs as of 2026-05; issue https://github.com/semgrep/semgrep/issues/3147 remains open. On registry-unreachable, Semgrep exits 2 (fail-closed).

The "1.96.0" version cited in the legacy `extends:` and in `semgrep-update-model.md` almost certainly referred to a Semgrep CLI release, not a pack version — meaning the prior config was either silently ignored by Semgrep or did partial work the maintainer believed was correct.

## 4. Architecture

**Two-tier scan model.**

**Tier 1 — Pre-push (hot path).** `.semgrep.yml` continues to host only the 9 in-tree rules. The CheckConfig at `stack_runner.py:209-213` adds `--baseline-commit $(git merge-base HEAD origin/<default-branch>)` so the scan covers only files changed since the merge base. Network-free, deterministic, expected wall-clock under 5 seconds. The 9 in-tree rule IDs are renamed with an `aieng.<area>.` prefix (for example, `subprocess-shell-true` becomes `aieng.injection.subprocess-shell-true`) to eliminate the rule-ID collision risk surfaced by external research — pack rules with matching IDs would silently dedup against in-tree rules with no warning.

**Tier 2 — CI (full coverage backstop).** `.github/workflows/ci-check.yml:615-636` updates the invocation to use repeated `--config` flags — the documented Semgrep syntax for combining packs:

```yaml
- name: semgrep
  run: |
    semgrep \
      --config .semgrep.yml \
      --config p/python \
      --config p/owasp-top-ten \
      --config p/security-audit \
      --config p/bash \
      --error --json . > semgrep-results.json
```

Pin the Semgrep CLI version via `pip install semgrep==<version>` in the workflow's install step so the gate is reproducible across runs (since pack aliases roll forward from HEAD). Cache the registry-fetched pack YAML in the GH Actions cache keyed by the Semgrep CLI version to soften transient registry failures.

**Suppression integration.** Add `nosemgrep_hash` to the pattern enum at `.ai-engineering/suppression-allowlist.yml:22-26`. The `no_suppression.cli.run_check` function (called from `cli_commands/gate.py:130-164`) learns the new family. `# nosemgrep:` markers in code become first-class citizens of the Article VII allowlist + DEC pipeline, on par with `# noqa` and `# nosec`.

**Doc rewrite.** `.ai-engineering/contexts/semgrep-update-model.md` is rewritten to describe **documented** Semgrep behaviour:

- The "extends with `@<version>` pins" model is replaced with "repeated `--config` flags + pinned Semgrep CLI".
- Quarterly bump procedure becomes "bump the `semgrep` CLI pin in `ci-check.yml`, re-run gate, triage findings".
- Reproducibility section honestly explains that pack aliases roll forward from HEAD and the only deterministic anchor is the CLI pin (plus, optionally, vendored pack snapshots).
- An advisory section documents that pre-push deliberately does **not** run the packs because of the 5-second budget; full coverage is CI-only.

**Dogfood parity.** Live `.semgrep.yml` and `src/ai_engineering/templates/project/.semgrep.yml` remain byte-equivalent. The dogfood parity test at `tests/integration/test_dogfood_parity.py:41-77` continues to enforce sha256 match — no special-casing needed.

## 5. Evidence Catalog

| Claim | Citation |
|-------|----------|
| 9 in-tree rules, no `extends:` block | `.semgrep.yml:1-138` |
| Template byte-equivalent to live | `src/ai_engineering/templates/project/.semgrep.yml:1-138` |
| Dogfood parity test enforces sha256 | `tests/integration/test_dogfood_parity.py:41-77` |
| Pre-push CheckConfig invocation | `src/ai_engineering/policy/checks/stack_runner.py:209-213` |
| Gate CLI entry point | `src/ai_engineering/cli_commands/gate.py:118-127` |
| Pre-push checks runner | `src/ai_engineering/policy/gates.py:320-347` |
| Article VII enforcement integration | `src/ai_engineering/cli_commands/gate.py:130-164` |
| CI backstop step | `.github/workflows/ci-check.yml:615-636` |
| Pre-push hot-path budget | `CLAUDE.md` "Hot-Path Discipline" section |
| 30+ second full-source cost | `.ai-engineering/contexts/gate-policy.md:53` |
| Invented `extends:` model in doc | `.ai-engineering/contexts/semgrep-update-model.md:10-18` |
| `extends:` added in `b0cf6fe4` | git log 2026-05-07 |
| `extends:` removed in `3758d58a` | git log 2026-05-12 |
| Missing `nosemgrep` in suppression enum | `.ai-engineering/suppression-allowlist.yml:22-26` |
| Stack manifest is python-only | `.ai-engineering/manifest.yml:20` |
| Semgrep canonical multi-pack syntax | https://semgrep.dev/docs/running-rules |
| Pack `@version` pinning not documented | https://semgrep.dev/docs/cli-reference |
| No offline cache for packs | https://github.com/semgrep/semgrep/issues/3147 |
| Registry fail-closed exit 2 | https://semgrep.dev/docs/cli-reference |
| Pre-push 8-25s with packs benchmark | https://semgrep.dev/blog/2025/benchmarking-semgrep-performance-improvements/ |
| OWASP Top 10 2025 coverage in `p/owasp-top-ten` | https://semgrep.dev/blog/2026/owasp-top-10-2025-whats-new/ |
| Semgrepignore v2 default since v1.117.0 | https://raw.githubusercontent.com/semgrep/semgrep/develop/CHANGELOG.md |

## 6. Roadmap

| M | Title | Acceptance Gate |
|---|-------|------------------|
| M1 | In-tree rule ID namespacing + `--baseline-commit` on hot path | `.semgrep.yml` and template carry `aieng.<area>.` IDs; CheckConfig runs in under 5 seconds on a 50-file diff. |
| M2 | CI extension to full pack coverage with repeated `--config` flags | `ci-check.yml` semgrep job runs all 4 packs; CLI pin documented; job under 120 seconds end-to-end on this repo. |
| M3 | `nosemgrep_hash` suppression family | `suppression-allowlist.yml` enum extended; `no_suppression.cli.run_check` recognises `# nosemgrep:` markers; unit test covers happy + DEC-linked paths. |
| M4 | `semgrep-update-model.md` rewrite + drift regression test | Doc references only documented Semgrep syntax; new test fails if `extends:` or `@1.` patterns reappear in the doc. |
| M5 | Triage of CI findings from M2's first run | Each new finding either fixed inline or risk-accepted via `ai-eng risk accept`; CI green; CHANGELOG entry for rule-ID rename. |

## 7. Definition of Done

- Pre-push gate timed at 5 seconds or less on a clean clone of this repo with a representative 50-file diff.
- CI semgrep job runs all four community packs and the in-tree rules within 120 seconds.
- `# nosemgrep:` markers in code resolve through `no_suppression.run_check` to DEC rows in `state.db` decisions table.
- `.ai-engineering/contexts/semgrep-update-model.md` references only documented Semgrep syntax (`--config`, vendoring, CLI version pin). No `extends:` block, no `@<version>` pack pin claims.
- Dogfood parity test green: live and template `.semgrep.yml` byte-equivalent.
- All 9 in-tree rule IDs carry the `aieng.<area>.` prefix.
- A new test at `tests/unit/contexts/test_semgrep_update_model_drift.py` (or similar) fails if `extends:` or `@1.` patterns reappear in `semgrep-update-model.md`.
- CHANGELOG entry under "BREAKING — rule IDs" documents the in-tree rule rename.
- All Open Decisions (§9) resolved during `/ai-brainstorm`.

## 8. Quality Stamps

- **§10.1 KISS** — shortest config that delivers coverage; no invented YAML; one true syntax (repeated `--config`).
- **§10.2 YAGNI** — only Python-relevant packs (`manifest.yml:20` declares `stacks: [python]`); no speculative JS / TS / Rust packs.
- **§10.5 TDD** — drift regression test added before doc rewrite; rule-ID namespace test added before rename.
- **§10.7 Clean Code** — doc, config, and suppression allowlist all tell the same true story.
- **Hot-Path Discipline (CLAUDE.md)** — pre-push under 5 seconds preserved; full coverage moved to CI per the documented two-tier model.
- **CONSTITUTION.md §13 hard rule #1** — secrets / SAST gate continues to BLOCK at CRITICAL / HIGH / MEDIUM; risk acceptance flows through `ai-eng risk accept`.
- **CONSTITUTION.md Article VII** — `nosemgrep` markers now allowlist-enforceable, on par with `noqa` and `nosec`.

## 9. Open Decisions

- **D-A — Vendor vs registry.** Vendor the four community packs (commit YAML snapshots into `.semgrep/vendor/`) for full offline determinism, or rely on the Semgrep registry with a CLI version pin and GH Actions cache? Trade-off: vendoring adds repo weight (low single-digit MB per pack) but removes network dependency entirely; registry keeps the config small but stays exposed to fail-closed registry failures.
- **D-B — Registry failure policy.** When CI registry fetch fails, should the build fail (current Semgrep default, exit 2) or warn-and-continue with a one-day grace window? Lean toward fail-closed since this is a security gate, but a transient outage on a Friday could block legitimate merges.
- **D-C — Rule ID rename breaking-change surface.** The 9 in-tree rule IDs are renamed with `aieng.<area>.` prefix. Are there any external consumers (downstream forks, internal reporting dashboards) reading these IDs? Probably none, but worth a stated check before the rename.
- **D-D — Operator opt-in `--full` mode on pre-push.** Should `ai-eng gate pre-push --full` exist as an opt-in flag that runs the packs locally (paying the 8-25 second cost) for paranoid pre-push runs?
- **D-E — Quarterly bump cadence.** Keep manual (per current doc) or wire `dependabot.yml` to automatically open a PR bumping the Semgrep CLI pin?

## 10. Migration

Per CONSTITUTION.md §3 (no backwards-compat shims), the rule-ID rename is a **hard rename**: `subprocess-shell-true` → `aieng.injection.subprocess-shell-true` with no alias. A CHANGELOG entry under "BREAKING — rule IDs" documents the renamed mapping so any external consumer (CI dashboard, fork, internal pipeline) can update their references.

`.ai-engineering/suppression-allowlist.yml` gains one enum value (`nosemgrep_hash`). Existing allowlist entries are unaffected — schema is additive.

`.semgrep.yml` top-level format is unchanged: still `rules:`, no `extends:`. The CI invocation pattern changes but the file format does not, so external tooling that reads `.semgrep.yml` directly continues to work.

`.ai-engineering/contexts/semgrep-update-model.md` is rewritten in place — no backwards-compat preamble, no "this section was renamed" callouts.

## 11. Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Tier-2 CI surfaces a flood of pack findings that block all PRs | High | High | Land Tier-2 in a separate PR after triage; risk-accept the residue with proper DEC rows; consider a one-time "ratchet" allowlist with explicit DEC IDs. |
| Semgrep registry transient failure breaks CI | Medium | Medium | GH Actions cache; D-B grace-window decision; CI badge that surfaces "registry failure" distinctly from "real finding". |
| Rule-ID collision after namespacing | Low | Low | Grep `semgrep/semgrep-rules` for any rule whose ID starts with `aieng.` — confirm none. |
| `--baseline-commit` subtly skips checks on large diffs | Low | Medium | CI runs full unscoped scan anyway; pre-push is the convenience, CI is the authority. |
| Doc rewrite introduces new claims that themselves drift | Low | Low | Drift regression test in M4 forbids `extends:` and `@1.` patterns from re-entering the doc. |
| Semgrepignore v2 default (since v1.117.0) changes which files are scanned vs prior config | Medium | Low | Compare scan target list between current and post-change CI runs; document any intentional inclusions / exclusions in `.semgrepignore`. |
| In-tree rule rename breaks a downstream consumer we don't know about | Low | Medium | CHANGELOG entry under BREAKING; ask in operator channel before merge. |

## 12. References

- Semgrep "Run rules" docs (canonical multi-pack syntax): https://semgrep.dev/docs/running-rules
- Semgrep CLI reference: https://semgrep.dev/docs/cli-reference
- Semgrep release notes: https://semgrep.dev/docs/release-notes
- Semgrep April 2026 release notes: https://semgrep.dev/docs/release-notes/april-2026
- Semgrep changelog (raw): https://raw.githubusercontent.com/semgrep/semgrep/develop/CHANGELOG.md
- Semgrep benchmark (2025): https://semgrep.dev/blog/2025/benchmarking-semgrep-performance-improvements/
- OWASP Top 10 2025 in `p/owasp-top-ten`: https://semgrep.dev/blog/2026/owasp-top-10-2025-whats-new/
- Offline cache request: https://github.com/semgrep/semgrep/issues/3147
- Semgrep deployment / tokens: https://semgrep.dev/docs/deployment/tokens
- Semgrep authentication (DeepWiki): https://deepwiki.com/semgrep/semgrep/4.6-authentication-and-settings
- `semgrep-rules` Python tree: https://github.com/semgrep/semgrep-rules/tree/develop/python
- Registry Python ruleset: https://registry.semgrep.dev/ruleset/python
- CONSTITUTION.md §13 (hard rules — secrets gate)
- CLAUDE.md "Hot-Path Discipline" section
- `.ai-engineering/contexts/gate-policy.md` (gate policy reference)

## 13. Glossary

- **Pack** — a Semgrep community rule alias (`p/<name>`). Resolves at runtime from HEAD of `semgrep/semgrep-rules`. Not version-pinnable via Semgrep syntax; reproducibility comes from pinning the Semgrep CLI or vendoring the pack YAML.
- **Tier-1 / Tier-2 scan** — this brief's terminology for the pre-push (hot, narrow, in-tree) versus CI (cold, full, networked) Semgrep invocations.
- **Vendoring** — committing a snapshot of upstream rule YAML into the repository (for example, at `.semgrep/vendor/`) for pinned reproducibility without runtime network dependency.
- **`--baseline-commit`** — Semgrep flag that scopes the scan to files changed since a given git ref, enabling fast incremental scans on the hot path.
- **`nosemgrep_hash`** — proposed new entry in `.ai-engineering/suppression-allowlist.yml` pattern enum, covering the `# nosemgrep:` marker convention.
- **Article VII** — CONSTITUTION.md article governing suppression-marker policy; this brief brings `nosemgrep` markers into Article VII parity with `noqa` / `nosec`.

## 14. Acceptance

- [ ] Pre-push gate timed at 5 seconds or less on a clean clone with a representative 50-file diff.
- [ ] CI semgrep job runs the four community packs plus the in-tree rules in 120 seconds or less.
- [ ] `.semgrep.yml` live and template files remain byte-equivalent (sha256 match per `tests/integration/test_dogfood_parity.py:41-77`).
- [ ] All 9 in-tree rule IDs carry the `aieng.<area>.` prefix.
- [ ] `nosemgrep_hash` entry added to `.ai-engineering/suppression-allowlist.yml` pattern enum.
- [ ] `no_suppression.cli.run_check` recognises `# nosemgrep:` markers in code.
- [ ] `.ai-engineering/contexts/semgrep-update-model.md` rewritten — references only documented Semgrep syntax.
- [ ] Doc-drift regression test added — fails on `extends:` or `@1.` reintroduction.
- [ ] CHANGELOG entry under BREAKING — rule IDs.
- [ ] CI green: dogfood parity, gate flow, unit + integration tests, semgrep itself.
- [ ] All Open Decisions (§9 A through E) resolved by `/ai-brainstorm`.
- [ ] PR description links this brief.
