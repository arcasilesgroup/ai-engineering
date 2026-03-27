# Copilot wrapper for instinct-extract.py.
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"
try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        exit 0
    }
    $env:CLAUDE_HOOK_EVENT_NAME = "Stop"
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"
    "{}" | & python (Join-Path $ScriptDir "instinct-extract.py") | Out-Null
    exit 0
} catch {
    exit 0
}
