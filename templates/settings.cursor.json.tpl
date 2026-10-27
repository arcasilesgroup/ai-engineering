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
