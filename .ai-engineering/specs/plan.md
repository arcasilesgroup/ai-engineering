# Plan: spec-097 CI/CD Redesign — DevSecOps, Supply Chain Security, Artifact-Driven Releases

## Pipeline: full
## Phases: 6
## Tasks: 38 (build: 28, verify: 10)

---

### Phase 1: GitHub Hardening
**Gate**: All settings verified via `gh api` — branch protection, tag protection, environment restrictions, Actions allowlist applied. No workflow changes.

- [ ] T-1.1: Configure branch protection on main — 1 required approval, code owner review required, dismiss stale reviews, last-push approval, enforce for admins (agent: build)
- [ ] T-1.2: Create tag protection ruleset — `v*` pattern restricted to maintainers only (agent: build)
- [ ] T-1.3: Configure PyPI environment — branch restriction to main only, disable admin bypass (agent: build)
- [ ] T-1.4: Configure Actions allowlist — restrict to `actions/*`, `github/*`, `pypa/*`, `astral-sh/*`, `SonarSource/*`, `CycloneDX/*`, `EndBug/*`, `dorny/*` (agent: build)
- [ ] T-1.5: Rotate or delete expired WIKI_PAT secret (expired 2026-02-05) (agent: build)
- [ ] T-1.6: Verify all settings — run `gh api` checks for branch protection, tag ruleset, environment config, and Actions permissions; confirm all match spec (agent: verify)

### Phase 2: Split ci.yml into ci-check.yml + ci-build.yml
**Gate**: ci-check.yml runs on PR with all validation jobs + dry build. ci-build.yml triggers via workflow_run on ci-check success on main. Old ci.yml retained but deprecated. release.yml updated to reference ci-check. All workflows pass `check_workflow_policy.py`.

- [ ] T-2.1: Create `ci-check.yml` — extract all validation jobs from ci.yml (change-scope, lint, duplication, risk-acceptance, typecheck, test-unit, test-integration, test-e2e, sonarcloud, framework-smoke, security, snyk-security, workflow-sanity, verify-gate-trailers, content-integrity). Triggers: `pull_request` to main + `push` to main. Include concurrency, permissions, path-ignore from current ci.yml (agent: build)
- [ ] T-2.2: Add `build-check` job to ci-check.yml — runs `uv build` without `upload-artifact`. Conditional on `change-scope.outputs.code == 'true'`. Depends on all validation jobs (agent: build)
- [ ] T-2.3: Add `ci-check-result` aggregation job to ci-check.yml — adapts current ci-result logic. Treats `build-check` as code-conditional (skipped = OK when no code changes). Does NOT include the old `build` job (agent: build)
- [ ] T-2.4: Create `ci-build.yml` — triggers on `workflow_run` for ci-check completion on main with success conclusion. Uses `github.event.workflow_run.head_sha` for checkout. Jobs: build (`uv build`), upload artifact (90-day retention). Add top-level permissions, timeout-minutes, no concurrency needed (single-fire per ci-check) (agent: build)
- [ ] T-2.5: Update `release.yml` verify-ci job — change workflow reference from `ci.yml` to `ci-check` in `gh run list --workflow=` command. Ensures release still works during transition (agent: build)
- [ ] T-2.6: Update `scripts/check_workflow_policy.py` — add `"github/"`, `"pypa/"`, `"astral-sh/"`, `"SonarSource/"`, `"CycloneDX/"`, `"EndBug/"`, `"dorny/"` to `_FIRST_PARTY_PREFIXES` tuple (agent: build)
- [ ] T-2.7: Update branch protection required status checks — change from `CI Result` to `ci-check-result` (or equivalent job name). Use `gh api` to update (agent: build)
- [ ] T-2.8: Add deprecation comment to top of ci.yml — `# DEPRECATED: This workflow is retained for transition. See ci-check.yml and ci-build.yml. Will be deleted in Phase 6.` Disable ci.yml triggers (set to `workflow_dispatch` only to prevent duplicate runs) (agent: build)
- [ ] T-2.9: Verify ci-check.yml and ci-build.yml pass `check_workflow_policy.py` — run `python scripts/check_workflow_policy.py` (agent: verify)
- [ ] T-2.10: Verify workflow triggers — confirm ci-check runs on PR events, ci-build does NOT run on PR events, build-check produces no artifacts (agent: verify)

### Phase 3: Semantic Release + Conventional Commits
**Gate**: python-semantic-release configured. `__version__.py` eliminated. commit-msg gate accepts both formats. `/ai-commit` generates conventional format. All tests pass.

- [ ] T-3.1: Configure python-semantic-release in `pyproject.toml` — add `[tool.semantic_release]` section with `version_toml`, commit parser config, branch config, changelog generation disabled (CHANGELOG is manual), tag format `v{version}` (agent: build)
- [ ] T-3.2: Eliminate `__version__.py` — delete `src/ai_engineering/__version__.py`. Update `src/ai_engineering/__init__.py` to use `importlib.metadata.version("ai-engineering")` with fallback for editable installs (agent: build)
- [ ] T-3.3: Update all `__version__` imports — fix `cli_ui.py`, `cli_commands/core.py`, `cli_factory.py`, `doctor/runtime/version.py`, `policy/checks/branch_protection.py` to use the new `__init__.py` re-export or `importlib.metadata` directly (agent: build)
- [ ] T-3.4: Update `release/version_bump.py` — remove `_find_version_file()` and `__version__.py` update logic from `bump_python_version()`. Only update `pyproject.toml`. Update `detect_current_version()` to use `importlib.metadata` as primary source (agent: build)
- [ ] T-3.5: Update `release/orchestrator.py` — remove `__version__.py` references from prepare phase. Ensure `bump_python_version()` call still works with single-file update (agent: build)
- [ ] T-3.6: Update `policy/checks/commit_msg.py` — add acceptance of conventional commit format (`type(scope): description`) alongside legacy `spec-NNN:` format during transition. Both formats pass validation (agent: build)
- [ ] T-3.7: Update `/ai-commit` SKILL.md — change commit format instructions from `spec-NNN: Task X.Y -- description` to `feat(spec-NNN): description`, `fix(scope): description`, `chore: description`. Remove legacy format documentation (agent: build)
- [ ] T-3.8: Update `/ai-pr` SKILL.md — change PR title format from `spec-NNN: title` to `feat(spec-NNN): title`. Update `pr_description.py` `build_pr_title()` to generate conventional format (agent: build)
- [ ] T-3.9: Sync skill mirrors — run `python scripts/sync_command_mirrors.py` to propagate ai-commit and ai-pr changes to `.gemini/`, `.codex/`, `.github/` mirrors (agent: build)
- [ ] T-3.10: Integrate semantic-release into ci-build.yml — add semantic-release step after build: analyze commits, determine bump, create tag if bump needed, create draft GitHub Release with dist artifacts attached. If no bump, skip tag/release/artifact-upload (agent: build)
- [ ] T-3.11: Write tests for updated commit_msg.py — test both legacy and conventional format acceptance. Test that invalid formats still fail (agent: build)
- [ ] T-3.12: Write tests for updated version detection — test `importlib.metadata` path and editable-install fallback. Update existing test_version_bump.py for single-file bump (agent: build)
- [ ] T-3.13: Verify all tests pass — run `pytest` full suite. Verify `ruff check` and `ty check src/` clean (agent: verify)
- [ ] T-3.14: Verify semantic-release dry-run — run `semantic-release --dry-run` to confirm commit parsing and version detection work correctly with the project's commit history (agent: verify)

### Phase 4: Supply Chain Security (SLSA + SBOM + Checksums)
**Gate**: ci-build produces SLSA attestation, CycloneDX SBOM, and SHA-256 checksums alongside dist artifacts. All attached to draft GitHub Release. Attestation verifiable via `gh attestation verify`.

- [ ] T-4.1: Add `actions/attest-build-provenance` to ci-build.yml — place in same job as `uv build`, after build step. Configure `subject-path: 'dist/*'`. Requires `id-token: write` and `attestations: write` permissions (agent: build)
- [ ] T-4.2: Add CycloneDX SBOM generation to ci-build.yml — use `CycloneDX/gh-python-generate-sbom` or `pip install cyclonedx-bom && cyclonedx-py`. Output to `sbom.json`. Upload as artifact alongside dist (agent: build)
- [ ] T-4.3: Add SHA-256 checksum generation to ci-build.yml — `cd dist && sha256sum * > CHECKSUMS-SHA256.txt`. Upload CHECKSUMS-SHA256.txt as artifact (agent: build)
- [ ] T-4.4: Attach SBOM and checksums to draft GitHub Release — in the semantic-release draft step, include `sbom.json` and `CHECKSUMS-SHA256.txt` as release assets alongside dist files (agent: build)
- [ ] T-4.5: Verify ci-build.yml passes `check_workflow_policy.py` after additions (agent: verify)
- [ ] T-4.6: Verify attestation — after a test build on main, run `gh attestation verify` on the produced artifact to confirm SLSA provenance is valid (agent: verify)

### Phase 5: Release Redesign (workflow_dispatch)
**Gate**: New release.yml works as `workflow_dispatch` with version input (default: latest). Resolves version, validates CHANGELOG, downloads artifact, publishes to PyPI, finalizes GitHub Release. Old tag-triggered release.yml replaced.

- [ ] T-5.1: Rewrite `release.yml` trigger — change from `on: push: tags: ["v*"]` to `on: workflow_dispatch` with input `version` (type: string, description: "Version to release (e.g., v0.2.0). Leave empty for latest.", default: "") (agent: build)
- [ ] T-5.2: Add version resolution job — if input empty, find latest tag via `git tag --sort=-v:refname | head -1`. Verify tag exists. Verify matching ci-build artifact exists (search by tag SHA). Output resolved version and ci-build run-id (agent: build)
- [ ] T-5.3: Add CHANGELOG validation job — extract `VERSION` from resolved tag (`v0.2.0` → `0.2.0`). Verify `## [VERSION]` section exists in CHANGELOG.md via `awk`. Fail with clear error if missing (agent: build)
- [ ] T-5.4: Add PyPI publish job — download dist artifact from ci-build run-id. Verify dist/ not empty. Publish via `pypa/gh-action-pypi-publish` with OIDC (`id-token: write`). Environment: `pypi` with `url: https://pypi.org/project/ai-engineering/` (agent: build)
- [ ] T-5.5: Add GitHub Release finalization job — find draft release matching version tag. Update from draft to published. Attach release notes extracted from CHANGELOG. Ensure SBOM, CHECKSUMS, and dist files are already attached from ci-build draft (agent: build)
- [ ] T-5.6: Verify release.yml passes `check_workflow_policy.py` (agent: verify)
- [ ] T-5.7: Verify end-to-end release flow — trace the full path: ci-build draft exists → workflow_dispatch → version resolved → CHANGELOG validated → PyPI publish → GitHub Release finalized. Document the verification (agent: verify)

### Phase 6: Cleanup + Documentation
**Gate**: Old ci.yml deleted. Legacy commit format removed from gate. Decisions persisted. CHANGELOG updated. All workflows pass policy. All tests pass.

- [ ] T-6.1: Delete deprecated `ci.yml` — remove `.github/workflows/ci.yml` entirely (agent: build)
- [ ] T-6.2: Remove legacy commit format from `commit_msg.py` — remove `spec-NNN:` acceptance, keep only conventional commit format validation (agent: build)
- [ ] T-6.3: Add decisions D-097-01 through D-097-12 to `state/decision-store.json` — mark DEC-012 as superseded by D-097-04, mark DEC-015 as superseded by D-097-03 (agent: build)
- [ ] T-6.4: Update CHANGELOG.md with spec-097 changes (agent: build)
- [ ] T-6.5: Final verification — run full test suite (`pytest`), lint (`ruff check`), typecheck (`ty check src/`), policy check (`python scripts/check_workflow_policy.py`), secret scan (`gitleaks protect --staged`) (agent: verify)
