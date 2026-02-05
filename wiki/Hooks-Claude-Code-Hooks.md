# Claude Code Hooks

> Detailed documentation for each Claude Code hook script.

## auto-format.sh

**Event:** PostToolUse (Write|Edit)
**Purpose:** Automatically format files after Claude edits them.

### How It Works

1. Detects file type from extension
2. Runs the appropriate formatter
3. Exits silently if formatter not installed

### Formatters by File Type

| Extension | Formatter | Command |
|-----------|-----------|---------|
| `.cs` | dotnet format | `dotnet format --include {file}` |
| `.ts`, `.tsx`, `.js`, `.jsx` | Prettier | `npx prettier --write {file}` |
| `.py` | Black/Ruff | `black {file}` or `ruff format {file}` |
| `.json` | Prettier | `npx prettier --write {file}` |
| `.yaml`, `.yml` | Prettier | `npx prettier --write {file}` |
| `.tf` | terraform fmt | `terraform fmt {file}` |

### Script Source

```bash
#!/usr/bin/env bash
# .claude/hooks/auto-format.sh

set -euo pipefail

FILE="$1"
EXT="${FILE##*.}"

case "$EXT" in
  cs)
    command -v dotnet >/dev/null && dotnet format --include "$FILE" 2>/dev/null
    ;;
  ts|tsx|js|jsx|json|yaml|yml)
    command -v npx >/dev/null && npx prettier --write "$FILE" 2>/dev/null
    ;;
  py)
    if command -v black >/dev/null; then
      black "$FILE" 2>/dev/null
    elif command -v ruff >/dev/null; then
      ruff format "$FILE" 2>/dev/null
    fi
    ;;
  tf)
    command -v terraform >/dev/null && terraform fmt "$FILE" 2>/dev/null
    ;;
esac

exit 0
```

---

## block-dangerous.sh

**Event:** PreToolUse (Bash)
**Purpose:** Block destructive commands before execution.

### Blocked Commands

| Pattern | Reason |
|---------|--------|
| `git push --force` | Can overwrite remote history |
| `git push -f` | Same as above |
| `git reset --hard` | Discards uncommitted changes |
| `rm -rf /` | Catastrophic deletion |
| `rm -rf ~` | Home directory deletion |
| `rm -rf .` | Current directory deletion |
| `:(){ :|:& };:` | Fork bomb |

### How It Works

1. Receives the command as input
2. Checks against blocked patterns
3. Returns exit code 2 to block, 0 to allow

### Script Source

```bash
#!/usr/bin/env bash
# .claude/hooks/block-dangerous.sh

COMMAND="$1"

# Dangerous patterns
DANGEROUS_PATTERNS=(
  "git push --force"
  "git push -f"
  "git reset --hard"
  "rm -rf /"
  "rm -rf ~"
  "rm -rf ."
  "rm -rf *"
  ":(){ :|:& };:"
)

for pattern in "${DANGEROUS_PATTERNS[@]}"; do
  if [[ "$COMMAND" == *"$pattern"* ]]; then
    echo "BLOCKED: Dangerous command detected: $pattern"
    exit 2  # Exit code 2 blocks the tool call
  fi
done

exit 0
```

### Bypassing

If you need to run a blocked command, do it manually in a separate terminal — not through Claude Code.

---

## block-env-edit.sh

**Event:** PreToolUse (Write|Edit)
**Purpose:** Prevent editing environment files with secrets.

### Blocked File Patterns

| Pattern | Example Files |
|---------|--------------|
| `.env` | `.env` |
| `.env.*` | `.env.local`, `.env.production` |
| `*.env` | `secrets.env` |
| `credentials.*` | `credentials.json`, `credentials.yaml` |
| `secrets.*` | `secrets.json`, `secrets.yaml` |

### Script Source

```bash
#!/usr/bin/env bash
# .claude/hooks/block-env-edit.sh

FILE="$1"
BASENAME=$(basename "$FILE")

# Patterns to block
if [[ "$BASENAME" == .env* ]] || \
   [[ "$BASENAME" == *.env ]] || \
   [[ "$BASENAME" == credentials.* ]] || \
   [[ "$BASENAME" == secrets.* ]]; then
  echo "BLOCKED: Cannot edit sensitive file: $BASENAME"
  echo "Edit this file manually if needed."
  exit 2
fi

exit 0
```

### Why This Matters

- Prevents accidental secret exposure in Claude conversation history
- Protects against committing secrets
- Forces manual review of credential changes

---

## notify.sh

**Event:** Notification
**Purpose:** Desktop notifications when Claude needs attention.

### Platform Support

| Platform | Method |
|----------|--------|
| macOS | `osascript` (native) |
| Linux | `notify-send` (requires libnotify) |
| Windows | Not supported |

### Script Source

```bash
#!/usr/bin/env bash
# .claude/hooks/notify.sh

TITLE="${1:-Claude Code}"
MESSAGE="${2:-Notification}"

if [[ "$OSTYPE" == "darwin"* ]]; then
  osascript -e "display notification \"$MESSAGE\" with title \"$TITLE\""
elif command -v notify-send >/dev/null; then
  notify-send "$TITLE" "$MESSAGE"
fi

exit 0
```

### Use Cases

- Long-running tasks complete
- Claude asks a question
- Error occurs that needs attention

---

## Configuration in settings.json

Full hooks configuration:

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
          }
        ]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-env-edit.sh"
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

---
**See also:** [Hooks Overview](Hooks-Overview) | [Git Hooks](Hooks-Git-Hooks) | [Custom Hooks](Customization-Custom-Hooks)
