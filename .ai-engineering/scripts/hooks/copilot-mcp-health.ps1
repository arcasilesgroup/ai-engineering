# Copilot wrapper for mcp-health.py: MCP server health monitoring.
# Called by GitHub Copilot hooks (preToolCall and postToolCallFailure events).
# Translates Copilot JSON field names to Claude Code convention, then delegates.
# MUST preserve exit code 2 for blocking — non-fail-open.

$ErrorActionPreference = "Stop"

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    . (Join-Path $ScriptDir "_lib/copilot-common.ps1")
    . (Join-Path $ScriptDir "_lib/copilot-runtime.ps1")

    Read-StdinPayload | Out-Null
    $TranslatedJson = "{}"
    $CopilotEvent = "PreToolUse"

    if ($null -ne $script:CopilotPayload) {
        $payload = $script:CopilotPayload
        if (
            $null -ne $payload.PSObject.Properties["error"] -or
            $null -ne $payload.PSObject.Properties["failure"] -or
            $null -ne $payload.PSObject.Properties["errorMessage"]
        ) {
            $CopilotEvent = "PostToolUseFailure"
        }

        $Translated = [ordered]@{}
        foreach ($Property in $payload.PSObject.Properties) {
            $Name = $Property.Name
            $Value = $Property.Value
            if ($Name -eq "toolName") {
                $Translated["tool_name"] = $Value
            } elseif ($Name -eq "toolArgs") {
                if ($Value -is [string]) {
                    try { $Value = $Value | ConvertFrom-Json } catch { }
                }
                $Translated["tool_input"] = $Value
            } elseif ($Name -eq "toolResult") {
                $Translated["tool_output"] = $Value
            } else {
                $Translated[$Name] = $Value
            }
        }
        $TranslatedJson = $Translated | ConvertTo-Json -Compress -Depth 20
    }

    $env:CLAUDE_HOOK_EVENT_NAME = $CopilotEvent
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"

    $TranslatedJson | Invoke-CopilotFrameworkPythonScript `
        -ProjectRoot $ProjectDir `
        -ScriptPath (Join-Path $ScriptDir "mcp-health.py") | Out-Null

    if ($null -ne $LASTEXITCODE) { exit $LASTEXITCODE }
    exit 0
} catch {
    exit 0
}
