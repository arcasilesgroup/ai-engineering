---
spec: spec-141
slug: semgrep-pack-coverage
title: Plan — Semgrep Pack Coverage Restoration
pipeline: build
phases: 5
status: approved
branch: claude/review-spec-drafts-DX2pD
date_approved: 2026-05-16
auto_approved: true
single_concern: true
---

# Plan — spec-141 Semgrep Pack Coverage Restoration

Five tight milestones; single PR scope; smallest and most isolated of the four specs in this run.

## Branch / PR

- Working branch: `claude/review-spec-drafts-DX2pD`
- Target: `main` via single PR carrying spec-138 + spec-139 + spec-140 + spec-141.

## Quality bar

- §10.1 KISS: shortest config that delivers; no invented YAML; one true syntax (repeated `--config`).
- §10.2 YAGNI: only Python-relevant packs (`manifest.yml:20` declares `stacks: [python]`).
- §10.5 TDD: drift regression test added BEFORE doc rewrite; rule-ID namespace test added BEFORE rename.
- §10.7 Clean Code: doc, config, and suppression allowlist all tell the same true story.

## Milestone M1 — In-tree rule ID namespacing + `--baseline-commit` on hot path

**Anchor:** §10.7 Clean Code; D-141-03.

### Tasks

- [ ] **M1.T1** — Rename all 9 in-tree rule IDs in `.semgrep.yml`:
  - `subprocess-shell-true` → `aieng.injection.subprocess-shell-true`
  - `eval-exec-usage` → `aieng.injection.eval-exec-usage`
  - `pickle-load` → `aieng.deserialize.pickle-load`
  - `yaml-load-unsafe` → `aieng.deserialize.yaml-load-unsafe`
  - `tempfile-mktemp` → `aieng.fs.tempfile-mktemp`
  - `requests-no-verify` → `aieng.net.requests-no-verify`
  - (verify remaining 3 in-tree rules and apply `aieng.<area>.` prefix)
- [ ] **M1.T2** — Re-render `src/ai_engineering/templates/project/.semgrep.yml` byte-equivalent (dogfood parity).
- [ ] **M1.T3** — `tests/integration/test_dogfood_parity.py:41-77` confirms sha256 match.
- [ ] **M1.T4** — Update `CheckConfig(name="semgrep", cmd=[...])` in `src/ai_engineering/policy/checks/stack_runner.py:209-213` to add `--baseline-commit $(git merge-base HEAD origin/<default-branch>)`.
- [ ] **M1.T5** — Add `tests/unit/policy/test_semgrep_baseline_arg.py` GREEN — asserts the baseline arg is present in the constructed cmd.
- [ ] **M1.T6** — Time the hot path on a 50-file diff: expected ≤ 5 s wall-clock.

## Milestone M2 — CI extension to full pack coverage

**Anchor:** §10.4 DRY; D-141-01; D-141-02.

### Tasks

- [ ] **M2.T1** — Update `.github/workflows/ci-check.yml:615-636` semgrep step:
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
- [ ] **M2.T2** — Pin Semgrep CLI version via `pip install semgrep==<version>` in the workflow install step.
- [ ] **M2.T3** — Cache registry-fetched pack YAML in GH Actions cache keyed by Semgrep CLI version.
- [ ] **M2.T4** — Verify CI job wall-clock ≤ 120 s end-to-end on this repo.
- [ ] **M2.T5** — `tests/unit/workflows/test_semgrep_packs.py` parses `ci-check.yml` and asserts the 4 `--config p/...` flags are present (drift gate).

## Milestone M3 — `nosemgrep_hash` suppression family

**Anchor:** CONSTITUTION.md Article VII parity.

### Tasks

- [ ] **M3.T1** — Add `nosemgrep_hash` to `.ai-engineering/suppression-allowlist.yml:22-26` pattern enum.
- [ ] **M3.T2** — Teach `no_suppression.cli.run_check` (called from `cli_commands/gate.py:130-164`) to recognise `# nosemgrep:` markers.
- [ ] **M3.T3** — `tests/unit/no_suppression/test_nosemgrep_recognition.py` GREEN — covers happy path + DEC-linked path.

## Milestone M4 — Doc rewrite + drift regression test

**Anchor:** §10.5 TDD (test FIRST); §10.7 Clean Code.

### Tasks

- [ ] **M4.T1** — Add `tests/unit/contexts/test_semgrep_update_model_drift.py` FIRST (RED):
  ```python
  def test_no_extends_block():
      content = Path(".ai-engineering/contexts/semgrep-update-model.md").read_text()
      assert "extends:" not in content
      assert "@1." not in content  # forbids the @<version> pack pin pattern
  ```
- [ ] **M4.T2** — Rewrite `.ai-engineering/contexts/semgrep-update-model.md`:
  - Replace "extends with `@<version>` pins" model with "repeated `--config` flags + pinned Semgrep CLI".
  - Quarterly bump procedure: bump `semgrep` CLI pin in `ci-check.yml`, re-run gate, triage findings (D-141-05).
  - Reproducibility: pack aliases roll forward from HEAD; deterministic anchor is the CLI pin.
  - Advisory section: pre-push deliberately does NOT run packs (5-second budget); full coverage is CI-only.
- [ ] **M4.T3** — Confirm `test_semgrep_update_model_drift.py` GREEN after rewrite.

## Milestone M5 — Triage of CI findings + CHANGELOG

**Anchor:** CONSTITUTION.md §13 secrets-gate hard rule.

### Tasks

- [ ] **M5.T1** — Run CI with the new pack invocation; capture findings. (Deferred — depends on first post-merge CI run.)
- [ ] **M5.T2** — Triage each new finding: fix inline OR risk-accept via `ai-eng risk accept --finding-id <ID>`. (Deferred — pending M5.T1 output.)
- [x] **M5.T3** — CHANGELOG entry under `## [Unreleased] ### BREAKING CHANGES`: nine rule-ID renames consolidated under `#### BREAKING CHANGES — spec-141 D-141-04 in-tree rule ID rename (M1)` at `CHANGELOG.md:942-963`.
- [x] **M5.T4** — CHANGELOG under `### Added`: `# nosemgrep:` Article-VII parity consolidated under `#### Added — # nosemgrep: suppression Article VII parity (M3)` at `CHANGELOG.md:1001-1010`.
- [x] **M5.T5** — CHANGELOG under `### Changed`: CI semgrep job invocation consolidated under `#### Changed — CI semgrep job now runs four community packs (M2)` at `CHANGELOG.md:981-999`.
- [x] **M5.T6** — CHANGELOG under `### Fixed`: `semgrep-update-model.md` rewrite consolidated under `#### Fixed — semgrep-update-model.md invented-YAML drift (M4)` at `CHANGELOG.md:1012-1020`.

## Cross-spec coordination

- **spec-138 dependency.** None.
- **spec-139 dependency.** None.
- **spec-140 dependency.** Wave 2 may extract `setup-env` composite action; this spec's M2 modifies the semgrep step inside `ci-check.yml`. Order: do this spec FIRST (M2 edits inline step), then spec-140 Wave 2 abstracts the wrapping (both compatible).

## Single-concern envelope

This plan satisfies the `/ai-build --no-hitl` single-concern gate: single PR scope, one concern (semgrep pack coverage restoration), no `## Task Group` headings (only `## Milestone`).
