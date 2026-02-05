# Hooks Overview

> Shell scripts that run automatically in response to events.

## What Are Hooks?

Hooks are shell scripts that execute automatically when certain events occur. The framework includes two types:

1. **Claude Code Hooks** — Run during Claude Code sessions
2. **Git Hooks** — Run during git operations

## Claude Code Hooks (5)

| Hook | Trigger | Purpose |
|------|---------|---------|
| `auto-format.sh` | After Edit/Write | Formats files after Claude edits them |
| `block-dangerous.sh` | Before Bash | Blocks force push, `rm -rf`, etc. |
| `block-env-edit.sh` | Before Edit/Write | Prevents editing `.env` files |
| `notify.sh` | Notification | Desktop alerts when Claude needs attention |
| `version-check.sh` | Session start | Checks for framework updates (24h cache) |

## Git Hooks (2)

| Hook | Trigger | Purpose |
|------|---------|---------|
| `pre-commit` | Before git commit | Scans staged files for secrets (gitleaks) |
| `pre-push` | Before git push | Blocks pushes with critical vulnerabilities |

## How Hooks Work

### Claude Code Hooks

1. **Event occurs** (e.g., Claude edits a file)
2. **Matcher checks** if hook applies (e.g., "Write|Edit")
3. **Hook script runs** with event data
4. **Exit code determines outcome:**
   - `0` = Success, continue
   - `2` = Block the action
   - Other = Warning, continue

### Git Hooks

1. **Git command runs** (e.g., `git push`)
2. **Hook script executes**
3. **Exit code determines outcome:**
   - `0` = Allow
   - Non-zero = Block

## Hook Location

```
.claude/
└── hooks/
    ├── auto-format.sh
    ├── block-dangerous.sh
    ├── block-env-edit.sh
    ├── notify.sh
    └── version-check.sh

.git/
└── hooks/
    ├── pre-commit
    └── pre-push
```

## Enabling Hooks

### Claude Code Hooks

Make scripts executable:

```bash
chmod +x .claude/hooks/*.sh
```

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

### Git Hooks

Install with `--install-tools` flag:

```bash
scripts/install.sh --name "MyProject" --stacks dotnet --install-tools
```

Or manually:

```bash
cp scripts/hooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

cp scripts/hooks/pre-push .git/hooks/pre-push
chmod +x .git/hooks/pre-push
```

## Hook Events

### PreToolUse

Runs **before** Claude executes a tool.

| Matcher | Tools Affected |
|---------|---------------|
| `Bash` | All bash commands |
| `Write` | File writes |
| `Edit` | File edits |
| `Write\|Edit` | Both writes and edits |

Use cases:
- Block dangerous commands
- Prevent editing sensitive files
- Add confirmation for risky operations

### PostToolUse

Runs **after** Claude executes a tool.

Use cases:
- Auto-format edited files
- Run linters
- Update documentation

### Notification

Runs when Claude sends a notification.

Use cases:
- Desktop alerts
- Slack notifications
- Sound alerts

## Bypassing Hooks

### Claude Code Hooks

Cannot be bypassed — they're part of the session configuration.

### Git Hooks

```bash
git commit --no-verify  # Skip pre-commit hook (not recommended)
git push --no-verify    # Skip pre-push hook (not recommended)
```

---
**See also:** [Claude Code Hooks](Hooks-Claude-Code-Hooks) | [Git Hooks](Hooks-Git-Hooks)
