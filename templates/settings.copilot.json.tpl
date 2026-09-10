{
  "version": 1,
  "hooks": {
    "PreToolUse": [
      {
        "type": "command",
        "command": "ai-eng chain PreToolUse --surface copilot",
        "timeoutSec": 10
      }
    ],
    "PostToolUse": [
      {
        "type": "command",
        "command": "ai-eng chain PostToolUse --surface copilot",
        "timeoutSec": 10
      }
    ]
  }
}
