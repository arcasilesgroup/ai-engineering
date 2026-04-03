# Copilot errorOccurred telemetry hook.
# PowerShell implementation for Windows compatibility.
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"

try {
    $InputJson = [Console]::In.ReadToEnd()
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    . (Join-Path $ScriptDir "_lib/copilot-runtime.ps1")
    $ErrorName = "unknown"
    $ErrorMessage = "unknown"

    if (-not [string]::IsNullOrWhiteSpace($InputJson)) {
        try {
            $Payload = $InputJson | ConvertFrom-Json
        } catch {
            $Payload = $null
        }

        if ($null -ne $Payload) {
            $errorProp = $Payload.PSObject.Properties["error"]
            if ($null -ne $errorProp -and $null -ne $errorProp.Value) {
                $ErrorObject = $errorProp.Value
                $nameProp = $ErrorObject.PSObject.Properties["name"]
                $messageProp = $ErrorObject.PSObject.Properties["message"]
                if ($null -ne $nameProp -and -not [string]::IsNullOrWhiteSpace([string]$nameProp.Value)) {
                    $ErrorName = [string]$nameProp.Value
                }
                if ($null -ne $messageProp -and -not [string]::IsNullOrWhiteSpace([string]$messageProp.Value)) {
                    $ErrorMessage = [string]$messageProp.Value
                }
            }
        }
    }

    $env:PROJECT_DIR = $ProjectDir
    $env:ERROR_NAME = $ErrorName
    $env:ERROR_MESSAGE = $ErrorMessage
    $PythonScript = @'
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.observability import emit_framework_error, emit_ide_hook_outcome

project_root = Path(os.environ["PROJECT_DIR"])
emit_ide_hook_outcome(
    project_root,
    engine="github_copilot",
    hook_kind="error-occurred",
    component="hook.copilot-error",
    outcome="failure",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
)
emit_framework_error(
    project_root,
    engine="github_copilot",
    component="hook.copilot-error",
    error_code=os.environ["ERROR_NAME"] or "hook_error",
    summary=os.environ["ERROR_MESSAGE"],
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
)
'@
    Invoke-CopilotFrameworkPythonInline -ProjectRoot $ProjectDir -ScriptText $PythonScript | Out-Null
    exit 0
} catch {
    exit 0
}
