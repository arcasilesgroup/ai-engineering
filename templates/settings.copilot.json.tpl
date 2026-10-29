{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "command": "ai-eng chain PreToolUse --surface copilot-cli",
        "timeoutSec": 10
      }
    ],
    "postToolUse": [
      {
        "type": "command",
        "command": "ai-eng chain PostToolUse --surface copilot-cli",
        "timeoutSec": 10
      }
    ]
  }
}
