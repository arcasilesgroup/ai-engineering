---
spec: spec-097
title: "CI/CD Redesign — DevSecOps, Supply Chain Security, Artifact-Driven Releases"
status: draft
effort: large
---

## Summary

The current CI/CD pipeline is a 760-line monolith (`ci.yml`) that builds deployable artifacts on every PR (untrusted code), lacks supply chain security (no SLSA provenance, no SBOM, no checksums), and relies on a tag-triggered release that couples build+publish. GitHub repository settings have critical gaps: 0 required approvals, no code owner review enforcement, no tag protection, and no environment branch restrictions. For an open-source framework targeting regulated industries (banking, finance, healthcare), this is unacceptable.

This spec redesigns the entire CI/CD architecture into 6 focused workflows with clear trust boundaries, artifact-driven releases with rollback capability, SLSA Build provenance (L2-L3 depending on dependency pinning), and hardened GitHub settings that prevent external contributors from bypassing governance.

## Goals

- Split `ci.yml` monolith into `ci-check.yml` (validation, no artifacts) + `ci-build.yml` (build + supply chain, main only)
- ci-build triggers via `workflow_run` after ci-check succeeds on main, using `head_sha` for exact commit tracking
- Adopt python-semantic-release with conventional commits (`feat(spec-NNN):`, `fix:`, `chore:`) for automatic versioning
- Generate SLSA Build provenance via `actions/attest-build-provenance` in the build job (L2 baseline, L3 with `uv.lock` verification)
- Generate CycloneDX SBOM and SHA-256 checksums for every release artifact
- Redesign `release.yml` as `workflow_dispatch` with default-to-latest input, consuming existing artifacts (no rebuild)
- Artifact retention: 90 days in GitHub Actions + permanent in GitHub Releases
- Only produce release artifacts when semantic-release determines a version bump (no-bump merges are silent)
- Include dry-build validation (`uv build` without artifact upload) in ci-check for PR compilation checks
- Validate CHANGELOG section exists in release workflow (not in CI)
- Harden GitHub settings: 1 required approval, code owner review, enforce for admins, last-push approval, tag protection for `v*`
- Configure PyPI environment with branch restriction to main only
- Update `/ai-commit` skill to generate conventional commit format
- Extend DEC-012 zero-rebuild principle into artifact-driven releases (D-097-04 supersedes DEC-012)
- Eliminate dual version source: remove `__version__.py`, use `pyproject.toml` as single version source via hatchling dynamic versioning
- Update `scripts/check_workflow_policy.py` to include all allowlisted action orgs
- Update `ai-eng gate commit-msg` to accept both legacy and conventional commit formats during transition
- Every workflow passes `scripts/check_workflow_policy.py` (SHA-pinning, permissions, timeouts, concurrency)

## Non-Goals

- Test PyPI staging (future consideration, not in this spec)
- Automated rollback (manual `workflow_dispatch` with older version covers this need)
- GitHub Packages / OCI artifact registry (GitHub Releases + Actions artifacts cover this need)
- Changing the CI test matrix (3 OS x 3 Python versions stays as-is)
- Migrating away from GitHub Actions to another CI platform
- Release notifications (Slack, email) — out of scope
- Signed git tags (GPG/SSH) — tag protection rules cover this need
- Merging `install-smoke.yml` into ci-check (they test different things: smoke tests the installed wheel end-to-end, dry build tests compilation only)

## Decisions

### D-097-01: Workflow decomposition — 6 independent YAML files

Split the monolith into focused workflows: `ci-check.yml`, `ci-build.yml`, `release.yml`, `install-smoke.yml`, `maintenance.yml`, `label-sync.yml`.

**Rationale**: A 760-line monolith violates separation of concerns. PRs (untrusted) must never produce deployable artifacts. Build and validation have different triggers, permissions, and outputs. Each workflow should do one thing.

### D-097-02: ci-build triggers via workflow_run on ci-check success

ci-build uses `on: workflow_run` filtering on ci-check completion with success conclusion on main branch. Uses `github.event.workflow_run.head_sha` for exact commit checkout.

**Rationale**: Guarantees that artifacts are only produced after all validation passes. Using head_sha prevents race conditions when multiple merges happen in quick succession. Sequential guarantee: checks pass → then build.

### D-097-03: Conventional commits replace spec-NNN prefix

Commit format changes from `spec-NNN: description` to `feat(spec-NNN): description`, `fix(scope): description`, `chore: description`. `/ai-commit` skill updated to generate this format.

**Rationale**: python-semantic-release requires conventional commit parsing to determine version bumps (feat → minor, fix → patch, BREAKING CHANGE → major). The spec number is preserved in the scope parenthetical. DEC-015 is superseded.

### D-097-04: Artifact-driven releases with workflow_dispatch

Release is decoupled from build. `release.yml` uses `workflow_dispatch` with a version input (default: latest tag). Downloads the existing artifact from the matching ci-build run, validates CHANGELOG, publishes to PyPI, and creates GitHub Release.

**Rationale**: Separating build from publish enables rollback (publish an older artifact), removes timing pressure (no 5-day expiry for release decisions), and makes releases a conscious deployment decision rather than an automated side-effect.

### D-097-05: SLSA Build attestations generated in the build job

`actions/attest-build-provenance` runs in the same job that executes `uv build`, ensuring provenance is signed by the builder identity. This achieves SLSA Build L2 baseline; L3 requires additional dependency pinning verification via `uv.lock`.

**Rationale**: Generating attestations in the same job that builds ensures the provenance signature covers the exact artifacts. A separate job or workflow would weaken the provenance chain. L2 is the realistic baseline for GitHub-hosted runners; L3 is achievable by verifying `uv.lock` integrity before build. The spec does not claim L3 unconditionally — regulated industry auditors will verify the actual level.

### D-097-06: Semantic-release only generates artifacts on version bump

When python-semantic-release determines no bump is needed (only `chore:`, `docs:`, `ci:` commits since last tag), ci-build validates the build but does not produce a tag, draft release, or stored artifact.

**Rationale**: Producing artifacts for non-releaseable changes creates noise, wastes storage, and confuses the artifact inventory. Silent no-op on no-bump keeps the artifact store clean: every artifact in it is a genuine release candidate.

### D-097-07: 90-day artifact retention + permanent GitHub Releases

CI artifacts retain for 90 days (GitHub Actions maximum for free tier). Published releases persist permanently as GitHub Release assets.

**Rationale**: 90 days covers any reasonable release delay, hotfix window, or vacation period. Published releases are permanent by nature (GitHub Releases don't expire). Covers both "recent candidates" and "historical releases" without custom infrastructure.

### D-097-08: GitHub hardening — required reviews, tag protection, environment restrictions

Branch protection: 1 required approval, code owner review required, dismiss stale reviews, last-push approval required, enforce for admins. Tag protection: `v*` pattern restricted to maintainers. PyPI environment: branch restriction to main only.

**Rationale**: Open-source project where external contributors can open PRs. Without required reviews, code owner enforcement, and tag protection, an external contributor with write access (or a compromised account) could merge unreviewed code and create releases. Defense in depth: branch protection + tag protection + environment restriction.

### D-097-09: Dry build in ci-check for PR compilation validation

ci-check includes a `build-check` job that runs `uv build` without uploading artifacts. Validates that the package compiles before merge.

**Rationale**: Catching build failures after merge is expensive — the broken commit is already on main and blocks all subsequent releases. A dry build in PRs prevents this. No artifacts are produced because PR code has not passed review and merge — it is untrusted.

### D-097-10: CHANGELOG validation in release workflow only

Release workflow validates that `CHANGELOG.md` contains a section matching the release version (`## [VERSION]`). If missing, the release fails with a clear error. CI does not validate CHANGELOG.

**Rationale**: CHANGELOG is a release concern, not a CI concern. Many merges to main are internal work (`chore:`, `docs:`) that don't need CHANGELOG entries. Validating only at release time ensures the check fires when it matters and doesn't create noise on routine merges.

## Phases

### Phase 1: GitHub Hardening

Configure repository settings, branch protection, tag protection, and environment restrictions. No workflow changes.

- Branch protection: 1 required approval, code owner review, enforce for admins, last-push approval, dismiss stale reviews
- Tag protection ruleset: `v*` restricted to maintainers
- PyPI environment: branch restriction to main, no admin bypass
- Rotate or delete expired WIKI_PAT secret
- Actions allowlist: `actions/*`, `github/*`, `pypa/*`, `astral-sh/*`, `SonarSource/*`, `CycloneDX/*`, `EndBug/*`, `dorny/*`
- Validate settings via `gh api repos/{owner}/{repo}/branches/main/protection` after applying changes

### Phase 2: Split ci.yml → ci-check.yml + ci-build.yml

Decompose the monolith. ci-check runs on PR + push to main (validation only, dry build, no artifacts). ci-build runs via workflow_run on ci-check success on main (build + artifact upload).

- Create `ci-check.yml` with all validation jobs from current ci.yml + build-check (dry build)
- Create `ci-build.yml` triggered by workflow_run on ci-check success on main
- ci-build uses `github.event.workflow_run.head_sha` for checkout
- Artifact retention: 90 days
- Update `ci-result` job in ci-check to handle build-check as code-conditional
- Update branch protection required status checks to reference new workflow names
- Update existing `release.yml` to reference `ci-check` instead of `ci.yml` in verify-ci job (prevents breakage during transition)
- Retain `ci.yml` as deprecated until Phase 5 completes — do NOT delete yet

### Phase 3: Semantic Release + Conventional Commits

Adopt python-semantic-release for auto-versioning. Update commit conventions.

- Install and configure python-semantic-release in `pyproject.toml`
- Configure commit parser for conventional commits with spec-NNN scope support
- Integrate semantic-release into ci-build: analyze commits → bump version → tag → draft GitHub Release
- Update `/ai-commit` SKILL.md to generate conventional commit format (`feat(spec-NNN):`)
- Update DEC-015 as superseded by D-097-03
- Eliminate `__version__.py` — configure hatchling to read version from `pyproject.toml` dynamically
- Configure `version_toml` in `[tool.semantic_release]` to update `pyproject.toml` only (single source)
- Update `ai-eng gate commit-msg` to accept both `spec-NNN:` (legacy) and `feat(scope):` (conventional) during transition
- Update `scripts/check_workflow_policy.py` `_FIRST_PARTY_PREFIXES` to include all allowlisted action orgs

### Phase 4: Supply Chain Security (SLSA + SBOM + Checksums)

Add attestations, SBOM generation, and checksums to ci-build.

- Add `actions/attest-build-provenance` step in ci-build after `uv build` (same job)
- Add CycloneDX SBOM generation step
- Add SHA-256 checksum generation (`sha256sum dist/* > CHECKSUMS-SHA256.txt`)
- Attach SBOM and checksums to draft GitHub Release
- Verify attestation with `gh attestation verify`

### Phase 5: Release Redesign (workflow_dispatch)

Rewrite `release.yml` as manual-trigger artifact-driven release.

- Trigger: `workflow_dispatch` with version input (default: latest tag)
- Job 1: Resolve version — find latest tag if not specified, verify artifact exists
- Job 2: Validate CHANGELOG — `## [VERSION]` section must exist
- Job 3: Publish to PyPI — download artifact from matching ci-build run, publish via OIDC
- Job 4: Finalize GitHub Release — promote draft to published, attach release notes from CHANGELOG
- Rollback: same workflow with older version as input

### Phase 6: Cleanup + Documentation

Remove old artifacts, update framework references, persist decisions.

- Delete old `ci.yml` (retained since Phase 2, now safe to remove)
- Update `manifest.yml` if needed
- Add decisions D-097-01 through D-097-10 to `state/decision-store.json`
- Supersede DEC-012 with D-097-04 (artifact-driven releases extend zero-rebuild)
- Supersede DEC-015 with D-097-03 (conventional commits)
- Remove legacy commit format acceptance from `ai-eng gate commit-msg` (all open branches should be merged by now)
- Update CHANGELOG.md
- Verify all workflows pass `scripts/check_workflow_policy.py`

### D-097-11: install-smoke.yml remains separate from ci-check

`install-smoke.yml` is preserved as an independent workflow. It tests the installed wheel end-to-end (CLI version, doctor, wizard, dry-run) across 3 OS. ci-check's `build-check` only validates compilation. Different concerns, different test surfaces.

**Rationale**: `build-check` answers "does the code compile?" while `install-smoke` answers "does the installed package work?". Merging them would create a ci-check that is both validation and integration test, violating the separation of concerns established in D-097-01.

### D-097-12: Single version source — eliminate `__version__.py`

Remove `src/ai_engineering/__version__.py`. Configure hatchling to read version dynamically from `pyproject.toml`. python-semantic-release updates `pyproject.toml` only via `version_toml`.

**Rationale**: Dual version sources (`pyproject.toml` + `__version__.py`) create a sync hazard. semantic-release must update both files atomically, and any misconfiguration creates silent version mismatches. A single source eliminates this class of bug entirely. Code that needs the version at runtime uses `importlib.metadata.version("ai-engineering")`.

## Risks

### R1: workflow_run trigger complexity

`workflow_run` events have known quirks — they always run on the default branch's version of the workflow file, and filtering by conclusion requires careful conditional logic. Additionally, `workflow_run` workflows cannot be required status checks for branch protection — ci-build failures happen post-merge.

**Mitigation**: The dry-build in ci-check (D-097-09) catches compilation failures pre-merge. Post-merge ci-build failures (attestation, artifact upload) are operational incidents: the commit is on main but no release artifact is produced, blocking the next release until fixed. This is acceptable because (a) the code itself is valid (dry-build passed), and (b) the fix is a targeted ci-build workflow repair, not a code revert. Test workflow_run behavior in a branch before merging. Document the trigger chain clearly in workflow comments.

### R2: Semantic-release misconfiguration

Incorrect parser configuration could produce wrong version bumps or skip bumps entirely, blocking releases silently.

**Mitigation**: Phase 3 includes verification of version sync. Test with dry-run mode first. Keep `src/ai_engineering/release/version_bump.py` as fallback for manual emergency bumps.

### R3: Branch protection change breaks contributor workflow

Requiring code owner reviews and 1 approval could slow down solo maintainer work if only 1 person is available.

**Mitigation**: 4 collaborators exist (soydachi, crystian, tamasi17, CarmenTajuelo). With 1 required approval, any team member can unblock another. Admin bypass is intentionally disabled for security.

### R4: Existing PRs and branches use old commit format

After Phase 3, open PRs with `spec-NNN:` format commits won't trigger semantic-release bumps.

**Mitigation**: Squash-merge with conventional commit message format. The PR title (used as squash commit message) follows the new convention regardless of individual commit format.

### R5: SLSA attestation adds CI time

`actions/attest-build-provenance` and CycloneDX SBOM generation add build time to ci-build.

**Mitigation**: These only run on main (not PRs) and only when semantic-release determines a bump. Impact is limited to actual releases. Expected overhead: < 2 minutes.

## References

- DEC-012: Release zero-rebuild (superseded by D-097-04 — artifact-driven releases extend the principle)
- DEC-015: Conventional commits with spec-NNN prefix (to be superseded by D-097-03)
- DEC-020: Exempt automated actors from gate trailer verification
- DEC-025: Accept CVE-2026-4539 in pygments
- [GitHub: actions/attest-build-provenance](https://github.com/actions/attest-build-provenance)
- [CycloneDX Python SBOM](https://github.com/CycloneDX/cyclonedx-python)
- [python-semantic-release](https://python-semantic-release.readthedocs.io/)
- [GitHub: Tag protection rules](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/configuring-tag-protection-rules)
