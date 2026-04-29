# Copilot wrapper for prompt-injection-guard.py: scan tool inputs for injection.
# Called by GitHub Copilot hooks (preToolCall event).
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
    if ($null -ne $script:CopilotPayload) {
        $Translated = [ordered]@{}
        foreach ($Property in $script:CopilotPayload.PSObject.Properties) {
            $Name = $Property.Name
            $Value = $Property.Value
            if ($Name -eq "toolName") {
                $Translated["tool_name"] = $Value
            } elseif ($Name -eq "toolArgs") {
                if ($Value -is [string]) {
                    try { $Value = $Value | ConvertFrom-Json } catch { }
                }
                $Translated["tool_input"] = $Value
            } else {
                $Translated[$Name] = $Value
            }
        }
        $TranslatedJson = $Translated | ConvertTo-Json -Compress -Depth 20
    }

    $env:CLAUDE_HOOK_EVENT_NAME = "PreToolUse"
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"

    $TranslatedJson | Invoke-CopilotFrameworkPythonScript `
        -ProjectRoot $ProjectDir `
        -ScriptPath (Join-Path $ScriptDir "prompt-injection-guard.py") | Out-Null

    if ($null -ne $LASTEXITCODE) { exit $LASTEXITCODE }
    exit 0
} catch {
    exit 0
}
