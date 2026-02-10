# Git Helpers Utility

## Purpose

Provide compact, safe git helper patterns used by governed command workflows.

## Protected Branch Check

```bash
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" = "main" ] || [ "$CURRENT_BRANCH" = "master" ]; then
  echo "protected branch"
fi
```

## Upstream Check

```bash
git rev-parse --abbrev-ref --symbolic-full-name @{u}
```

## Push Current Branch with Tracking

```bash
git push -u origin "$(git branch --show-current)"
```

## Default Branch Detection

```bash
git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'
```

Fallbacks:

- prefer `main`, then `master`.
- provider CLI lookup if symbolic ref is missing.

## Governance Notes

- Do not suggest `--no-verify`.
- Do not force push.
- Do not bypass mandatory checks.

## References

- `skills/workflows/commit.md` — primary consumer of git helper procedures.
- `skills/workflows/pr.md` — PR workflow using git operations.
- `standards/framework/core.md` — protected branch rules and enforcement.
