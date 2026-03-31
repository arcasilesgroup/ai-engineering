---
total: 6
completed: 6
---

# Plan: sub-001 GitHub Repository Hardening

## Plan

### T-1.1: Configure branch protection on main [x]

Update branch protection via `PUT /repos/arcasilesgroup/ai-engineering/branches/main/protection`. The payload must be a complete replacement that preserves existing settings while changing the target fields.

**Payload** (changes highlighted with `<-- CHANGE`):

```json
{
  "required_status_checks": {
    "strict": true,
    "contexts": ["install-smoke", "CI Result"]
  },
  "enforce_admins": true,
  "required_pull_request_reviews": {
    "dismiss_stale_reviews": true,
    "require_code_owner_reviews": true,
    "require_last_push_approval": true,
    "required_approving_review_count": 1
  },
  "restrictions": null,
  "required_linear_history": false,
  "allow_force_pushes": false,
  "allow_deletions": false,
  "block_creations": false,
  "required_conversation_resolution": false,
  "lock_branch": false,
  "allow_fork_syncing": false
}
```

**Verification**: `gh api repos/arcasilesgroup/ai-engineering/branches/main/protection` and confirm:
- `required_pull_request_reviews.required_approving_review_count` == 1
- `required_pull_request_reviews.require_code_owner_reviews` == true
- `required_pull_request_reviews.require_last_push_approval` == true
- `enforce_admins.enabled` == true
- `required_status_checks.contexts` still contains `install-smoke` and `CI Result`

**Files**: (none -- API only)
**Done**: All 5 branch protection fields match target values in GET response.

---

### T-1.2: Create tag protection ruleset for `v*` [x]

Create a new repository ruleset via `POST /repos/arcasilesgroup/ai-engineering/rulesets` that restricts tag creation matching `v*` to repository admins only.

**Payload**:

```json
{
  "name": "tag-protection-v",
  "target": "tag",
  "enforcement": "active",
  "conditions": {
    "ref_name": {
      "include": ["v*"],
      "exclude": []
    }
  },
  "rules": [
    { "type": "creation" },
    { "type": "update" },
    { "type": "deletion" }
  ],
  "bypass_actors": [
    {
      "actor_id": 5,
      "actor_type": "RepositoryRole",
      "bypass_mode": "always"
    }
  ]
}
```

Note: `actor_id: 5` corresponds to the `admin` repository role. Only admins can create, update, or delete `v*` tags. All other users (including `write` role) are blocked.

**Verification**: `gh api repos/arcasilesgroup/ai-engineering/rulesets` returns 2 rulesets (existing `main` + new `tag-protection-v`). The new ruleset target is `tag`, enforcement is `active`, and conditions include `v*`.

**Files**: (none -- API only)
**Done**: Ruleset `tag-protection-v` is active and `gh api` confirms `v*` tags are restricted to admins.

---

### T-1.3: Configure PyPI environment restrictions [x]

Two sequential API calls:

**Step 1**: Update the PyPI environment to disable admin bypass and enable custom branch policies.

`PUT /repos/arcasilesgroup/ai-engineering/environments/pypi`:

```json
{
  "deployment_branch_policy": {
    "protected_branches": false,
    "custom_branch_policies": true
  },
  "prevent_self_review": false
}
```

**Step 2**: Add `main` as the only allowed deployment branch.

`POST /repos/arcasilesgroup/ai-engineering/environments/pypi/deployment-branch-policies`:

```json
{
  "name": "main",
  "type": "branch"
}
```

Note: The environment PUT endpoint does not support `can_admins_bypass` directly in all API versions. If the field is not accepted, the admin bypass setting must be configured via the GitHub UI. Verify after applying.

**Verification**: `gh api repos/arcasilesgroup/ai-engineering/environments/pypi` shows:
- `deployment_branch_policy` is not null
- `deployment_branch_policy.custom_branch_policies` == true
- `gh api repos/arcasilesgroup/ai-engineering/environments/pypi/deployment-branch-policies` lists exactly 1 policy for `main`

**Files**: (none -- API only)
**Done**: PyPI environment is restricted to main-only deployments with deployment branch policy active.

---

### T-1.4: Configure Actions allowlist [x]

Two sequential API calls:

**Step 1**: Switch from `all` to `selected` actions.

`PUT /repos/arcasilesgroup/ai-engineering/actions/permissions`:

```json
{
  "enabled": true,
  "allowed_actions": "selected"
}
```

**Step 2**: Set the specific allowlist.

`PUT /repos/arcasilesgroup/ai-engineering/actions/permissions/selected-actions`:

```json
{
  "github_owned_allowed": true,
  "verified_allowed": false,
  "patterns_allowed": [
    "pypa/*",
    "astral-sh/*",
    "SonarSource/*",
    "CycloneDX/*",
    "EndBug/*",
    "dorny/*"
  ]
}
```

Note: `github_owned_allowed: true` covers both `actions/*` and `github/*` organizations. `CycloneDX/*` is not currently used but is pre-approved for sub-004 (supply chain SBOM generation). All currently used actions are covered by this allowlist.

**Verification**:
- `gh api repos/arcasilesgroup/ai-engineering/actions/permissions` shows `allowed_actions: "selected"`
- `gh api repos/arcasilesgroup/ai-engineering/actions/permissions/selected-actions` shows `github_owned_allowed: true` and all 6 patterns in `patterns_allowed`
- Trigger a CI run (or check existing queued runs) to confirm workflows are not blocked

**Files**: (none -- API only)
**Done**: Actions permissions show `selected` with all 6 patterns plus `github_owned_allowed: true`.

---

### T-1.5: Delete expired WIKI_PAT secret [x]

Delete the expired `WIKI_PAT` secret that was last updated 2026-02-05. No workflow in `.github/workflows/` references this secret.

**Command**: `gh secret delete WIKI_PAT --repo arcasilesgroup/ai-engineering`

**Pre-check**: Confirm no workflow uses `WIKI_PAT`:
```
grep -r "WIKI_PAT" .github/workflows/  # expect: no matches
```

**Verification**: `gh secret list --repo arcasilesgroup/ai-engineering` shows only `SNYK_TOKEN` and `SONAR_TOKEN`.

**Files**: (none -- API only)
**Done**: `WIKI_PAT` no longer appears in `gh secret list`.

---

### T-1.6: Verify all hardening settings [x]

Run a comprehensive verification pass to confirm every setting from T-1.1 through T-1.5 is correctly applied. This is the final gate before marking sub-001 complete.

**Verification commands** (all must pass):

1. Branch protection:
   ```
   gh api repos/arcasilesgroup/ai-engineering/branches/main/protection \
     --jq '{
       approvals: .required_pull_request_reviews.required_approving_review_count,
       code_owners: .required_pull_request_reviews.require_code_owner_reviews,
       dismiss_stale: .required_pull_request_reviews.dismiss_stale_reviews,
       last_push: .required_pull_request_reviews.require_last_push_approval,
       enforce_admins: .enforce_admins.enabled,
       status_checks: .required_status_checks.contexts
     }'
   ```
   Expected: `approvals: 1, code_owners: true, dismiss_stale: true, last_push: true, enforce_admins: true, status_checks: ["install-smoke", "CI Result"]`

2. Tag protection: `gh api repos/arcasilesgroup/ai-engineering/rulesets --jq '.[].name'` includes `tag-protection-v`

3. PyPI environment: `gh api repos/arcasilesgroup/ai-engineering/environments/pypi --jq '.deployment_branch_policy'` is not null

4. Actions: `gh api repos/arcasilesgroup/ai-engineering/actions/permissions --jq '.allowed_actions'` == `selected`

5. Secrets: `gh secret list --repo arcasilesgroup/ai-engineering` does not contain `WIKI_PAT`

**Files**: (none -- API only)
**Done**: All 5 verification checks pass. Sub-001 is complete.

## Confidence

**Level: HIGH (90%)**

Rationale:
- All GitHub API endpoints are well-documented and stable (REST API v3).
- Current state is fully understood from API exploration.
- The `gh` CLI is installed and authenticated with admin permissions.
- CODEOWNERS is already correctly configured -- no file changes needed.
- The only risk area is the environment `can_admins_bypass` setting, which may require the GitHub UI if the API does not accept it in all versions. This is a minor configuration gap, not a blocker.
- All currently used actions are covered by the allowlist -- no CI breakage expected.
- `WIKI_PAT` is confirmed unused in all workflows -- safe to delete.
- 4 collaborators are available, so requiring 1 approval does not create a bottleneck.

## Self-Report

### Task Classifications

| Task | Classification | Evidence |
|------|---------------|----------|
| T-1.1 | real | `gh api` PUT returned full protection object with target values; GET verification confirmed approvals=1, code_owners=true, last_push=true, enforce_admins=true |
| T-1.2 | real | `gh api` POST returned ruleset id=14560846 with name=`tag-protection-v`, target=tag, enforcement=active; GET rulesets lists both `main` and `tag-protection-v` |
| T-1.3 | real | `gh api` PUT returned environment with deployment_branch_policy.custom_branch_policies=true; POST returned branch policy id=46048811 for main; GET confirms main is sole allowed branch |
| T-1.4 | real | `gh api` PUT (both steps) returned 204; GET confirms allowed_actions=selected, github_owned_allowed=true, 6 patterns in patterns_allowed |
| T-1.5 | real | `gh secret delete` returned success; `gh secret list` shows only SNYK_TOKEN and SONAR_TOKEN -- WIKI_PAT is absent |
| T-1.6 | real | All 5 verification queries returned expected values matching spec targets |

### Deviations from Plan

1. **T-1.2 pattern format**: The plan specified `"include": ["v*"]` but the GitHub Rulesets API rejected this as an invalid target pattern. The correct format is `"include": ["refs/tags/v*"]` for tag rulesets. Fixed on second attempt.
2. **T-1.3 prevent_self_review**: The plan included `"prevent_self_review": false` in the environment PUT payload. The API rejected this because `prevent_self_review` requires at least one reviewer to be configured. Omitted the field -- the setting defaults to false when no reviewers are set.
3. **T-1.3 can_admins_bypass**: Remains `true` as the API does not support setting this field directly (as noted in the plan's risk section). Requires GitHub UI configuration. This is a known limitation, not a failure.

### Summary

All 6 tasks completed successfully. Repository hardening is fully applied via API. The only remaining manual action is toggling `can_admins_bypass` to `false` for the PyPI environment via the GitHub UI (documented in spec as an acceptable gap).
