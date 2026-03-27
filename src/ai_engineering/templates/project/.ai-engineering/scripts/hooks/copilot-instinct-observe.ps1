# Copilot wrapper for instinct-observe.py.
# Usage: copilot-instinct-observe.ps1 pre|post
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"
try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = Resolve-Path (Join-Path $ScriptDir "../../..")
    $Phase = if ($args.Count -gt 0) { $args[0] } else { "post" }
    $InputJson = [Console]::In.ReadToEnd()
    $Translated = $InputJson | & python (Join-Path $ScriptDir "copilot-adapter.py")
    $env:CLAUDE_HOOK_EVENT_NAME = if ($Phase -eq "pre") { "PreToolUse" } else { "PostToolUse" }
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"
    $Translated | & python (Join-Path $ScriptDir "instinct-observe.py") | Out-Null
    exit 0
} catch {
    exit 0
}
