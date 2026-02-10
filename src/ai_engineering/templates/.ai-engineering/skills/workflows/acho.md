# Acho Workflow

## Purpose

Execute the `/acho` governed workflow as a fast-path alias for `/commit`. The `/acho pr` variant combines commit + push with PR creation and auto-complete. Designed for speed while maintaining full governance enforcement.

## Trigger

- Command: `/acho` (alias for `/commit`) or `/acho pr` (alias for `/pr`)
- Context: user wants the fastest governed commit or PR path.

## Procedure

### `/acho` (stage + commit + push)

Identical to `/commit` default flow:

1. Stage changes — `git add -A`.
2. Run formatter — `ruff format .`.
3. Run linter — `ruff check . --fix`. Stop on unfixable issues.
4. Run secret detection — `gitleaks detect --staged --no-banner`. Stop on findings.
5. Commit — `git commit -m "<message>"`.
6. Push — `git push origin <current-branch>`. Block if `main`/`master`.

### `/acho pr` (stage + commit + push + create PR + auto-complete)

Identical to `/pr` default flow:

1. Stage, format, lint, secret detection (steps 1–4 above).
2. Run pre-push checks — `semgrep`, `pip-audit`, `pytest`, `ty check`. Stop on failures.
3. Commit with well-formed message.
4. Push to current branch. Block if protected.
5. Create PR — `gh pr create --fill`.
6. Enable auto-complete — `gh pr merge --auto --squash --delete-branch`.

## Output Contract

- Same output as `/commit` or `/pr` respectively.
- On success: commit hash (for `/acho`) or PR URL (for `/acho pr`).
- On failure: specific check that failed with remediation guidance.

## Governance Notes

- `/acho` is a strict alias — it provides identical governance to `/commit`. No shortcuts.
- `/acho pr` is a strict alias — it provides identical governance to `/pr`. No shortcuts.
- All non-negotiables from `standards/framework/core.md` apply without exception.
- Protected branch blocking, secret detection, and auto-complete rules are enforced identically.

## References

- `skills/workflows/commit.md` — full `/commit` procedure (aliases `/acho`).
- `skills/workflows/pr.md` — full `/pr` procedure (aliases `/acho pr`).
- `standards/framework/core.md` — non-negotiables.
