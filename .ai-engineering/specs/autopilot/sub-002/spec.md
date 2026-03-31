---
id: sub-002
parent: spec-097
title: "Workflow Architecture Split"
status: planning
files:
  - .github/workflows/ci.yml              # 758 lines, monolith to decompose
  - .github/workflows/ci-check.yml        # NEW: validation + dry build
  - .github/workflows/ci-build.yml        # NEW: build + artifact upload
  - .github/workflows/release.yml         # UPDATE: verify-ci reference
  - .github/workflows/install-smoke.yml   # READ-ONLY: confirm no overlap
  - .github/workflows/maintenance.yml     # READ-ONLY: confirm no overlap
  - .github/workflows/label-sync.yml      # READ-ONLY: confirm no overlap
  - scripts/check_workflow_policy.py      # UPDATE: _FIRST_PARTY_PREFIXES
  - README.md                             # NOTE: badge references ci.yml
depends_on: []
---

# Sub-Spec 002: Workflow Architecture Split

## Scope

Decompose the 758-line `ci.yml` monolith into two focused workflows: `ci-check.yml` (validation + dry build, runs on PR + push to main) and `ci-build.yml` (build + artifact upload, triggers via `workflow_run` on ci-check success on main, uses `head_sha`). Add `build-check` dry build job to ci-check. Update `check_workflow_policy.py` `_FIRST_PARTY_PREFIXES`. Update `release.yml` verify-ci reference. Deprecate old `ci.yml`. Covers spec-097 Phase 2 and decisions D-097-01, D-097-02, D-097-09, D-097-11.

## Exploration

### Existing Files

#### `.github/workflows/ci.yml` (758 lines)

**Triggers**: `push` to `[main, "rewrite/**"]` and `pull_request` to `[main]`, with `paths-ignore` for `.mdx`, `.rst`, `.txt`, `docs/**`.
**Permissions**: `contents: read` (top-level).
**Concurrency**: `ci-${{ github.ref }}`, cancel-in-progress: true.

**Jobs** (17 total):

| # | Job ID | Name | Depends On | Condition | Lines |
|---|--------|------|------------|-----------|-------|
| 1 | `change-scope` | Change Scope | none | always | 27-69 |
| 2 | `lint` | Lint & Format | change-scope | code == true | 71-87 |
| 3 | `duplication` | Duplication Check | change-scope | code == true | 89-103 |
| 4 | `risk-acceptance` | Risk Acceptance Check | change-scope | code == true | 105-119 |
| 5 | `typecheck` | Type Check | change-scope | code == true | 121-135 |
| 6 | `test-unit` | Unit (matrix 3x3) | change-scope | code == true | 137-192 |
| 7 | `test-integration` | Integration (matrix 3x1) | change-scope | code == true | 194-248 |
| 8 | `test-e2e` | E2E | change-scope | code == true | 250-286 |
| 9 | `sonarcloud` | SonarCloud | change-scope, test-unit, test-integration, test-e2e | code == true | 288-320 |
| 10 | `framework-smoke` | Framework Smoke (matrix 3x1) | change-scope | code == true | 322-389 |
| 11 | `workflow-sanity` | Workflow Sanity | none | always | 391-411 |
| 12 | `verify-gate-trailers` | Verify Gate Trailers | none | PR + not dependabot | 413-442 |
| 13 | `snyk-security` | Snyk Security | change-scope | has-snyk-token == true | 444-479 |
| 14 | `security` | Security Audit | none | always | 481-524 |
| 15 | `content-integrity` | Content Integrity | none | always | 526-576 |
| 16 | `build` | Build Package | change-scope + 12 validation jobs | code == true | 578-611 |
| 17 | `ci-result` | CI Result | all 16 jobs above | always() | 613-758 |

**Key observations**:
- `build` (job 16) is the real build that uploads `dist/` artifact. It depends on ALL validation jobs passing.
- `ci-result` (job 17) is the aggregation gate. It categorizes jobs into 4 tiers: always-required, code-conditional, PR-only, optional.
- `change-scope` uses `dorny/paths-filter` and explicitly references `.github/workflows/ci.yml` in its `test-config` filter (line 65) -- must update to reference new workflow names.
- `change-scope` also outputs `has-snyk-token` for the optional Snyk job.
- Concurrency group uses `ci-${{ github.ref }}` -- new workflows need their own concurrency groups.

#### `.github/workflows/release.yml` (133 lines)

**Triggers**: `push` tags `v*`.
**Permissions**: `contents: write`, `actions: read`, `id-token: write`.

**Jobs** (3):
1. `verify-ci` -- Searches for CI workflow run via `gh run list --workflow=ci.yml --commit=$COMMIT_SHA`. Retries 10 times with 30s backoff. Outputs `ci-run-id`.
2. `publish` -- Downloads `dist` artifact from ci-run-id, publishes to PyPI via `pypa/gh-action-pypi-publish`.
3. `github-release` -- Downloads `dist` again, extracts CHANGELOG notes, creates GitHub Release.

**Key dependency**: Line 37 explicitly references `--workflow=ci.yml`. This MUST be updated to reference the new workflow. Since `ci-build.yml` will be the one producing artifacts, the release workflow should reference `ci-build.yml` (not `ci-check.yml`). However, per the parent plan T-2.5, the spec says to update to `ci-check` -- this is incorrect for artifact download. The verify-ci job needs to verify that checks passed AND locate the build artifact. During Phase 2 transition (before ci-build exists as the artifact producer on main), referencing `ci-check` for the "passed" signal is correct, but the artifact download in `publish` job still needs the `ci-run-id` from whichever workflow produces the `dist` artifact. Since ci-build is new and won't have historical runs, release.yml should reference `ci-build.yml` for the verify-ci step once ci-build is active. For the transition: point verify-ci at `ci-check.yml` (validation signal), and handle artifact source separately. The parent plan accounts for this -- Phase 5 rewrites release.yml entirely. Phase 2 only needs the transition reference.

#### `.github/workflows/install-smoke.yml` (110 lines)

**Triggers**: `pull_request` to main, `push` to `[main, "rewrite/**"]`.
**Permissions**: `contents: read`.
**Jobs**: `smoke-test` (matrix 3 OS) + `install-smoke` (aggregation gate).

**Overlap analysis** (D-097-11): `install-smoke` builds a wheel (`uv build`), installs it into a clean venv, and validates the installed CLI (`ai-eng version`, `ai-eng install`, `ai-eng doctor`). The new `build-check` job in ci-check only runs `uv build` without installing or testing the CLI. Different test surfaces -- no overlap. Confirmed: install-smoke.yml stays separate.

#### `.github/workflows/maintenance.yml` (30 lines)

**Triggers**: Weekly schedule (Monday 06:00 UTC) + workflow_dispatch.
**No overlap** with CI split. Unchanged.

#### `.github/workflows/label-sync.yml` (24 lines)

**Triggers**: Push to main (paths: `.github/labels.yml`) + workflow_dispatch.
**No overlap** with CI split. Unchanged.

#### `scripts/check_workflow_policy.py` (117 lines)

**Policies enforced**:
1. No `pull_request_target` trigger.
2. Top-level `permissions` key required.
3. Every job must have `timeout-minutes`.
4. Workflows with `pull_request` trigger must have `concurrency` key.
5. Third-party actions must use SHA pinning.

**`_FIRST_PARTY_PREFIXES`** (line 19): Currently only `("actions/",)`. Actions from `astral-sh/`, `SonarSource/`, `dorny/`, `EndBug/`, `pypa/`, `CycloneDX/`, `github/` are NOT in this list. They use SHA pinning today so the check passes, but adding them to the prefix list means they would be exempt from SHA pinning checks. Per the parent plan, these orgs are in the Actions allowlist (T-1.4) and should be added to `_FIRST_PARTY_PREFIXES`.

**Impact on new workflows**: Both `ci-check.yml` and `ci-build.yml` must pass all 5 policy checks. ci-check.yml has a `pull_request` trigger so it needs `concurrency`. ci-build.yml uses `workflow_run` (not `pull_request`) so concurrency is optional.

### Patterns to Follow

#### workflow_run trigger (for ci-build.yml)

```yaml
on:
  workflow_run:
    workflows: ["CI Check"]    # matches the `name:` field, not filename
    types: [completed]
    branches: [main]
```

Key facts:
- `workflows:` matches the workflow **name** (the `name:` key), not the filename.
- `types: [completed]` fires on any conclusion (success, failure, cancelled). Must add `if: github.event.workflow_run.conclusion == 'success'` on jobs.
- Always runs the **default branch version** of the workflow file, regardless of which branch triggered the upstream workflow.
- `github.event.workflow_run.head_sha` gives the exact commit that triggered ci-check.
- Cannot be a required status check for branch protection (fires post-merge on main).

#### Concurrency groups

ci-check.yml needs its own concurrency group to avoid conflicts with the deprecated ci.yml during transition:
```yaml
concurrency:
  group: ci-check-${{ github.ref }}
  cancel-in-progress: true
```

ci-build.yml does not need concurrency cancellation (each run is for a specific commit on main, should not be cancelled).

#### Aggregation job pattern

The `ci-result` pattern in current ci.yml is well-structured. Replicate as `ci-check-result` in ci-check.yml with these changes:
- Remove `build` from `needs` and from `code_conditional` array.
- Add `build-check` to `code_conditional` array.
- Keep all 4 tiers: always-required, code-conditional, PR-only, optional.

### Dependencies Map

| Consumer | References | How |
|----------|-----------|-----|
| `release.yml` verify-ci job | `ci.yml` | `gh run list --workflow=ci.yml` (line 37) |
| `release.yml` publish + github-release | `ci.yml` artifact `dist` | `actions/download-artifact` with `run-id` from verify-ci |
| `ci.yml` change-scope filter | `.github/workflows/ci.yml` | `test-config` paths-filter (line 65) |
| `README.md` badge | `ci.yml` | Badge URL (line 16): `actions/workflows/ci.yml/badge.svg` |
| Branch Protection | `CI Result` | Required status check name is the job `name:` field |
| `check_workflow_policy.py` | All `.github/workflows/*.yml` | Scans all YAML files in directory |
| `ai-pipeline` skill handlers | `ci.yml` | Documentation reference (not functional) |
| `CHANGELOG.md` | `ci.yml` | Historical reference (not functional) |
| `sub-006` cleanup spec | `ci.yml` | Scheduled deletion in Phase 6 |

### Risks

#### R1: Status check name change breaks branch protection

Current branch protection requires `CI Result` as status check. Renaming to `ci-check-result` (or changing the workflow `name:`) means:
- The old status check name disappears from GitHub's list.
- The new name must be manually added as a required status check.
- During transition, both old and new workflows may run if ci.yml is not immediately disabled.

**Mitigation**: T-2.8 disables ci.yml triggers (sets to `workflow_dispatch` only) in the same PR. T-2.7 updates branch protection via `gh api`. These must be coordinated -- the PR that introduces ci-check.yml must also disable ci.yml triggers and update branch protection. If branch protection update fails (permissions), the old CI Result check will be missing and PRs will be blocked.

**Recommendation**: Keep the aggregation job name as `CI Result` in ci-check.yml to avoid branch protection changes. This avoids R1 entirely. The job ID can be `ci-check-result` internally but the `name:` field should remain `CI Result`.

#### R2: Duplicate workflow runs during transition

If ci.yml is not disabled before ci-check.yml is merged, both workflows trigger on the same PR/push events. This doubles CI usage and creates confusing status checks.

**Mitigation**: T-2.8 disables ci.yml triggers in the same PR. The deprecated ci.yml gets `on: workflow_dispatch` only.

#### R3: workflow_run event always uses default branch workflow file

ci-build.yml runs the version from the default branch (main). If the PR introduces ci-build.yml for the first time, it won't run until the PR is merged. This means ci-build cannot be tested on the PR itself.

**Mitigation**: Accept this as a known GitHub limitation. The dry-build in ci-check (build-check job) validates compilation on the PR. ci-build only adds artifact upload, which is low-risk. After merge, verify ci-build triggers correctly on the first push to main.

#### R4: release.yml transition -- artifact source changes

During Phase 2, the old `ci.yml` is deprecated but `release.yml` still needs to find CI artifacts. If ci.yml no longer runs (disabled triggers), old artifacts expire (5-day default), and ci-build.yml hasn't produced artifacts yet, releases are blocked.

**Mitigation**: The current artifact retention is 5 days (ci.yml `build` job). Once ci.yml is disabled, no new artifacts are produced until ci-build.yml is active. Phase 2 should ensure ci-build.yml is ready to produce artifacts before ci.yml is disabled. The parent plan T-2.5 updates release.yml to reference `ci-check` for the validation signal, but during Phase 2, release.yml still downloads `dist` artifact from the referenced workflow run. Since ci-check does NOT produce artifacts (only build-check dry build), `release.yml` must reference `ci-build.yml` for artifact download. However, ci-build.yml won't have runs until it's merged and triggered. For the transition: keep release.yml referencing `ci.yml` in the verify-ci step until Phase 5 rewrites it entirely. Or: update to reference `ci-build` and accept that releases are blocked until ci-build has its first successful run on main.

**Recommendation**: Update release.yml verify-ci to reference `ci-build.yml` (the artifact producer). Accept that the first release after merge requires ci-build to have run successfully at least once. This is safe because ci-build triggers automatically on ci-check success on main -- the merge commit itself triggers ci-check, which triggers ci-build, which produces the artifact.

#### R5: change-scope self-reference

The `change-scope` job's `test-config` filter (line 65) references `.github/workflows/ci.yml`. In the new ci-check.yml, this should reference `.github/workflows/ci-check.yml` instead, so that changes to ci-check.yml trigger full test runs.

## Confidence

**Level**: HIGH (9/10)

All source files are fully explored. The job decomposition is straightforward -- every job from ci.yml maps cleanly to ci-check.yml except the `build` job which moves to ci-build.yml. The main complexity is the transition period: coordinating ci.yml deprecation, branch protection updates, and release.yml references. The parent spec and plan are clear on the approach. No ambiguities remain that would block implementation.
