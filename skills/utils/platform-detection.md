# Platform Detection — Shared Utility

Detect the git hosting platform and available CLI tools. Use this before running any platform-specific commands.

---

## Detection Logic

```bash
# Detect platform from remote URL
REMOTE_URL="$(git remote get-url origin 2>/dev/null || echo "")"

PLATFORM="unknown"
if echo "$REMOTE_URL" | grep -qE 'github\.com'; then
  PLATFORM="github"
elif echo "$REMOTE_URL" | grep -qE 'dev\.azure\.com|visualstudio\.com'; then
  PLATFORM="azdo"
elif echo "$REMOTE_URL" | grep -qE 'gitlab\.com'; then
  PLATFORM="gitlab"
elif echo "$REMOTE_URL" | grep -qE 'bitbucket\.org'; then
  PLATFORM="bitbucket"
fi
```

---

## CLI Availability

```bash
# Check CLI tools
HAS_GH=false
HAS_AZ=false

if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
  HAS_GH=true
fi

if command -v az &>/dev/null && az account show &>/dev/null 2>&1; then
  HAS_AZ=true
fi
```

---

## Platform Command Reference

| Operation            | GitHub (`gh`)                                                        | Azure DevOps (`az`)                                                                                |
| -------------------- | -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| Create PR            | `gh pr create --title "..." --body "..." --base <branch>`            | `az repos pr create --title "..." --description "..." --source-branch <src> --target-branch <tgt>` |
| List PRs             | `gh pr list --state open`                                            | `az repos pr list --status active`                                                                 |
| View PR              | `gh pr view <number>`                                                | `az repos pr show --id <id>`                                                                       |
| PR checks            | `gh pr checks <number>`                                              | `az repos pr show --id <id> --query 'status'`                                                      |
| Enable auto-merge    | `gh pr merge --auto --squash <number>`                               | `az repos pr update --id <id> --auto-complete true --merge-strategy squash`                        |
| Add reviewers        | `gh pr edit <number> --add-reviewer <users>`                         | `az repos pr update --id <id> --reviewers <users>`                                                 |
| Link work items      | `Closes #123` in PR body                                             | `--work-items <id>` flag on create                                                                 |
| View issue           | `gh issue view <number>`                                             | `az boards work-item show --id <id>`                                                               |
| Delete remote branch | `git push origin --delete <branch>`                                  | `git push origin --delete <branch>`                                                                |
| Default branch       | `gh repo view --json defaultBranchRef --jq '.defaultBranchRef.name'` | `az repos show --query 'defaultBranch' -o tsv \| sed 's@refs/heads/@@'`                            |

---

## Usage in Skills

When a skill needs platform-specific commands:

1. Detect the platform using the logic above.
2. Verify the required CLI is available and authenticated.
3. Use the corresponding command from the reference table.
4. If the CLI is not available, inform the user with installation instructions:
   - GitHub: `gh auth login` (install: https://cli.github.com)
   - Azure DevOps: `az login && az devops configure --defaults organization=<org> project=<project>` (install: https://aka.ms/azure-cli)
