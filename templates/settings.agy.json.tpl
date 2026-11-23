{
  "ai-eng-guard": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "command -v ai-eng >/dev/null 2>&1 || { echo ai-eng: not found in PATH, allowing this call >&2; exit 0; }; ai-eng chain PreToolUse --surface agy",
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
            "command": "command -v ai-eng >/dev/null 2>&1 || { echo ai-eng: not found in PATH, allowing this call >&2; exit 0; }; ai-eng chain PostToolUse --surface agy",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
