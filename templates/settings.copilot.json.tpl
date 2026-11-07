{
  "version": 1,
  "hooks": {
    "preToolUse": [
      {
        "type": "command",
        "command": "command -v ai-eng >/dev/null 2>&1 || exit 0; ai-eng chain PreToolUse --surface copilot-cli",
        "powershell": "$c = Get-Command ai-eng -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1; if ($null -eq $c) { exit 0 }; & $c.Source chain PreToolUse --surface copilot-cli; if ($null -eq $LASTEXITCODE) { exit 1 }; exit $LASTEXITCODE",
        "timeoutSec": 10
      }
    ],
    "postToolUse": [
      {
        "type": "command",
        "command": "command -v ai-eng >/dev/null 2>&1 || exit 0; ai-eng chain PostToolUse --surface copilot-cli",
        "powershell": "$c = Get-Command ai-eng -CommandType Application -ErrorAction SilentlyContinue | Select-Object -First 1; if ($null -eq $c) { exit 0 }; & $c.Source chain PostToolUse --surface copilot-cli; if ($null -eq $LASTEXITCODE) { exit 1 }; exit $LASTEXITCODE",
        "timeoutSec": 10
      }
    ]
  }
}
