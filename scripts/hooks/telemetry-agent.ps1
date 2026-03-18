# Telemetry hook: emit agent_dispatched event (Windows stub).
# Fail-open: exit 0 always.
try {
    $input_data = $input | ConvertFrom-Json -ErrorAction SilentlyContinue
    $agent_type = $input_data.tool_input.subagent_type
    if (-not $agent_type) { exit 0 }
    $desc = $input_data.tool_input.description
    $root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }
    & "$root\.venv\Scripts\Activate.ps1" 2>$null
    ai-eng signals emit agent_dispatched --actor=ai --source=hook --detail="{`"agent`":`"$agent_type`",`"description`":`"$desc`"}" 2>$null
} catch { }
exit 0
