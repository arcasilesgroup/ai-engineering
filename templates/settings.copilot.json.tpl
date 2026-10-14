{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "command": "ai-eng chain PreToolUse --surface copilot-cli",
        "timeoutSec": 10
      },
      {
        "type": "command",
        "command": "[ -f \"$HOME/.ai-engineering/scripts/checkpoint-gate.py\" ] || exit 0; python3 \"$HOME/.ai-engineering/scripts/checkpoint-gate.py\" --surface copilot-cli",
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
