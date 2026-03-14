---
name: pr
description: "Execute governed PR workflow: shared commit pipeline, pre-push gates, create pull request with auto-complete squash merge."
metadata:
  version: 3.0.0
  tags: [git, pull-request, ci, merge]
  ai-engineering:
    requires:
      bins: [gitleaks, ruff]
      anyBins: [gh, az]
    scope: read-write
    token_estimate: 1000
---

# PR Workflow

## Purpose

Execute the `/pr` governed workflow: run the shared commit pipeline (from `commit/SKILL.md`), add pre-push gates, create a pull request, and enable auto-complete with squash merge. The `--only` variant creates the PR without the commit pipeline.

## Trigger

- Command: `/pr` or `/pr --only`
- Context: user requests creating a pull request with governance enforcement.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"pr"}'` at skill start. Fail-open — skip if ai-eng unavailable.

## When NOT to Use

- **Commit-only without PR** — use `/commit --only` instead.
- **Quick push without PR** — use `/commit` instead.
- **Draft explorations** (not ready for review) — use `/commit` to push first, then `/pr` when ready.

## Preconditions (MUST verify before proceeding)

- **Required binaries**: `gitleaks`, `ruff` — must be available on PATH.
- **VCS CLI**: At least one of `gh` (GitHub) or `az` (Azure DevOps) — must be available and authenticated.
- Abort with remediation guidance if missing. Run `ai-eng doctor --fix-tools` to auto-install.

## Procedure

### `/pr` (default: commit pipeline + pre-push + create PR + auto-complete)

**Steps 0–6: Shared Commit Pipeline** — execute steps 0–6 from `commit/SKILL.md`:
- Auto-branch from protected, stage, format, lint, secret detection, documentation gate.

7. **Pre-push checks** — execute full pre-push gate:
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
      b. Append separator `\n\n---\n\n` + new section `## Additional Changes`.
      c. Update:
         - **GitHub**: `gh pr edit <number> --body "<extended_body>"`
         - **Azure DevOps**: `az repos pr update --id <id> --description "<extended_body>"`

15. **Enable auto-complete** — squash merge with branch deletion:
    - **GitHub**: `gh pr merge --auto --squash --delete-branch`
    - **Azure DevOps**: `az repos pr update --id <id> --auto-complete true --squash true --delete-source-branch true`

### `/pr --only` (create PR only)

1. **Check branch status** — verify current branch is pushed to remote.
   - If NOT pushed: emit warning and propose auto-push.
   - If user accepts: `git push origin <current-branch>`, then continue.
   - If user declines: continue with selected handling mode.
2. **Detect VCS provider** — same as step 12 above.
3. **Check for existing PR** — same as step 13 above.
4. **Create or update PR** — same as step 14 above.
5. **Enable auto-complete** — same as step 15 above.

## PR Structure

1. **Title** — `type(scope): description` or `spec-NNN: Task X.Y — description`. Max 72 chars.
2. **Description** — What (2-3 sentences), Why (link to spec/task), How (key decisions).
3. **Checklist** — code standards, tests, linting, secrets, CHANGELOG, README, breaking changes.
4. **Labels** — size (S/M/L/XL), area, spec link.
5. **Review assignment** — auto-assign if CODEOWNERS configured.
6. **Issue linking** — GitHub: `Closes #N`; Azure DevOps: `AB#NNN`.

## Output Contract

- Terminal output showing each step's result (pass/fail).
- On success: PR URL displayed with auto-complete status confirmed.
- On failure: specific check that failed with remediation guidance.

## Governance Notes

- Protected branch push is always blocked.
- All pre-push checks must pass before PR creation.
- Auto-complete with squash merge and branch deletion is mandatory.
- When updating an existing PR, body is ALWAYS extended, never replaced.
- Secret detection failure is a hard stop.
- Spec reset runs only in `/pr` default flow.

## Examples

### Example 1: Full governed PR flow

User says: "Run /pr for my current branch changes."
Actions:

1. Execute shared commit pipeline (auto-branch, stage, format, lint, secrets, doc gate).
2. Run pre-push gates, commit, push, create PR, enable auto-complete.
   Result: Governed PR opened with all checks and merge automation.

## References

- `skills/commit/SKILL.md` — shared commit pipeline (steps 0–6).
- `skills/changelog/SKILL.md` — changelog entry formatting.
- `skills/docs/SKILL.md` — README and documentation updates.
- `standards/framework/core.md` — non-negotiables and enforcement rules.
- `standards/framework/quality/core.md` — gate structure.
- `agents/release.md` — agent that validates PR workflow execution.
