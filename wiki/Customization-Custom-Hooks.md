# Custom Hooks

> Create team-specific automation hooks.

## Overview

Hooks are shell scripts that run automatically on events. Custom hooks let you add team-specific automation.

## Creating a Custom Hook

### 1. Create the Script

**File:** `.claude/hooks/my-hook.sh`

```bash
#!/usr/bin/env bash
set -euo pipefail

# Your hook logic here
# Exit 0 to allow, Exit 2 to block

exit 0
```

### 2. Make It Executable

```bash
chmod +x .claude/hooks/my-hook.sh
```

### 3. Register in settings.json

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [{
          "type": "command",
          "command": ".claude/hooks/my-hook.sh"
        }]
      }
    ]
  }
}
```

## Hook Types

### PreToolUse

Runs **before** a tool executes. Use for:
- Blocking dangerous operations
- Validating inputs
- Adding confirmations

**Exit codes:**
- `0` = Allow the tool to run
- `2` = Block the tool
- Other = Warning, continue

### PostToolUse

Runs **after** a tool executes. Use for:
- Formatting code
- Running linters
- Updating documentation

### Notification

Runs when Claude sends notifications. Use for:
- Desktop alerts
- Slack messages
- Sound alerts

## Example Custom Hooks

### Block Large File Writes

Prevent Claude from writing files larger than 1000 lines:

```bash
#!/usr/bin/env bash
# .claude/hooks/block-large-files.sh

FILE="$1"
CONTENT="$2"

LINE_COUNT=$(echo "$CONTENT" | wc -l)

if [[ $LINE_COUNT -gt 1000 ]]; then
  echo "BLOCKED: File too large ($LINE_COUNT lines). Maximum is 1000."
  echo "Consider splitting into multiple files."
  exit 2
fi

exit 0
```

**Register for Write tool:**
```json
{
  "matcher": "Write",
  "hooks": [{
    "type": "command",
    "command": ".claude/hooks/block-large-files.sh"
  }]
}
```

### Require Ticket Reference in Commits

```bash
#!/usr/bin/env bash
# .claude/hooks/require-ticket.sh

COMMAND="$1"

if [[ "$COMMAND" == *"git commit"* ]]; then
  # Check if commit message contains ticket reference
  if [[ "$COMMAND" != *"JIRA-"* ]] && [[ "$COMMAND" != *"#"* ]]; then
    echo "WARNING: Commit message should reference a ticket (JIRA-XXX or #XXX)"
  fi
fi

exit 0  # Warn but don't block
```

### Notify Slack on PR Creation

```bash
#!/usr/bin/env bash
# .claude/hooks/notify-slack.sh

MESSAGE="$1"

if [[ "$MESSAGE" == *"pull request"* ]]; then
  curl -X POST -H 'Content-type: application/json' \
    --data "{\"text\":\"New PR created: $MESSAGE\"}" \
    "$SLACK_WEBHOOK_URL" 2>/dev/null || true
fi

exit 0
```

### Auto-Add Copyright Headers

```bash
#!/usr/bin/env bash
# .claude/hooks/add-copyright.sh

FILE="$1"
EXT="${FILE##*.}"

COPYRIGHT="// Copyright $(date +%Y) MyCompany. All rights reserved."

case "$EXT" in
  cs|ts|js)
    # Check if file already has copyright
    if ! head -1 "$FILE" | grep -q "Copyright"; then
      # Add copyright to top
      CONTENT=$(cat "$FILE")
      echo -e "$COPYRIGHT\n\n$CONTENT" > "$FILE"
    fi
    ;;
esac

exit 0
```

### Log All Claude Actions

```bash
#!/usr/bin/env bash
# .claude/hooks/audit-log.sh

TOOL="$1"
ARGS="$2"

LOG_FILE="$HOME/.claude/audit.log"
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

echo "$TIMESTAMP | $TOOL | $ARGS" >> "$LOG_FILE"

exit 0
```

## Hook Input

Hooks receive data as command arguments:

| Event | Argument 1 | Argument 2 |
|-------|------------|------------|
| PreToolUse (Bash) | Command | - |
| PreToolUse (Write) | File path | Content |
| PreToolUse (Edit) | File path | Changes |
| PostToolUse | Tool name | Result |
| Notification | Title | Message |

## Matcher Patterns

Control which tools trigger hooks:

```json
{
  "matcher": "Bash",           // Only Bash
  "matcher": "Write",          // Only Write
  "matcher": "Write|Edit",     // Write OR Edit
  "matcher": "",               // All tools
}
```

## Full settings.json Example

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-dangerous.sh"
          },
          {
            "type": "command",
            "command": ".claude/hooks/require-ticket.sh"
          }
        ]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-env-edit.sh"
          },
          {
            "type": "command",
            "command": ".claude/hooks/block-large-files.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/auto-format.sh"
          },
          {
            "type": "command",
            "command": ".claude/hooks/add-copyright.sh"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/notify.sh"
          }
        ]
      }
    ]
  }
}
```

## Debugging Hooks

### Test Manually

```bash
# Test with sample input
echo "test input" | .claude/hooks/my-hook.sh
echo $?  # Check exit code
```

### Add Logging

```bash
#!/usr/bin/env bash
exec 2>> /tmp/hook-debug.log  # Redirect stderr to log
set -x  # Enable debug output
```

### Check Permissions

```bash
ls -la .claude/hooks/
# Should show executable permissions: -rwxr-xr-x
```

---
**See also:** [Hooks Overview](Hooks-Overview) | [Claude Code Hooks](Hooks-Claude-Code-Hooks)
