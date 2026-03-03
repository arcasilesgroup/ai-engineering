# VCS Commands Reference

Single-source command mapping for all VCS CLI operations used across skills. Supports GitHub (`gh`) and Azure DevOps (`az repos`).

## Provider Detection

1. Check `manifest.yml` → `providers.vcs.primary`.
2. Fallback: `git remote get-url origin`
   - Contains `github.com` → GitHub
   - Contains `dev.azure.com` or `visualstudio.com` → Azure DevOps
3. CLI availability: `command -v gh` / `command -v az`
4. Auth verification: `gh auth status` / `az account show`

## Command Mapping

| Operation | GitHub (`gh`) | Azure DevOps (`az repos`) |
|-----------|--------------|--------------------------|
| List open PRs for branch | `gh pr list --head <branch> --json number,title,body --state open` | `az repos pr list --source-branch <branch> --status active -o json` |
| Create PR | `gh pr create --title "..." --body "..."` | `az repos pr create --source-branch <branch> --target-branch <target> --title "..." --description "..."` |
| Update PR body | `gh pr edit <number> --body "..."` | `az repos pr update --id <id> --description "..."` |
| Update PR title | `gh pr edit <number> --title "..."` | `az repos pr update --id <id> --title "..."` |
| Auto-complete (squash) | `gh pr merge --auto --squash --delete-branch` | `az repos pr update --id <id> --auto-complete true --squash true --delete-source-branch true` |
| View PR | `gh pr view <number>` | `az repos pr show --id <id>` |
| List PRs | `gh pr list` | `az repos pr list -o json` |
| Auth check | `gh auth status` | `az account show` |
| Auth login | `gh auth login` | `az login` |
