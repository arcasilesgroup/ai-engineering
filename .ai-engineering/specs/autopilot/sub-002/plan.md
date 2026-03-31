---
total: 9
completed: 9
---

# Plan: sub-002 Workflow Architecture Split

```
exports: [ci-check.yml, ci-build.yml]
imports: []
```

## Plan

### [x] T-2.1: Create ci-check.yml with all validation jobs

Extract every validation job from `ci.yml` into `.github/workflows/ci-check.yml`. This includes: `change-scope`, `lint`, `duplication`, `risk-acceptance`, `typecheck`, `test-unit`, `test-integration`, `test-e2e`, `sonarcloud`, `framework-smoke`, `workflow-sanity`, `verify-gate-trailers`, `snyk-security`, `security`, `content-integrity`.

Workflow-level configuration:
- `name: CI Check`
- Triggers: `pull_request` to `[main]` + `push` to `[main, "rewrite/**"]`
- `paths-ignore`: same as current ci.yml (`.mdx`, `.rst`, `.txt`, `docs/**`)
- `permissions: contents: read`
- `concurrency: group: ci-check-${{ github.ref }}, cancel-in-progress: true`

Job-level changes:
- `change-scope` filter `test-config` line: change `.github/workflows/ci.yml` to `.github/workflows/ci-check.yml`
- All jobs are copied verbatim except `build` (moves to ci-build) and `ci-result` (replaced by ci-check-result in T-2.3)

**Files**: `.github/workflows/ci-check.yml` (CREATE)
**Done**: ci-check.yml exists with 15 validation jobs, correct triggers, concurrency, permissions, paths-ignore

---

### [x] T-2.2: Add build-check dry build job to ci-check.yml

Add a `build-check` job that runs `uv build` without uploading artifacts. Purpose: validate that the package compiles before merge (D-097-09).

Job definition:
- `name: Build Check`
- `needs: [change-scope, lint, duplication, risk-acceptance, typecheck, test-unit, test-integration, test-e2e, sonarcloud, framework-smoke, security, content-integrity, workflow-sanity]` (same deps as current `build` job)
- `if: needs.change-scope.outputs.code == 'true'`
- `runs-on: ubuntu-latest`
- `timeout-minutes: 10`
- Steps: checkout, setup-uv, `uv build` (no upload-artifact step)

**Files**: `.github/workflows/ci-check.yml` (MODIFY -- append job)
**Done**: `build-check` job exists in ci-check.yml, runs `uv build`, does NOT upload artifacts, depends on all validation jobs

---

### [x] T-2.3: Add ci-check-result aggregation job

Adapt the current `ci-result` job from ci.yml as `ci-check-result` in ci-check.yml. Keep the aggregation job `name:` as `CI Result` to preserve branch protection status check compatibility (avoids Risk R1).

Changes from current ci-result:
- Job ID: `ci-check-result` (internal), Name: `CI Result` (displayed)
- `needs:` list: replace `build` with `build-check` in the needs array
- `code_conditional` array: replace `"build:${{ needs.build.result }}"` with `"build-check:${{ needs.build-check.result }}"`
- Remove any reference to the old `build` job

**Files**: `.github/workflows/ci-check.yml` (MODIFY -- append job)
**Done**: `ci-check-result` job exists with `name: CI Result`, handles build-check as code-conditional, all 4 tiers (always-required, code-conditional, PR-only, optional) preserved

---

### [x] T-2.4: Create ci-build.yml with workflow_run trigger

Create `.github/workflows/ci-build.yml` that triggers via `workflow_run` when CI Check completes successfully on main.

Workflow-level configuration:
- `name: CI Build`
- Trigger:
  ```yaml
  on:
    workflow_run:
      workflows: ["CI Check"]
      types: [completed]
      branches: [main]
  ```
- `permissions: contents: read`
- No concurrency needed (single-fire per ci-check success)

Jobs:
- `build`:
  - `name: Build Package`
  - `if: github.event.workflow_run.conclusion == 'success'` (critical: workflow_run fires on any conclusion)
  - `runs-on: ubuntu-latest`
  - `timeout-minutes: 10`
  - Steps:
    1. `actions/checkout@v6` with `ref: ${{ github.event.workflow_run.head_sha }}` (exact commit tracking, D-097-02)
    2. `astral-sh/setup-uv` (SHA-pinned, same version as ci-check)
    3. `uv build`
    4. `actions/upload-artifact@v7` with `name: dist`, `path: dist/`, `retention-days: 90` (D-097-07)

**Files**: `.github/workflows/ci-build.yml` (CREATE)
**Done**: ci-build.yml exists, triggers only on CI Check success on main, uses head_sha for checkout, uploads dist artifact with 90-day retention, passes all policy checks

---

### [x] T-2.5: Update release.yml verify-ci reference

Change the `verify-ci` job in `release.yml` to reference the new build workflow. Update line 37: change `--workflow=ci.yml` to `--workflow=ci-build.yml`.

Rationale: release.yml downloads the `dist` artifact from the CI run. ci-build.yml is the workflow that produces this artifact. Referencing `ci-check.yml` would find the validation run but NOT the artifact (ci-check has no upload step). ci-build.yml is correct.

Note: After this change, releases require ci-build.yml to have run successfully at least once. This is safe because the merge commit triggers ci-check -> ci-build automatically.

**Files**: `.github/workflows/release.yml` (MODIFY line 37)
**Done**: `gh run list --workflow=ci-build.yml` in release.yml verify-ci job

---

### [x] T-2.6: Update check_workflow_policy.py _FIRST_PARTY_PREFIXES

Add all Actions allowlist organizations to `_FIRST_PARTY_PREFIXES` tuple on line 19.

Current: `("actions/",)`
New: `("actions/", "github/", "pypa/", "astral-sh/", "SonarSource/", "CycloneDX/", "EndBug/", "dorny/")`

These match the allowlist from D-097-01 / T-1.4. Actions from these orgs are trusted and do not require SHA pinning (though they currently use it). Adding them prevents future false positives if any of these orgs switch from SHA to tag references.

**Files**: `scripts/check_workflow_policy.py` (MODIFY line 19)
**Done**: `_FIRST_PARTY_PREFIXES` contains all 8 org prefixes

---

### [x] T-2.7: Verify branch protection status checks

Verify that branch protection still works after the workflow split. Since T-2.3 preserves the job `name: CI Result`, the required status check name does NOT change. No `gh api` update is needed.

Verification steps:
1. Confirm ci-check.yml's `ci-check-result` job has `name: CI Result`
2. Confirm that the deprecated ci.yml (workflow_dispatch only) no longer produces a `CI Result` status (it won't run on PR/push)
3. Confirm no naming collision between ci-check and ci-build status checks

**Files**: none (verification only)
**Done**: Branch protection continues to require `CI Result` status check, which is now produced by ci-check.yml

---

### [x] T-2.8: Deprecate ci.yml (disable triggers)

Modify ci.yml to disable its PR and push triggers. Replace with `workflow_dispatch` only to prevent duplicate runs while preserving the file for Phase 6 deletion.

Changes:
1. Add deprecation comment at top: `# DEPRECATED: Retained for transition. See ci-check.yml and ci-build.yml. Will be deleted in Phase 6 (sub-006).`
2. Replace triggers:
   ```yaml
   on:
     workflow_dispatch:  # Manual only — triggers disabled for transition
   ```
3. Keep all jobs intact (no structural changes) so the file remains valid YAML and passes actionlint/policy checks.
4. Remove `concurrency` block (no longer needed without PR trigger; also avoids policy check failure since concurrency is only required for `pull_request` triggers).

**Files**: `.github/workflows/ci.yml` (MODIFY triggers + add comment)
**Done**: ci.yml has `workflow_dispatch` only trigger, deprecation comment at top, passes policy checks

---

### [x] T-2.9: Verify all workflows pass policy checks

Run `python scripts/check_workflow_policy.py` to verify that all 5 workflow files pass all policy checks:
1. No `pull_request_target`
2. Top-level `permissions` present
3. Every job has `timeout-minutes`
4. `concurrency` present when `pull_request` trigger exists
5. Third-party SHA pinning (with updated `_FIRST_PARTY_PREFIXES`)

Also run `actionlint` on the new workflow files if available.

**Files**: none (verification only)
**Done**: `check_workflow_policy.py` reports "workflow policy check passed (5 workflow files)" with zero failures

## Execution Order

T-2.1 -> T-2.2 -> T-2.3 (sequential: building ci-check.yml incrementally)
T-2.4 (independent: ci-build.yml is a separate file)
T-2.5 (depends on T-2.4: must know the workflow name)
T-2.6 (independent: policy script update)
T-2.8 (depends on T-2.1: ci-check.yml must exist before disabling ci.yml)
T-2.7 (depends on T-2.3 + T-2.8: verify after both are done)
T-2.9 (depends on ALL: final verification)

Parallelizable groups:
- Group A: T-2.1 + T-2.2 + T-2.3 (sequential within group)
- Group B: T-2.4, T-2.5, T-2.6 (parallel with each other, parallel with Group A)
- Group C: T-2.8 (after Group A)
- Group D: T-2.7, T-2.9 (after everything)

## Self-Report

### Deliverables

| Task | Status | Deliverable | Classification |
|------|--------|-------------|----------------|
| T-2.1 | DONE | `.github/workflows/ci-check.yml` created with 15 validation jobs | CREATE |
| T-2.2 | DONE | `build-check` job appended to ci-check.yml (dry build, no artifact upload) | CREATE |
| T-2.3 | DONE | `ci-check-result` job appended with `name: CI Result` (branch protection preserved) | CREATE |
| T-2.4 | DONE | `.github/workflows/ci-build.yml` created with `workflow_run` trigger | CREATE |
| T-2.5 | DONE | `release.yml` verify-ci references `ci-build.yml` (line 37) | MODIFY |
| T-2.6 | DONE | `_FIRST_PARTY_PREFIXES` expanded to 8 org prefixes (linter auto-formatted to multi-line) | MODIFY |
| T-2.7 | DONE | Branch protection verified: `CI Result` name preserved in ci-check.yml, ci.yml no longer triggers on PR/push | VERIFY |
| T-2.8 | DONE | ci.yml triggers set to `workflow_dispatch` only, deprecation comment added, concurrency removed | MODIFY |
| T-2.9 | DONE | `check_workflow_policy.py` passes: "workflow policy check passed (7 workflow files)" | VERIFY |

### Key Decisions

1. **Emoji removal in ci-check-result**: The `ci-result` job in ci.yml used unicode checkmark/cross characters in echo statements. These were replaced with plain text (`FAIL:`, `PASSED`, `FAILED`) to avoid encoding issues across runner environments.
2. **Linter auto-format**: `_FIRST_PARTY_PREFIXES` was auto-formatted from a single-line tuple to multi-line by ruff. This is correct and preferred style.
3. **change-scope self-reference**: Updated from `.github/workflows/ci.yml` to `.github/workflows/ci-check.yml` in the `test-config` filter so CI re-runs full tests when the new workflow itself changes.

### Verification

- Policy check: 7/7 workflow files pass all 5 policy rules
- Branch protection: `CI Result` status check name preserved (ci-check-result job `name:` field)
- No duplicate triggers: ci.yml reduced to `workflow_dispatch` only
- ci-build.yml: `workflow_run` trigger with `conclusion == 'success'` guard and `head_sha` checkout
