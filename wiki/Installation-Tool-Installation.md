# Tool Installation

> Configure optional development tools that enhance the framework's capabilities.

## The --install-tools Flag

When you run the installer with `--install-tools`:

```bash
scripts/install.sh --name "MyProject" --stacks dotnet --cicd github --install-tools
```

It installs and configures:

1. **gitleaks** - Secret scanning
2. **gh CLI** - GitHub command line (for `/pr` skill)
3. **pre-push hook** - Vulnerability check before push

## What Gets Installed

### 1. Gitleaks (Secret Scanning)

[Gitleaks](https://github.com/gitleaks/gitleaks) scans your code for secrets before commits.

**Automatic install:**
- macOS: `brew install gitleaks`
- Linux: Downloads from GitHub releases

**Manual install:**
```bash
# macOS
brew install gitleaks

# Linux
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.1/gitleaks_8.18.1_linux_x64.tar.gz
tar -xzf gitleaks_8.18.1_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/
```

**Used by:**
- `/commit` skill (scans staged files before commit)
- `verify-app` agent (scans entire codebase)
- `/security-audit` skill

### 2. GitHub CLI (gh)

[GitHub CLI](https://cli.github.com/) enables the `/pr` skill to create pull requests.

**Automatic install:**
- macOS: `brew install gh`
- Linux: Via apt/dnf package managers

**Manual install:**
```bash
# macOS
brew install gh

# Linux (Debian/Ubuntu)
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

**Authenticate after install:**
```bash
gh auth login
```

**Used by:**
- `/pr` skill (creates GitHub PRs)
- `/commit-push-pr` skill (full commit-push-PR cycle)

### 3. Pre-Push Hook

A git hook that checks for vulnerabilities before push.

**What it does:**
- Runs on `git push`
- Checks npm (if package.json exists) for vulnerabilities
- Checks pip (if requirements.txt exists) for vulnerabilities
- **CRITICAL vulnerabilities** → Blocks push
- **HIGH vulnerabilities** → Warns but allows push

**Location:** `.git/hooks/pre-push`

**Bypass (not recommended):**
```bash
git push --no-verify
```

## Enabling Hooks

The framework includes 4 Claude Code hooks. Make them executable:

```bash
chmod +x .claude/hooks/*.sh
```

### Hook Scripts

| Script | Event | Purpose |
|--------|-------|---------|
| `auto-format.sh` | PostToolUse | Formats files after Claude edits them |
| `block-dangerous.sh` | PreToolUse | Blocks `rm -rf`, force push, etc. |
| `block-env-edit.sh` | PreToolUse | Prevents editing `.env` files |
| `notify.sh` | Notification | Desktop alerts when Claude needs attention |

### Hook Configuration

Hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": ".claude/hooks/block-dangerous.sh"
        }]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [{
          "type": "command",
          "command": ".claude/hooks/auto-format.sh"
        }]
      }
    ]
  }
}
```

## Installing Stack-Specific Tools

### .NET

```bash
# Install .NET format tool
dotnet tool install -g dotnet-format

# Verify
dotnet format --version
```

### TypeScript

```bash
# Install from tool-configs template
npm install --save-dev $(cat scripts/tool-configs/typescript.json | jq -r '.devDependencies | to_entries | map("\(.key)@\(.value)") | join(" ")')
```

Or manually:
```bash
npm install --save-dev eslint prettier typescript @typescript-eslint/parser @typescript-eslint/eslint-plugin
```

### Python

```bash
# Install from tool-configs template
pip install -r scripts/tool-configs/python.txt
```

Or manually:
```bash
pip install ruff black mypy pytest pytest-cov
```

### Terraform

```bash
# Install tflint
brew install tflint

# Use provided config
cp scripts/tool-configs/tflint.hcl ~/.tflint.hcl
```

## Verifying Tool Installation

```bash
# Check all tools
gitleaks version
gh --version
dotnet format --version
npx eslint --version
ruff --version
tflint --version
```

---
**See also:** [Quick Install](Installation-Quick-Install) | [Hooks Overview](Hooks-Overview)
