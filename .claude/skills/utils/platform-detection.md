# Platform Detection

Reusable instructions for detecting the git platform (GitHub vs Azure DevOps).

## Detection Process

### 1. Read Remote URL

```bash
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")
```

### 2. Determine Platform

```
if REMOTE_URL contains "github.com" → PLATFORM=github
if REMOTE_URL contains "dev.azure.com" or "visualstudio.com" → PLATFORM=azure
otherwise → PLATFORM=unknown
```

### 3. Verify CLI Availability

**GitHub:**
```bash
gh --version          # CLI installed?
gh auth status        # Authenticated?
```

**Azure DevOps:**
```bash
az --version          # CLI installed?
az account show       # Authenticated?
az devops configure --list  # DevOps extension configured?
```

### 4. Fallback

If platform cannot be detected:
- Ask the user: "Which platform does this project use? (github/azure)"
- If CLI is not installed, report what needs to be installed
- If not authenticated, report how to authenticate:
  - GitHub: `gh auth login`
  - Azure DevOps: `az login` then `az devops configure --defaults organization=https://dev.azure.com/org project=MyProject`

## Platform-Specific Commands

| Action | GitHub | Azure DevOps |
|--------|--------|--------------|
| Create PR | `gh pr create --title "..." --body "..." --base <branch>` | `az repos pr create --title "..." --description "..." --target-branch <branch>` |
| Link work item | `Closes #123` in body | `--work-items AB#123` |
| List PRs | `gh pr list` | `az repos pr list` |
| View PR | `gh pr view <id>` | `az repos pr show --id <id>` |
| Check CI status | `gh run list` | `az pipelines runs list` |
