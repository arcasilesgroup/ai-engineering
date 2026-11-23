{
  "ai-eng-guard": {
    "PreToolUse": [
      {
        "matcher": "*",
        "hooks": [
          {
            "type": "command",
            "command": "command -v ai-eng >/dev/null 2>&1 || { echo \"ai-eng is not on PATH: this call was not judged and is allowed, because agy denies any non-zero exit. Install ai-eng, or remove the ai-eng-guard hook from hooks.json.\"; exit 0; }; ai-eng chain PreToolUse --surface agy",
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
            "command": "command -v ai-eng >/dev/null 2>&1 || { echo \"ai-eng is not on PATH: this call was not judged and is allowed, because agy denies any non-zero exit. Install ai-eng, or remove the ai-eng-guard hook from hooks.json.\"; exit 0; }; ai-eng chain PostToolUse --surface agy",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
