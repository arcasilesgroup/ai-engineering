{
  "version": 1,
  "hooks": {
    "PreToolUse": [
      {
        "type": "command",
        "command": "command -v ai-eng >/dev/null 2>&1 && ai-eng chain PreToolUse --surface copilot || exit 0",
        "timeoutSec": 10
      }
    ],
    "PostToolUse": [
      {
        "type": "command",
        "command": "command -v ai-eng >/dev/null 2>&1 && ai-eng chain PostToolUse --surface copilot || exit 0",
        "timeoutSec": 10
      }
    ]
  }
}
