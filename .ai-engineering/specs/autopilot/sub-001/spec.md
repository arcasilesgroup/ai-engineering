---
id: sub-001
parent: spec-097
title: "GitHub Repository Hardening"
status: planning
files: [".github/CODEOWNERS"]
depends_on: []
---

# Sub-Spec 001: GitHub Repository Hardening

## Scope

Configure GitHub repository security settings to close critical gaps: branch protection (1 required approval, code owner review, enforce for admins, last-push approval), tag protection ruleset (`v*` restricted to maintainers), PyPI environment restrictions (branch restriction to main, no admin bypass), Actions allowlist, and expired secret rotation. All changes via `gh api` — no workflow or code changes. Covers spec-097 Phase 1 and decision D-097-08.

## Exploration

### Existing Files

**Branch protection (main)** — queried via `gh api repos/arcasilesgroup/ai-engineering/branches/main/protection`:

| Setting | Current value | Target value |
|---------|--------------|--------------|
| `required_approving_review_count` | 0 | 1 |
| `require_code_owner_reviews` | false | true |
| `dismiss_stale_reviews` | true | true (already set) |
| `require_last_push_approval` | false | true |
| `enforce_admins` | false | true |
| Required status checks | `install-smoke`, `CI Result` (strict: true) | No change |
| Allow force pushes | false | No change |
| Allow deletions | false | No change |

**Rulesets** — queried via `gh api repos/arcasilesgroup/ai-engineering/rulesets`:

One active ruleset exists (id: `12465638`, name: `main`):
- Target: branch, condition: `~DEFAULT_BRANCH`
- Rules: deletion, non_fast_forward, copilot_code_review (review_on_push: true), code_quality (severity: errors)
- No tag protection ruleset exists. A new ruleset must be created for `v*` tags.

**Environments** — queried via `gh api repos/arcasilesgroup/ai-engineering/environments`:

| Environment | `can_admins_bypass` | `protection_rules` | `deployment_branch_policy` |
|------------|--------------------|--------------------|---------------------------|
| `pypi` | true | none | null (unrestricted) |
| `copilot` | true | none | null (unrestricted) |

PyPI needs: `can_admins_bypass: false`, deployment branch policy restricted to `main` only.

**Actions permissions** — queried via `gh api repos/arcasilesgroup/ai-engineering/actions/permissions`:

```json
{"enabled": true, "allowed_actions": "all", "sha_pinning_required": false}
```

Currently all actions are allowed. Must change to `selected` with an explicit allowlist of trusted orgs: `actions/*`, `github/*`, `pypa/*`, `astral-sh/*`, `SonarSource/*`, `CycloneDX/*`, `EndBug/*`, `dorny/*`.

**Secrets** — queried via `gh secret list`:

| Secret | Last updated |
|--------|-------------|
| `SNYK_TOKEN` | 2026-03-10 |
| `SONAR_TOKEN` | 2026-03-09 |
| `WIKI_PAT` | 2026-02-05 |

`WIKI_PAT` was last updated 2026-02-05. The spec calls for rotation or deletion of this expired secret. No workflow references `WIKI_PAT` in any `.github/workflows/*.yml` file, so it is safe to delete.

**CODEOWNERS** — `.github/CODEOWNERS` exists and assigns `@arcasilesgroup/ai-engineering-maintainers` to all critical paths (`.ai-engineering/`, `src/`, `tests/`, `.github/workflows/`, `.claude/skills/`, `.claude/agents/`, root governance files, security config). No changes needed.

**Collaborators** — 4 users: `soydachi`, `crystian`, `tamasi17`, `CarmenTajuelo`. With 1 required approval, any member can unblock another.

### Patterns to Follow

**Branch protection update** — `PUT /repos/{owner}/{repo}/branches/{branch}/protection`:
- This is a full replacement API (not a patch). Must send all existing settings plus the changes.
- Endpoint: `gh api repos/arcasilesgroup/ai-engineering/branches/main/protection --method PUT`
- Must include `required_status_checks` with current checks to avoid wiping them.

**Tag protection ruleset** — `POST /repos/{owner}/{repo}/rulesets`:
- Target: `tag`, conditions: `ref_name.include: ["v*"]`
- Rules: `[{"type": "tag_name_pattern", "parameters": {"name": "v*", "negate": false}}]` is not needed; instead use `creation` rule type with bypass actors restricted to maintainer role.
- Bypass actors: restrict to `organization_admin` and `repository_admin` roles (or specific team).

**Environment configuration** — Two sequential API calls:
1. `PUT /repos/{owner}/{repo}/environments/{name}` to set `prevent_self_review: false` and configure reviewers/wait timers if needed, and set deployment branch policy type.
2. `POST /repos/{owner}/{repo}/environments/{name}/deployment-branch-policies` to add `main` as the only allowed branch.
- The deployment branch policy must first be enabled via the environment PUT (setting `deployment_branch_policy.protected_branches: false, custom_branch_policies: true`), then individual policies are added via POST.

**Actions allowlist** — Two sequential API calls:
1. `PUT /repos/{owner}/{repo}/actions/permissions` with `{"enabled": true, "allowed_actions": "selected"}`
2. `PUT /repos/{owner}/{repo}/actions/permissions/selected-actions` with `{"github_owned_allowed": true, "verified_allowed": false, "patterns_allowed": ["pypa/*", "astral-sh/*", "SonarSource/*", "CycloneDX/*", "EndBug/*", "dorny/*"]}`
- Note: `github_owned_allowed: true` covers both `actions/*` and `github/*` orgs. The `patterns_allowed` array covers third-party verified actions.

**Secret deletion** — `gh secret delete WIKI_PAT --repo arcasilesgroup/ai-engineering`

### Dependencies Map

| Downstream sub-spec | Dependency on sub-001 |
|---------------------|----------------------|
| sub-002 (Workflow Architecture Split) | None (independent -- Wave 1 parallel) |
| sub-003 (Version & Commit Modernization) | None (depends on sub-002 only) |
| sub-004 (Supply Chain Security) | None (depends on sub-002 only) |
| sub-005 (Artifact-Driven Release) | None (depends on sub-003, sub-004) |
| sub-006 (Cleanup & Decision Persistence) | Depends on sub-001 -- will verify hardening settings are active and persist D-097-08 to decision-store.json |

Sub-001 is a leaf dependency -- only sub-006 depends on it. No other sub-spec is blocked by sub-001, and sub-001 blocks nothing in Waves 2-3. This makes it safe to execute independently.

### Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| **R1: Required approvals block solo maintainer** | Cannot merge without a second reviewer. With 4 collaborators, availability is reasonable but not guaranteed during holidays/weekends. | 4 collaborators available. Admin enforcement is intentional -- security outweighs convenience for a regulated-industry framework. |
| **R2: Branch protection PUT is a full replacement** | Sending incomplete data could wipe existing status checks (`install-smoke`, `CI Result`) or other settings. | Build the full payload from the current GET response, changing only the target fields. Verify after applying. |
| **R3: Actions allowlist blocks a used action** | If any workflow uses an action outside the allowlist, CI will break immediately. | Audit all `uses:` references across workflows. Current actions used: `actions/*`, `astral-sh/*`, `dorny/*`, `SonarSource/*`, `EndBug/*`, `pypa/*`. All are covered by the allowlist. `CycloneDX/*` and `github/*` are not yet used but will be needed by sub-004. |
| **R4: Environment branch restriction breaks release workflow** | If `release.yml` deploys from a non-main branch, restricting PyPI to main-only would block it. | Current `release.yml` triggers on `push` to tags (`v*`) which runs on main. Future `release.yml` (sub-005) uses `workflow_dispatch` on main. Both are compatible. |
| **R5: WIKI_PAT deletion breaks something unknown** | Secret might be used outside tracked workflows (e.g., scheduled job, external integration). | No workflow references `WIKI_PAT`. Name suggests wiki publishing -- GitHub wikis use repo-level access, not PATs. Safe to delete; if something breaks it will surface quickly and the secret can be recreated. |
