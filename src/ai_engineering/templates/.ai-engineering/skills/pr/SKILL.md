---
name: pr
description: "Execute governed PR workflow: conditional spec reset, stage, commit, push, create pull request with auto-complete squash merge."
metadata:
  version: 2.0.0
  tags: [git, pull-request, ci, merge]
  ai-engineering:
    requires:
      bins: [gitleaks, ruff]
      anyBins: [gh, az]
    scope: read-write
    token_estimate: 1400
---

# PR Workflow

## Purpose

Execute the `/pr` governed workflow: conditionally run spec reset, stage, commit, push, create a pull request, and enable auto-complete with squash merge and branch deletion. The `--only` variant creates the PR without spec reset, staging, committing, or pushing first.

## Trigger

- Command: `/pr` or `/pr --only`
- Context: user requests creating a pull request with governance enforcement.

## When NOT to Use

- **Commit-only without PR** — use `/commit --only` instead. PR always creates a pull request.
- **Quick push without PR** — use `/commit` instead for push-only behavior.
- **Draft explorations** (not ready for review) — use `/commit` to push to branch first, then `/pr` when ready.

## Preconditions (MUST verify before proceeding)

- **Required binaries**: `gitleaks`, `ruff` — must be available on PATH.
- **VCS CLI**: At least one of `gh` (GitHub) or `az` (Azure DevOps) — must be available and authenticated.
- Abort with remediation guidance if missing. Run `ai-eng doctor --fix-tools` to auto-install.

## Procedure

### `/pr` (default: conditional spec reset + stage + commit + push + create PR + auto-complete)

0. **Auto-branch from protected** — if current branch is `main` or `master`:
   a. Analyze pending changes (`git diff --stat` + file paths) to infer change type.
   b. Select prefix: `feat/` | `fix/` | `chore/` | `docs/` | `refactor/` based on change type.
   c. Generate a descriptive slug (kebab-case, max 50 chars) from the changes.
   d. Create branch: `git checkout -b <prefix>/<slug>`.
   e. Report: "Auto-created branch: `<branch-name>`" and continue.
   If NOT on a protected branch, skip this step.

1. **Spec reset** (conditional) — run `uv run ai-eng maintenance spec-reset --dry-run`.
   - If a completed active spec is detected: run `uv run ai-eng maintenance spec-reset` and report the summary.
   - If there is no active spec or the active spec is in progress: skip silently.
   - If spec reset fails: report the error and stop.
   - This ensures archived specs and cleared `_active.md` are staged with the PR and reach origin when the PR merges.
2. **Stage changes** — `git add -A` (or selective staging).
3. **Run formatter** — `ruff format .` to auto-fix formatting.
4. **Run linter** — `ruff check . --fix`. If unfixable issues remain, report and stop.
5. **Run secret detection** — `gitleaks protect --staged --no-banner`. If secrets found, report and stop.
6. **Documentation gate** — evaluate and update documentation for OSS GitHub users.
   a. Analyze staged changes and classify documentation scope:
   - **CHANGELOG + README**: new features, breaking changes, new CLI commands, skill/agent additions or removals, config schema changes, architecture changes visible to users.
   - **CHANGELOG only**: any other functional change — src/ modifications, API changes, dependency bumps with behavioral impact, governance surface changes, workflow behavior changes.
   - **No updates needed**: changes with zero functional impact — typo fixes in comments, whitespace-only changes, test-only additions that don't change public behavior, CI config formatting. Log: "Documentation gate evaluated — no functional changes detected."
     b. Update **CHANGELOG.md** (when scope requires it):
   - If `CHANGELOG.md` exists: add entries to `[Unreleased]` section per `skills/changelog/SKILL.md` format. Stage the updated file.
   - If `CHANGELOG.md` does NOT exist: create it following Keep a Changelog format. Stage the new file.
     c. Update **README.md** (when scope includes README):
   - If `README.md` exists AND changes include new features, breaking changes, new CLI commands, or skill catalog changes: update relevant sections. Stage the updated file.
   - If `README.md` does NOT exist AND changes are non-trivial: create it targeting OSS GitHub audience. Stage the new file.
     d. **External documentation portal**:
   - Ask: "Do you have an external documentation portal (docs site, wiki, separate repo)? Provide the repo URL, or 'skip'."
   - If URL provided: clone, branch, update, commit + push + create PR with auto-complete, report URL.
   - If 'skip': continue without external docs.
     e. **Update product-contract.md** (when scope requires it):
   - Evaluate if staged changes affect product contract sections:
     - New skills/agents/stacks: Section 2.2 (Functional Requirements), 3.1 (Stack).
     - Security findings changes: Section 5.4 (Hardening), 7.3 (KPIs).
     - New features/epics completion: Section 7.2 (Active Epics), 7.1 (Roadmap).
     - Coverage/quality metric changes: Section 6.1 (Quality Gates), 7.3 (KPIs).
     - Architecture changes: Section 2.1 (High-Level Solution), 3.1 (Stack).
     - New integrations/providers: Section 2.4 (Integrations).
   - If updates needed: invoke product-contract skill in sync mode for affected sections. Stage the updated file.
   - If no product-contract sections affected: skip silently.
7. **Run pre-push checks** — execute full pre-push gate:
   - `semgrep scan --config auto .`
   - `pip-audit`
   - `pytest tests/ -v`
   - `ty check src/`
     If any check fails, report and stop.
8. **Spec verify** — if an active spec exists, run `ai-eng spec verify` to auto-correct counters.
9. **Spec catalog** — run `ai-eng spec catalog` to regenerate the spec catalog before PR.
10. **Commit** — `git commit -m "<message>"` with well-formed message.
   - If active spec exists: `spec-NNN: Task X.Y — <description>`.
   - Otherwise: conventional commit format.
11. **Push** — `git push origin <current-branch>`.

- If current branch is `main`/`master`, **block** and report protected branch violation.

12. **Detect VCS provider** — determine which CLI to use:
   a. Check `manifest.yml` → `providers.vcs.primary`.
   b. Fallback: parse `git remote get-url origin`:
   - `github.com` → GitHub (`gh`)
   - `dev.azure.com` or `visualstudio.com` → Azure DevOps (`az repos`)
     c. Verify CLI authenticated: `gh auth status` / `az account show`.
13. **Check for existing PR** — query open PRs for current branch:

- **GitHub**: `gh pr list --head <branch> --json number,title,body --state open`
- **Azure DevOps**: `az repos pr list --source-branch <branch> --status active -o json`

14. **Create or update PR**:

- **If NO existing PR** → create new:
  - **GitHub**: `gh pr create --title "<title>" --body "<body>"`
  - **Azure DevOps**: `az repos pr create --source-branch <branch> --target-branch <target> --title "<title>" --description "<body>"`
- **If existing PR found** → extend (NEVER overwrite):
  a. Read existing title and body from the query result.
  b. Compose extended body:
  - Keep entire existing body intact.
  - Append separator: `\n\n---\n\n`
  - Append new section: `## Additional Changes\n\n<new changes summary>`
    c. Update title only if scope significantly expanded (e.g., append ` + <new scope>`). Otherwise keep original.
    d. Apply update:
  - **GitHub**: `gh pr edit <number> --body "<extended_body>"`
  - **Azure DevOps**: `az repos pr update --id <id> --description "<extended_body>"`
    e. Report: "PR #<number> updated — description extended with new changes."

15. **Enable auto-complete** — squash merge with branch deletion:

- **GitHub**: `gh pr merge --auto --squash --delete-branch`
- **Azure DevOps**: `az repos pr update --id <id> --auto-complete true --squash true --delete-source-branch true`

### `/pr --only` (create PR only)

Spec reset is intentionally excluded from `--only` because this mode does not stage/commit/push changes.

1. **Check branch status** — verify current branch is pushed to remote.
   - If NOT pushed: emit warning and propose auto-push.
   - If user accepts: `git push origin <current-branch>`, then continue.
   - If user declines: continue with selected PR handling mode (defer-pr, attempt-pr-anyway, export-pr-payload).
2. **Detect VCS provider** — same detection as step 9 above.
3. **Check for existing PR** — same query as step 10 above.
4. **Create or update PR** — same upsert logic as step 11 above.
5. **Enable auto-complete** — same as step 12 above.

## Output Contract

- Terminal output showing each step's result (pass/fail).
- On success: PR URL displayed with auto-complete status confirmed.
- On failure: specific check that failed with remediation guidance.
- PR includes: title, description, breaking changes (if any), linked spec/task.

## Governance Notes

- Protected branch push is always blocked. No exceptions.
- All pre-push checks (semgrep, pip-audit, pytest, ty) must pass before PR creation.
- Auto-complete with squash merge and branch deletion is mandatory — never skip.
- `gh` or `az` CLI must be installed and authenticated. If not, attempt remediation:
  - GitHub: install `gh`, then `gh auth login`.
  - Azure DevOps: install `az`, then `az login` + `az devops configure --defaults`.
- When updating an existing PR, body content is ALWAYS extended, never replaced.
- Secret detection failure is a hard stop.
- `/pr --only` never hard-fails on unpushed branch — it warns and offers continuation modes.
- Spec reset runs only in `/pr` default flow and only when the active spec is complete.

## PR Structure and Formatting

When creating the PR:

1. **Title** — concise, descriptive, prefixed with type.
   - Format: `type(scope): description` or `spec-NNN: Task X.Y — description`.
   - Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `ci`.
   - Max 72 characters.

2. **Description** — structured body with context.
   - **What**: summarize the changes in 2-3 sentences.
   - **Why**: link to spec, task, or issue. Explain the motivation.
   - **How**: key implementation decisions and trade-offs.
   - **Breaking changes**: list any API or behavior changes that affect consumers.

3. **Checklist** — self-review before requesting review.
   - [ ] Code follows `standards/framework/stacks/python.md`.
   - [ ] Tests added/updated for new behavior.
   - [ ] `ruff check` and `ruff format --check` pass.
   - [ ] `ty check src/` passes.
   - [ ] `pytest` passes with 100% coverage.
   - [ ] No secrets in committed code.
   - [ ] CHANGELOG.md updated for user-visible changes.
   - [ ] README.md updated for new features/breaking changes (if applicable).
   - [ ] External docs PR created (if applicable).
   - [ ] product-contract.md updated for product-level changes (if applicable).
   - [ ] Breaking changes documented (if any).

4. **Labels and metadata** — tag appropriately.
   - Size labels if applicable (S/M/L/XL).
   - Area labels (state, installer, hooks, doctor, etc.).
   - Link to spec task if part of governed workflow.

5. **Review assignment** — identify reviewers.
   - Auto-assign if CODEOWNERS configured.
   - Tag relevant domain experts for complex changes.

6. **Issue linking** — when a linked work item exists:
   - GitHub: `Closes #N` injected into PR body by `build_pr_description()`.
   - Azure DevOps: `AB#NNN` keyword + explicit `az repos pr update --work-items`.

## Examples

### Example 1: Full governed PR flow

User says: "Run /pr for my current branch changes."
Actions:

1. Run conditional spec reset, stage changes, and execute format/lint/secret and pre-push gates.
2. Commit, push, create PR, and enable auto-complete squash merge with branch deletion.
   Result: A governed PR is opened with all required checks and merge automation configured.

## References

- `standards/framework/core.md` — non-negotiables and enforcement rules.
- `standards/framework/quality/core.md` — gate structure (pre-push + PR gates).
- `skills/commit/SKILL.md` — shared pre-commit steps.
- `skills/cleanup/SKILL.md` — repository hygiene workflow; spec reset moved from `/cleanup` to `/pr`.
- `skills/changelog/SKILL.md` — changelog entry formatting (used by documentation gate).
- `skills/docs/SKILL.md` — README and documentation update procedure for OSS GitHub users (used by documentation gate).
- `agents/release.md` — agent that validates PR workflow execution.
