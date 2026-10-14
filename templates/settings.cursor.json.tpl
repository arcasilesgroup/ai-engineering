{
  "version": 1,
  "failClosed": true,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "command": "ai-eng chain PreToolUse --surface cursor",
        "timeout": 10,
        "failClosed": true,
        "comment": "ai-eng guards. The answer is JSON on stdout with exit 0: a non-zero exit is a hook ERROR to Cursor, not a denial."
      },
      {
        "type": "command",
        "command": "[ -f \"$HOME/.ai-engineering/scripts/checkpoint-gate.py\" ] || exit 0; python3 \"$HOME/.ai-engineering/scripts/checkpoint-gate.py\" --surface cursor",
        "timeout": 10,
        "failClosed": true,
        "comment": "checkpoint-gate beside chain for /ai-orchestrator."
      }
    ],
    "postToolUse": [
      {
        "type": "command",
        "command": "ai-eng chain PostToolUse --surface cursor",
        "timeout": 10
      }
    ]
  }
}
