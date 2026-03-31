---
total: 7
completed: 0
---

# Plan: sub-005 Artifact-Driven Release Pipeline

## Plan

```
exports: [release.yml workflow_dispatch]
imports: [ci-build.yml from sub-002, draft GitHub Releases from sub-003, SBOM/checksums from sub-004]
```

### T-5.1: Rewrite release.yml trigger to workflow_dispatch

Replace the `push.tags: v*` trigger with `workflow_dispatch` and a version input. The version input accepts a bare version string (e.g., `1.2.3`), defaulting to empty string which signals "use latest tag". Keep top-level permissions (`contents: write`, `actions: read`, `id-token: write`). Remove the old `verify-ci` job entirely -- it polled for CI completion by commit SHA, which is no longer needed since artifacts come from ci-build runs identified by tag.

Add a concurrency group `release-${{ github.event.inputs.version || 'latest' }}` to serialize releases for the same version (risk R-5.6).

**Files**: `.github/workflows/release.yml`
**Done**: `release.yml` has `on: workflow_dispatch` with `inputs.version` (type: string, required: false, default: ""), concurrency group present, old `on: push.tags` removed, old `verify-ci` job removed.

### T-5.2: Add version resolution job

Create `resolve-version` job as the first job in the pipeline. Logic:

1. If `inputs.version` is non-empty, normalize it (strip leading `v` if present), set `VERSION`.
2. If `inputs.version` is empty, find the latest semver tag: `git tag --list 'v*' --sort=-v:refname | head -1`, strip `v` prefix, set `VERSION`.
3. Fail if no version could be resolved (no tags exist and no input given).
4. Verify tag `v${VERSION}` exists: `git rev-parse --verify "refs/tags/v${VERSION}"`. Fail with clear error if tag does not exist.
5. Find the ci-build workflow run that produced artifacts for this tag's commit SHA: `gh run list --workflow=ci-build.yml --commit=${TAG_SHA} --status=completed --conclusion=success --json databaseId --limit 1`. Fail if no successful ci-build run found.
6. Verify artifact exists in that run: `gh api repos/{owner}/{repo}/actions/runs/${RUN_ID}/artifacts --jq '.artifacts[] | select(.name=="dist") | .id'`. Fail if dist artifact not found.
7. Output: `version`, `tag-name`, `ci-run-id`.

**Files**: `.github/workflows/release.yml`
**Done**: `resolve-version` job runs, resolves version from input or latest tag, verifies tag exists, finds ci-build run ID, verifies dist artifact exists, outputs `version`, `tag-name`, `ci-run-id`. Tested with both explicit version input and empty (latest tag) paths.

### T-5.3: Add CHANGELOG validation job

Create `validate-changelog` job (needs: `resolve-version`). Logic:

1. Checkout the repository at the tag's commit: `actions/checkout@v6` with `ref: v${VERSION}`.
2. Validate `## [VERSION]` section exists in CHANGELOG.md using grep: `grep -q "^## \[${VERSION}\]" CHANGELOG.md`. This is the inverse of the orchestrator's `validate_changelog()` which checks the section does NOT exist (pre-promotion). Here we need it to exist (post-promotion, confirming release notes were written).
3. Extract release notes for the finalization job: use awk to capture text between `## [VERSION]` and next `## [` heading, write to `release-notes.md`.
4. Fail if section is missing with actionable error: "CHANGELOG.md missing section for version ${VERSION}. Ensure the release branch promoted [Unreleased] before merging."
5. Upload `release-notes.md` as a workflow artifact for the finalization job.

Implements decision D-097-10: CHANGELOG validation in release workflow only (not in CI).

**Files**: `.github/workflows/release.yml`
**Done**: `validate-changelog` job checks for `## [VERSION]` in CHANGELOG.md, extracts release notes to `release-notes.md`, uploads as artifact. Fails with clear message if section missing.

### T-5.4: Add PyPI publish job with OIDC

Create `publish-pypi` job (needs: `resolve-version`, `validate-changelog`). Logic:

1. Download `dist` artifact from the ci-build run using `actions/download-artifact@v8` with `run-id: ${{ needs.resolve-version.outputs.ci-run-id }}` and `github-token: ${{ github.token }}`.
2. Verify artifact contents: `ls -la dist/` and fail if empty.
3. Publish to PyPI using `pypa/gh-action-pypi-publish@ed0c53931b1dc9bd32cbe73a98c7f6766f8a527e` (same pinned SHA as current release.yml, v1.13.0).
4. Environment: `pypi` with URL `https://pypi.org/project/ai-engineering/`.

This job uses the existing artifact from ci-build rather than rebuilding, implementing decision D-097-04 (artifact-driven releases, zero-rebuild principle).

**Files**: `.github/workflows/release.yml`
**Done**: `publish-pypi` job downloads dist from ci-build run, verifies contents, publishes via OIDC. Uses `pypi` environment. No rebuild occurs.

### T-5.5: Add GitHub Release finalization job

Create `finalize-release` job (needs: `resolve-version`, `validate-changelog`, `publish-pypi`). Logic:

1. Download `release-notes.md` artifact from the `validate-changelog` job.
2. Check if a draft release exists for the tag: `gh release view "v${VERSION}" --json isDraft,tagName`. The draft was created by semantic-release in ci-build (sub-003).
3. If draft exists: promote it by setting `--draft=false` and updating release notes: `gh release edit "v${VERSION}" --draft=false --notes-file release-notes.md --latest`.
4. If no draft exists (edge case -- manual tag, or semantic-release skipped draft creation): create a new published release: `gh release create "v${VERSION}" --title "v${VERSION}" --notes-file release-notes.md --latest`.
5. In both cases, the dist artifacts (wheel + sdist) and supply-chain assets (SBOM, checksums) are already attached to the draft release by ci-build (sub-004). Do not re-upload them.
6. Verify the release is now published: `gh release view "v${VERSION}" --json isDraft` should return `false`.

Implements decision D-097-07 (permanent GitHub Releases as the long-term artifact store).

**Files**: `.github/workflows/release.yml`
**Done**: `finalize-release` job promotes draft release to published (or creates new release if no draft), attaches release notes from CHANGELOG, verifies release is published. Handles both draft-promotion and fresh-creation paths.

### T-5.6: Verify release.yml passes check_workflow_policy.py

Run `check_workflow_policy.py` against the rewritten release.yml to ensure compliance with all 5 policies:

1. No `pull_request_target` trigger -- satisfied (workflow_dispatch only).
2. Top-level `permissions` present -- must be present.
3. Every job has `timeout-minutes` -- must be set on all 4 jobs.
4. Concurrency required for `pull_request` trigger -- not applicable (no PR trigger), but concurrency is present anyway for serialization.
5. Third-party actions SHA-pinned -- `pypa/gh-action-pypi-publish` must keep its SHA pin.

Also verify the workflow is valid YAML and structurally sound.

**Files**: `.github/workflows/release.yml`, `scripts/check_workflow_policy.py`
**Done**: `uv run python scripts/check_workflow_policy.py` passes with no failures for release.yml. All jobs have `timeout-minutes`, permissions block present, third-party actions SHA-pinned.

### T-5.7: Document rollback procedure

Add a comment block at the top of `release.yml` documenting the rollback procedure. The workflow_dispatch design inherently supports rollback: dispatch with an older version as input. Document the constraints:

1. Rollback publishes an older artifact to PyPI only if that version has not been previously published (PyPI is immutable).
2. For already-published versions, rollback means promoting the GitHub Release only (making it visible as latest).
3. The target version's tag must exist and its ci-build artifacts must still be available (within 90-day retention per D-097-07).
4. Example usage: "To rollback to v1.2.3: Actions > Release > Run workflow > version: 1.2.3".

**Files**: `.github/workflows/release.yml`
**Done**: Comment block at top of release.yml documents rollback procedure, constraints (PyPI immutability, 90-day artifact retention), and example usage.

## Confidence

**Overall: High (85%)**

Justification:
- The current release.yml is straightforward (133 lines, 3 jobs) and the rewrite is a structural transformation, not a complex logic change.
- All building blocks exist: `actions/download-artifact` cross-workflow download, `gh release edit --draft=false` for promotion, `pypa/gh-action-pypi-publish` OIDC pattern.
- Dependencies are well-defined: sub-002 provides ci-build.yml with artifacts, sub-003 provides draft releases, sub-004 provides SBOM/checksums.
- Primary uncertainty is integration testing: the artifact download chain (ci-build -> release) can only be fully validated in a real GitHub Actions run, not locally.
- Version resolution edge cases (R-5.1) are mitigable with defensive scripting but add surface area.

## Self-Report
[EMPTY -- populated by Phase 4]
