{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "command": "command -v ai-eng >/dev/null 2>&1 && ai-eng chain PreToolUse --surface copilot-cli || exit 0",
        "timeoutSec": 10
      }
    ],
    "postToolUse": [
      {
        "type": "command",
        "command": "command -v ai-eng >/dev/null 2>&1 && ai-eng chain PostToolUse --surface copilot-cli || exit 0",
        "timeoutSec": 10
      }
    ]
  }
}
