# Universal Git Conventions

These conventions govern how every project uses Git, regardless of technology stack. Consistent git practices make collaboration predictable, history useful, and automation reliable. Every AI assistant and human engineer must follow these rules.

---

## Conventional Commits

All commit messages must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. This enables automated changelogs, semantic versioning, and clear project history.

### Format

```
<type>(<scope>): <description>

[optional body]

[optional footer(s)]
```

### Types

| Type | When to Use |
|---|---|
| `feat` | A new feature visible to the user |
| `fix` | A bug fix |
| `docs` | Documentation only changes |
| `style` | Formatting, missing semicolons, whitespace — no logic changes |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `perf` | Performance improvement |
| `test` | Adding or correcting tests |
| `build` | Changes to build system or external dependencies |
| `ci` | Changes to CI/CD configuration |
| `chore` | Maintenance tasks (dependency bumps, config changes) |
| `revert` | Reverting a previous commit |

### Scope

The scope is optional but encouraged. It identifies the area of the codebase affected:

- `feat(auth): add MFA support for TOTP`
- `fix(payments): correct tax calculation for EU customers`
- `refactor(api): extract validation middleware`
- `ci(github): add dependency scanning to PR workflow`

### Description

- Use the imperative mood: "add feature" not "added feature" or "adds feature."
- Do not capitalize the first letter.
- Do not end with a period.
- Keep it under 72 characters.

### Body

- Separate from the description with a blank line.
- Explain **what** and **why**, not **how** (the diff shows how).
- Wrap at 72 characters.
- Reference related issues or tickets.

### Footer

- Use `BREAKING CHANGE:` for breaking changes. This triggers a major version bump in semantic versioning.
- Reference issues: `Closes #42`, `Fixes #108`, `Refs PROJ-456`.
- Co-authorship: `Co-Authored-By: Name <email>`.

### Examples

```
feat(cart): add quantity selector to product detail page

Users can now adjust item quantity before adding to cart.
Previously, items were always added with quantity 1.

Closes #215
```

```
fix(auth): prevent session fixation on login

Regenerate session ID after successful authentication to prevent
session fixation attacks. The previous implementation reused the
pre-auth session.

Refs SECURITY-042
```

```
refactor(db): migrate from raw SQL to query builder

Replace hand-written SQL strings with typed query builder calls.
This eliminates a class of SQL injection risks and improves
maintainability without changing any behavior.

BREAKING CHANGE: DatabaseService.rawQuery() has been removed.
Use DatabaseService.query() with the builder API instead.
```

```
chore(deps): update eslint from 8.45.0 to 9.0.0
```

---

## Branch Naming Conventions

All branch names use lowercase with hyphens as separators. Include a category prefix and a brief description.

### Format

```
<category>/<ticket-id>-<short-description>
```

### Categories

| Prefix | Purpose |
|---|---|
| `feature/` | New features |
| `fix/` | Bug fixes |
| `hotfix/` | Urgent production fixes |
| `release/` | Release preparation |
| `dev/` | Exploratory or developer-specific work |
| `docs/` | Documentation updates |
| `refactor/` | Code restructuring without behavior changes |
| `test/` | Test additions or corrections |
| `ci/` | CI/CD pipeline changes |

### Examples

```
feature/PROJ-123-user-onboarding-flow
fix/PROJ-456-login-timeout-handling
hotfix/PROJ-789-payment-double-charge
release/2.1.0
dev/spike-graphql-migration
docs/update-api-authentication-guide
refactor/extract-notification-service
```

### Rules

- Keep branch names under 60 characters total.
- Use only lowercase letters, numbers, hyphens, and forward slashes.
- Always include the ticket ID when one exists.
- Do not use personal names in shared branch names (`john/feature-x` is not acceptable on shared repositories; use `feature/PROJ-123-feature-x`).
- Delete branches after merging. Do not reuse branch names.

---

## Compliance Branches

### Branch Roles

| Branch | Role | Deploy Target |
|---|---|---|
| `main` (or `master`) | Production-ready code | Production |
| `develop` | Integration branch for next release | Staging |
| `release/*` | Release stabilization | Pre-production/QA |
| `hotfix/*` | Emergency production fixes | Production (fast-tracked) |

### Rules

- `main` always reflects what is deployed in production. Every commit on `main` must be deployable.
- `develop` is the integration branch. Feature branches merge into `develop`. When `develop` is stable and ready for release, it merges into a `release/*` branch or directly into `main`.
- `release/*` branches are created from `develop` when preparing a release. Only bug fixes, documentation, and release-specific changes are allowed on release branches. When complete, merge into both `main` and `develop`.
- `hotfix/*` branches are created from `main` to address critical production issues. When complete, merge into both `main` and `develop`.

---

## Protected Branch Rules

The following protections must be configured on `main` and `develop`:

### Required Protections

- **Require pull request reviews**: Minimum 1 approval (2 for `main` in team settings).
- **Require status checks to pass**: CI build, test suite, linting, and security scans must all pass.
- **Require branches to be up to date**: The branch must be rebased or merged with the target before merging.
- **Require signed commits**: Recommended for `main` in high-security environments.
- **Require linear history**: Enforce squash or rebase merges to keep history clean.
- **Do not allow bypassing the above settings**: Not even for administrators.

### Enforcement

- Configure these rules in the repository settings (GitHub Branch Protection, GitLab Protected Branches, or equivalent).
- Audit protection rules quarterly. Ensure no drift has occurred.
- Document any temporary exceptions with a ticket number and expiration date.

---

## Pull Request Workflow

### PR Description Template

Every PR must include the following sections:

```markdown
## What

[One-paragraph summary of the changes.]

## Why

[Explain the motivation. Link to the issue or design document.]

## How

[Brief description of the technical approach, if not obvious from the diff.]

## Testing

[Describe how the changes were tested. Include manual test steps if applicable.]

## Checklist

- [ ] Tests added/updated
- [ ] Documentation updated (if applicable)
- [ ] No secrets or credentials in the diff
- [ ] Self-review completed
- [ ] Breaking changes documented
```

### Review Process

1. **Author self-reviews** the diff before requesting review. Check for debug artifacts, commented-out code, and accidental file inclusions.
2. **Assign reviewers** who have context on the affected area. At least one reviewer must be a code owner.
3. **Reviewers respond within 1 business day.** If a review will take longer, acknowledge receipt and set expectations.
4. **Address all comments.** Resolve conversations explicitly — do not leave open threads. If you disagree with feedback, discuss it; do not silently ignore it.
5. **Re-request review** after significant changes.
6. **Merge only when all checks pass** and required approvals are obtained.

### PR Size

- Aim for PRs under 400 lines of diff (excluding generated files and lock files).
- If a change is larger, break it into stacked PRs or incremental changes.
- Large PRs are harder to review, more likely to introduce bugs, and slower to merge.

---

## Merge Strategies

### Feature Branches into Develop/Main

Use **squash merge**. This produces a single, clean commit on the target branch with the full PR context in the commit message.

- The squash commit message should follow conventional commit format.
- Include the PR number: `feat(auth): add MFA support (#234)`.
- The full commit history is preserved in the PR for reference.

### Release Branches into Main

Use **merge commit** (no fast-forward). This preserves the release branch history and creates a clear merge point that can be tagged.

### Hotfix Branches into Main and Develop

Use **merge commit** into `main`. Then merge `main` into `develop` (or cherry-pick the hotfix) to keep branches in sync.

### Rebase

- Use `git rebase` to keep a feature branch up to date with its target. This avoids unnecessary merge commits in the feature branch.
- **Never rebase a branch that has been pushed and is being reviewed.** Rewriting public history causes conflicts for other contributors.
- If in doubt, merge instead of rebasing.

---

## Git Hygiene

### Commit Practices

- **Make small, atomic commits.** Each commit should represent a single logical change that compiles and passes tests.
- **Write meaningful messages.** Every commit message should explain what changed and why, following the conventional commit format.
- **Do not commit work-in-progress to shared branches.** Use local branches or draft PRs for incomplete work.
- **Do not commit generated files** (build output, compiled assets) unless they are required for deployment and documented in the README.
- **Do not commit large binary files.** Use Git LFS for binaries over 1 MB, or store them externally.

### .gitignore

- Maintain a comprehensive `.gitignore` at the repository root.
- Include IDE files, OS files, build output, dependency directories, `.env` files, and local configuration.
- Use language-specific `.gitignore` templates as a starting point (available at github/gitignore).
- Never force-add a file that is gitignored without team consensus.

### History

- Do not amend or rebase commits that have been pushed to a shared branch.
- If you must fix a mistake in a pushed commit, create a new commit with the fix (or use `git revert` for undoing).
- Preserve meaningful history. Do not squash an entire feature branch's history if individual commits are valuable for understanding the evolution.

---

## Forbidden Actions

The following actions are **never** permitted without explicit, documented authorization from a repository administrator:

| Action | Why It Is Forbidden |
|---|---|
| `git push --force` to `main` or `develop` | Rewrites shared history, causes data loss for all collaborators |
| Direct commit to `main` | Bypasses review, CI, and quality gates |
| Direct commit to `develop` (in team settings) | Bypasses review and integration testing |
| Deleting protected branches | Destroys the primary integration point |
| Merging without passing CI checks | Introduces unverified code into the shared codebase |
| Committing secrets or credentials | Permanent security compromise (even after removal from history) |
| Using `git reset --hard` on shared branches | Rewrites history and causes divergence |

If any of these actions were performed accidentally, notify the team immediately. For secret exposure, rotate the compromised credentials before doing anything else.

---

## Stale Branch Cleanup

- Delete feature branches immediately after merging. Configure the repository to auto-delete merged branches.
- Branches with no activity for 30 days should be reviewed. The author must either merge, rebase and continue, or delete.
- Branches with no activity for 90 days should be deleted after confirming with the author.
- Run a monthly audit of open branches. Use `git branch -r --sort=-committerdate` or repository tooling to identify stale branches.
- Tag the branch tip before deleting if you want to preserve a reference: `git tag archive/<branch-name> <branch-name>`.

---

## Tagging and Versioning

### Semantic Versioning (SemVer)

All projects use [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH
```

| Component | Increment When |
|---|---|
| MAJOR | Breaking changes to the public API |
| MINOR | New features that are backward-compatible |
| PATCH | Backward-compatible bug fixes |

Pre-release versions use a hyphen suffix: `2.1.0-beta.1`, `3.0.0-rc.1`.

### Tagging Rules

- Create an annotated tag for every release: `git tag -a v2.1.0 -m "Release 2.1.0"`.
- Tag names use the `v` prefix: `v1.0.0`, `v2.3.1`, `v3.0.0-beta.1`.
- Tags must point to commits on `main` (or the release branch if using GitFlow).
- Never delete or move a published tag. If a release is defective, create a new patch release.
- Push tags explicitly: `git push origin v2.1.0` or `git push origin --tags`.

### Changelog

- Maintain a `CHANGELOG.md` at the repository root.
- Group entries under version headings: `## [2.1.0] - 2026-02-07`.
- Categorize entries: Added, Changed, Deprecated, Removed, Fixed, Security.
- Automate changelog generation from conventional commit messages where possible.

---

## Summary Checklist

| Area | Check |
|---|---|
| Commit message | Follows conventional commits format? |
| Branch name | Uses correct prefix and includes ticket ID? |
| PR | Includes description, linked issue, and checklist? |
| PR size | Under 400 lines of diff? |
| Merge strategy | Squash for features, merge commit for releases? |
| Protected branches | Rules configured and not bypassed? |
| Secrets | No credentials anywhere in the diff or history? |
| Stale branches | Cleaned up after merge? |
| Tags | Annotated, versioned with semver, on main? |
