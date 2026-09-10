{
  "description": "ai-eng governance. Codex merges hooks from every scope — hooks you wrote yourself keep running. Trust is per hook: open /hooks in Codex once, or run codex --dangerously-bypass-hook-trust for a single run. The answer arrives as JSON on stdout with exit 0.",
  "hooks": {
    "PreToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "ai-eng chain PreToolUse --surface codex",
            "timeout": 10,
            "statusMessage": "ai-eng guards"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "ai-eng chain PostToolUse --surface codex",
            "timeout": 10
          }
        ]
      }
    ]
  }
}
