# Copilot wrapper for runtime-stop.py (sessionEnd).
# Writes durable checkpoint + Ralph Loop resume marker. Fail-open.

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
            $Translated[$Property.Name] = $Property.Value
        }
        $TranslatedJson = $Translated | ConvertTo-Json -Compress -Depth 20
    }

    $env:CLAUDE_HOOK_EVENT_NAME = "Stop"
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"

    $TranslatedJson | Invoke-CopilotFrameworkPythonScript `
        -ProjectRoot $ProjectDir `
        -ScriptPath (Join-Path $ScriptDir "runtime-stop.py") | Out-Null

    exit 0
} catch {
    exit 0
}
