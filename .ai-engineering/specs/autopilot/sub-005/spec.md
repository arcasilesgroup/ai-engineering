---
id: sub-005
parent: spec-097
title: "Artifact-Driven Release Pipeline"
status: planning
files: [".github/workflows/release.yml", "CHANGELOG.md", "scripts/check_workflow_policy.py"]
depends_on: ["sub-003", "sub-004"]
---

# Sub-Spec 005: Artifact-Driven Release Pipeline

## Scope

Rewrite `release.yml` with `workflow_dispatch` trigger (version input, default: latest tag). Jobs: version resolution, CHANGELOG validation, PyPI publish (OIDC), GitHub Release finalization (draft to published). Rollback via same workflow with older version. Covers spec-097 Phase 5 and decisions D-097-04, D-097-07, D-097-10.

## Exploration

### Existing Files

**`.github/workflows/release.yml`** (133 lines, 3 jobs):

The current workflow triggers on `push.tags: v*` and runs three sequential jobs:

1. **`verify-ci`** -- Finds the CI workflow run for the tagged commit SHA by polling `gh run list --workflow=ci.yml --commit=COMMIT_SHA`. Retries up to 10 times with 30-second backoff (handles race when tag is pushed before CI completes). Outputs `ci-run-id` for downstream artifact download.

2. **`publish`** (needs: verify-ci) -- Downloads the `dist` artifact from the CI run using `actions/download-artifact@v8` with `run-id` parameter. Publishes to PyPI via `pypa/gh-action-pypi-publish` with OIDC (id-token: write). Uses `pypi` environment with URL.

3. **`github-release`** (needs: verify-ci, publish) -- Downloads dist again, extracts release notes from CHANGELOG.md via awk (`## [VERSION]` section), creates a GitHub Release with `gh release create` attaching dist files.

Top-level permissions: `contents: write`, `actions: read`, `id-token: write`.

**`src/ai_engineering/release/changelog.py`** (77 lines):

Three public helpers:
- `extract_release_notes(changelog_path, version)` -- Extracts the body text between `## [VERSION]` and the next `## [` heading. Returns `None` if section is missing or empty.
- `validate_changelog(changelog_path, version)` -- Returns blocking errors: checks for `[Unreleased]` section and rejects if `[VERSION]` already exists (prevents double-promotion). Used by the CLI release orchestrator pre-release.
- `promote_unreleased(changelog_path, version, date_str)` -- Moves `[Unreleased]` content to `[VERSION] - DATE` and clears unreleased. Used during release branch preparation.

Private helper `_section_bounds(text, heading)` does regex matching for `## [heading]` and returns (start, end) offsets.

**`src/ai_engineering/release/orchestrator.py`** (663 lines):

The CLI `ai-eng release <version>` flow: validate (semver, branch=main, clean tree, version > current, VCS auth, CHANGELOG) -> detect state (release branch, tag existence) -> prepare branch (create release/vN, bump version, promote CHANGELOG, commit) -> create PR -> wait for merge (optional) -> create tag -> update manifest -> monitor pipeline.

Key insight: the orchestrator's `_validate()` calls `validate_changelog()` which checks that the `[VERSION]` section does NOT yet exist (pre-promotion check). The new release.yml needs the inverse: validate that `[VERSION]` DOES exist (post-promotion check, confirming release notes were written).

**`CHANGELOG.md`** format:

Keep a Changelog format. Header: `# Changelog`. Sections: `## [Unreleased]`, then `## [VERSION] - DATE` entries. Each version section contains `### Added`, `### Changed`, `### Fixed`, `### Removed` subsections.

**`.github/workflows/ci.yml`** (build job, lines 578-611):

The `build` job runs after all validation jobs, executes `uv build`, and uploads `dist/` as artifact with `name: dist` and `retention-days: 5`. After sub-002, this moves to `ci-build.yml` with `workflow_run` trigger and 90-day retention. After sub-003, ci-build also runs semantic-release to create tags and draft GitHub Releases.

**`scripts/check_workflow_policy.py`** (117 lines):

Enforces 5 policies on all `.github/workflows/*.yml`:
1. No `pull_request_target` trigger
2. Top-level `permissions` key required
3. Every job must have `timeout-minutes`
4. Workflows with `pull_request` trigger must have `concurrency`
5. Third-party actions must use SHA pinning (`owner/action@<40-hex SHA>`)

First-party prefix: `actions/` only. Sub-002 will expand this.

### Patterns to Follow

**workflow_dispatch trigger pattern**:
```yaml
on:
  workflow_dispatch:
    inputs:
      version:
        description: "Version to release (e.g., 1.2.3). Leave empty for latest tag."
        required: false
        type: string
        default: ""
```

**Draft release promotion via `gh` CLI**:
```bash
# Find draft release by tag
gh release view "v${VERSION}" --json isDraft,tagName
# Promote draft to published, updating body
gh release edit "v${VERSION}" --draft=false --notes-file release-notes.md
```

**Artifact download from another workflow run**:
The current pattern uses `actions/download-artifact@v8` with `run-id` to download from a specific CI run. The new flow must find the ci-build run that produced the artifact for the target version's tag SHA.

**OIDC publishing**: The existing `pypa/gh-action-pypi-publish` step requires no changes -- it already uses OIDC via `id-token: write` permission. The `pypi` environment with branch restriction to main is configured (sub-001 hardens this).

### Dependencies Map

| Import | From | What |
|--------|------|------|
| ci-build.yml workflow | sub-002 | Produces `dist` artifact with 90-day retention, uploads via `actions/upload-artifact@v7` |
| Draft GitHub Releases | sub-003 | semantic-release in ci-build creates draft releases with tag `vN.M.P` on version bump |
| SBOM + checksums | sub-004 | `sbom.json` and `CHECKSUMS-SHA256.txt` attached to draft release by ci-build |
| `pypi` environment | sub-001 | Branch restriction to main, OIDC trust policy |

**What sub-005 exports**: The fully rewritten `release.yml` with `workflow_dispatch` trigger. This is the terminal workflow -- sub-006 (cleanup) depends on it for removing the deprecated `ci.yml`.

**Integration contract with ci-build.yml** (produced by sub-002 + sub-004):
- Artifact name: `dist` (matches current convention)
- Artifact contains: `*.whl` + `*.tar.gz`
- Draft GitHub Release: created by semantic-release with tag `vN.M.P`, body auto-generated from commits
- SBOM + checksums: attached to draft release as assets

### Risks

**R-5.1: Version resolution edge cases**
- User inputs `1.2.3` but no tag `v1.2.3` exists yet (semantic-release hasn't run for this version)
- User leaves version empty but no tags exist in the repository
- Version input includes the `v` prefix (must strip/normalize)
- Mitigation: Version resolution job validates tag existence and artifact availability before proceeding

**R-5.2: CHANGELOG format validation fragility**
- The awk-based extraction in current release.yml is duplicated from changelog.py logic
- Format variations (trailing whitespace, different heading levels) could cause false negatives
- Mitigation: Keep workflow validation simple (grep for `## [VERSION]` existence), rely on the orchestrator for rich validation

**R-5.3: Artifact not found for version**
- ci-build run may have been pruned (beyond 90-day retention)
- ci-build may have failed for this commit, producing no artifact
- Draft release exists but has no dist assets attached
- Mitigation: Explicit verification step that checks both artifact existence and content before proceeding to publish

**R-5.4: Draft release not found**
- semantic-release may not have created a draft (no-bump scenario from D-097-06)
- Draft was manually deleted or promoted
- Mitigation: Clear error message explaining the prerequisite, suggest re-running ci-build

**R-5.5: Rollback to older version**
- Older version's artifact may have expired (beyond 90-day retention)
- PyPI does not allow re-publishing the same version (immutable index)
- Mitigation: Document that rollback publishes the older artifact to PyPI only if it hasn't been published before; for already-published versions, rollback means GitHub Release promotion only

**R-5.6: Concurrency -- multiple releases triggered simultaneously**
- Two `workflow_dispatch` runs for different versions could race on PyPI publish
- Mitigation: Add concurrency group on version input to serialize releases
