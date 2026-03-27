# Copilot wrapper for instinct-extract.py.
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"
try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = Resolve-Path (Join-Path $ScriptDir "../../..")
    $InputJson = [Console]::In.ReadToEnd()
    $Translated = $InputJson | & python (Join-Path $ScriptDir "copilot-adapter.py")
    $env:CLAUDE_HOOK_EVENT_NAME = "Stop"
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"
    $Translated | & python (Join-Path $ScriptDir "instinct-extract.py") | Out-Null
    exit 0
} catch {
    exit 0
}
