# Copilot wrapper for strategic-compact.py.
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"
try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = Resolve-Path (Join-Path $ScriptDir "../../..")
    . (Join-Path $ScriptDir "_lib/copilot-runtime.ps1")
    $InputJson = [Console]::In.ReadToEnd()
    $Translated = $InputJson | Invoke-CopilotFrameworkPythonScript -ProjectRoot $ProjectDir -ScriptPath (Join-Path $ScriptDir "copilot-adapter.py")
    $env:CLAUDE_HOOK_EVENT_NAME = "PreToolUse"
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"
    $Translated | Invoke-CopilotFrameworkPythonScript -ProjectRoot $ProjectDir -ScriptPath (Join-Path $ScriptDir "strategic-compact.py") | Out-Null
    exit 0
} catch {
    exit 0
}
