# PR Workflow

## Purpose

Execute the `/pr` governed workflow: stage, commit, push, create a pull request, and enable auto-complete with squash merge and branch deletion. The `--only` variant creates the PR without staging/committing/pushing first.

## Trigger

- Command: `/pr` or `/pr --only`
- Context: user requests creating a pull request with governance enforcement.

## Procedure

### `/pr` (default: stage + commit + push + create PR + auto-complete)

1. **Stage changes** — `git add -A` (or selective staging).
2. **Run formatter** — `ruff format .` to auto-fix formatting.
3. **Run linter** — `ruff check . --fix`. If unfixable issues remain, report and stop.
4. **Run secret detection** — `gitleaks detect --staged --no-banner`. If secrets found, report and stop.
5. **Run pre-push checks** — execute full pre-push gate:
   - `semgrep scan --config auto .`
   - `pip-audit`
   - `pytest tests/ -v`
   - `ty check src/`
   If any check fails, report and stop.
6. **Commit** — `git commit -m "<message>"` with well-formed message.
   - If active spec exists: `spec-NNN: Task X.Y — <description>`.
   - Otherwise: conventional commit format.
7. **Push** — `git push origin <current-branch>`.
   - If current branch is `main`/`master`, **block** and report protected branch violation.
8. **Create PR** — `gh pr create --fill` (or with explicit title/body if provided).
9. **Enable auto-complete** — `gh pr merge --auto --squash --delete-branch`.

### `/pr --only` (create PR only)

1. **Check branch status** — verify current branch is pushed to remote.
   - If NOT pushed: emit warning and propose auto-push.
   - If user accepts: `git push origin <current-branch>`, then continue.
   - If user declines: continue with selected PR handling mode (defer-pr, attempt-pr-anyway, export-pr-payload).
2. **Create PR** — `gh pr create --fill`.
3. **Enable auto-complete** — `gh pr merge --auto --squash --delete-branch`.

## Output Contract

- Terminal output showing each step's result (pass/fail).
- On success: PR URL displayed with auto-complete status confirmed.
- On failure: specific check that failed with remediation guidance.
- PR includes: title, description, breaking changes (if any), linked spec/task.

## Governance Notes

- Protected branch push is always blocked. No exceptions.
- All pre-push checks (semgrep, pip-audit, pytest, ty) must pass before PR creation.
- Auto-complete with squash merge and branch deletion is mandatory — never skip.
- `gh` CLI must be installed and authenticated. If not, attempt remediation: install `gh`, then `gh auth login`.
- Secret detection failure is a hard stop.
- `/pr --only` never hard-fails on unpushed branch — it warns and offers continuation modes.

## References

- `standards/framework/core.md` — non-negotiables and enforcement rules.
- `standards/framework/quality/core.md` — gate structure (pre-push + PR gates).
- `skills/workflows/commit.md` — shared pre-commit steps.
- `skills/workflows/acho.md` — alias workflow.
