# Copilot wrapper for prompt-injection-guard.py: scan tool inputs for injection.
# Called by GitHub Copilot hooks (preToolCall event).
# Translates Copilot JSON field names to Claude Code convention, then delegates.
# MUST preserve exit code 2 for blocking — non-fail-open.

$ErrorActionPreference = "Stop"

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    . (Join-Path $ScriptDir "_lib/copilot-runtime.ps1")

    $InputJson = [Console]::In.ReadToEnd()
    $TranslatedJson = "{}"

    if (-not [string]::IsNullOrWhiteSpace($InputJson)) {
        try {
            $Payload = $InputJson | ConvertFrom-Json
            $Translated = [ordered]@{}

            foreach ($Property in $Payload.PSObject.Properties) {
                $Name = $Property.Name
                $Value = $Property.Value

                if ($Name -eq "toolName") {
                    $Translated["tool_name"] = $Value
                    continue
                }

                if ($Name -eq "toolArgs") {
                    if ($Value -is [string]) {
                        try {
                            $Value = $Value | ConvertFrom-Json
                        } catch {
                            # Preserve the original string if it is not valid JSON.
                        }
                    }
                    $Translated["tool_input"] = $Value
                    continue
                }

                $Translated[$Name] = $Value
            }

            $TranslatedJson = $Translated | ConvertTo-Json -Compress -Depth 20
        } catch {
            $TranslatedJson = "{}"
        }
    }

    $env:CLAUDE_HOOK_EVENT_NAME = "PreToolUse"
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"

    $TranslatedJson | Invoke-CopilotFrameworkPythonScript `
        -ProjectRoot $ProjectDir `
        -ScriptPath (Join-Path $ScriptDir "prompt-injection-guard.py") | Out-Null

    if ($null -ne $LASTEXITCODE) {
        exit $LASTEXITCODE
    }
    exit 0
} catch {
    exit 0
}
