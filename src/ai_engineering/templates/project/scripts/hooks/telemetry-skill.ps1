# Telemetry hook: emit skill_invoked event on PostToolUse(Skill).
# PowerShell stub for Windows compatibility.
# Fail-open: exit 0 always.

$ErrorActionPreference = "SilentlyContinue"

try {
    $input_data = $input | Out-String
    $json = $input_data | ConvertFrom-Json
    $skill = $json.tool_input.skill

    if (-not $skill) { exit 0 }

    # Strip ai- prefix
    $canonical = $skill -replace '^ai[-:]', ''

    $root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }

    # Activate venv if present
    $venvActivate = Join-Path $root ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) { & $venvActivate }

    $detail = "{`"skill`":`"$canonical`"}"
    & ai-eng signals emit skill_invoked --actor=ai --detail=$detail 2>$null
} catch {
    # Fail-open
}

exit 0
