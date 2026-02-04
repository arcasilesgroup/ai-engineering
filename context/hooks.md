# Hooks System

## Overview

Hooks are shell scripts that run automatically before or after Claude Code tool invocations. They enforce safety rules, automate formatting, and integrate with the developer's environment without manual intervention.

Hooks live in `.claude/hooks/` and are registered in `.claude/settings.json` (shared) or `.claude/settings.local.json` (personal).

## Hook Lifecycle

There are two hook execution points:

| Phase | When It Runs | Use Case |
|-------|-------------|----------|
| **PreToolUse** | Before a tool executes | Block dangerous commands, prevent editing secrets |
| **PostToolUse** | After a tool completes | Auto-format files, send notifications |

### Execution Flow

```
User request
  -> Claude selects tool
    -> PreToolUse hooks run (can block)
      -> Tool executes
        -> PostToolUse hooks run (informational)
          -> Result returned
```

If any PreToolUse hook exits with code 2, the tool invocation is blocked and the reason (from stderr) is shown to the user.

## Stdin JSON Format

Every hook receives a JSON object on stdin describing the tool invocation. The exact fields depend on the tool, but common fields include:

```json
{
  "tool_name": "Edit",
  "file_path": "/path/to/file.cs",
  "command": "git push --force origin main"
}
```

| Field | Present For | Description |
|-------|------------|-------------|
| `tool_name` | All hooks | The tool being invoked (Edit, Write, Bash, etc.) |
| `file_path` | Edit, Write | Absolute path to the file being modified |
| `command` | Bash | The shell command being executed |

## Exit Codes

| Code | Meaning | Effect |
|------|---------|--------|
| **0** | Allow / Success | Tool proceeds normally |
| **2** | Block | Tool invocation is rejected; stderr message shown to user |

Any other exit code is treated as an error but does not block execution.

## Included Hooks

### 1. auto-format.sh (PostToolUse)

Automatically formats files after Edit or Write operations based on file extension.

| Extension | Formatter |
|-----------|-----------|
| `.cs` | `dotnet format` (finds nearest .csproj/.sln) |
| `.ts`, `.tsx`, `.js`, `.jsx` | `npx prettier --write` |
| `.py` | `ruff format` |
| `.tf` | `terraform fmt` |

Formatting failures are silently ignored and never block the workflow.

### 2. block-dangerous.sh (PreToolUse)

Blocks destructive Bash commands before they execute.

| Pattern | Reason |
|---------|--------|
| `git push --force` to main/master | Prevents rewriting shared history |
| `rm -rf /` or `rm -rf /*` | Prevents catastrophic file deletion |
| `git reset --hard` on main/master | Prevents discarding shared commits |
| `git clean -fd` on main/master | Prevents deleting untracked files on shared branch |
| `DROP DATABASE` / `DROP TABLE` | Prevents accidental data destruction |

### 3. block-env-edit.sh (PreToolUse)

Prevents Claude Code from editing files that typically contain secrets.

| Pattern | Examples |
|---------|----------|
| `.env` | `.env` |
| `.env.*` | `.env.local`, `.env.production` |
| `*.env` | `production.env` |
| `credentials.*` | `credentials.json`, `credentials.yaml` |
| `*.pem` | `server.pem`, `ca-bundle.pem` |
| `*.key` | `private.key`, `server.key` |
| `*secret*` | `secrets.yaml`, `client_secret.json` |

### 4. notify.sh (PostToolUse)

Sends a desktop notification when a tool invocation completes.

- **macOS:** Uses `osascript` to display a native notification.
- **Linux:** Uses `notify-send` if available.

Notification failures are silently ignored.

## Configuration

### Shared hooks (`.claude/settings.json`)

Register hooks in the project settings so the entire team benefits:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "command": ".claude/hooks/block-dangerous.sh"
      },
      {
        "matcher": "Edit|Write",
        "command": ".claude/hooks/block-env-edit.sh"
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "command": ".claude/hooks/auto-format.sh"
      }
    ]
  }
}
```

### Personal hooks (`.claude/settings.local.json`)

Hooks that are personal preference (like notifications) go in the local settings file, which is gitignored:

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "*",
        "command": ".claude/hooks/notify.sh"
      }
    ]
  }
}
```

You can also reference hooks from `CLAUDE.local.md` for documentation purposes.

## Adding Custom Hooks

### Step 1: Create the script

```bash
#!/usr/bin/env bash
set -euo pipefail

# Read stdin JSON
INPUT="$(cat)"

# Extract fields (no jq dependency)
TOOL_NAME="$(echo "$INPUT" | grep -o '"tool_name"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"
FILE_PATH="$(echo "$INPUT" | grep -o '"file_path"\s*:\s*"[^"]*"' | head -1 | sed 's/.*:.*"\(.*\)"/\1/' || true)"

# Your logic here

exit 0  # or exit 2 to block (with reason on stderr)
```

### Step 2: Make it executable

```bash
chmod +x .claude/hooks/my-hook.sh
```

### Step 3: Register in settings

Add the hook to `.claude/settings.json` (shared) or `.claude/settings.local.json` (personal).

### Best Practices

- Always use `set -euo pipefail` for safety.
- Redirect stderr to `/dev/null` for non-critical operations (formatting, notifications).
- Never depend on `jq`; parse JSON with `grep`/`sed` for portability.
- PostToolUse hooks should always exit 0 (never block after the fact).
- PreToolUse hooks should exit 2 with a clear reason on stderr when blocking.
- Keep hooks fast; they run on every matching tool invocation.
- Test hooks locally before committing to the shared settings.
