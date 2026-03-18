# Telemetry hook: emit session lifecycle events.
# PowerShell stub for Windows compatibility.
# Fail-open: exit 0 always.

$ErrorActionPreference = "SilentlyContinue"

try {
    $mode = if ($args[0]) { $args[0] } else { "end" }

    $root = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }

    # Activate venv if present
    $venvActivate = Join-Path $root ".venv\Scripts\Activate.ps1"
    if (Test-Path $venvActivate) { & $venvActivate }

    if ($mode -eq "end") {
        & ai-eng signals emit session_end --actor=ai-session --detail='{"type":"session_end"}' 2>$null
    }
} catch {
    # Fail-open
}

exit 0
