{
  "ai-eng-guard": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "ai-eng chain PreToolUse --surface agy",
            "timeout": 10
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "ai-eng chain PostToolUse --surface agy",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
