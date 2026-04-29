# Copilot errorOccurred telemetry hook.
# PowerShell implementation for Windows compatibility.
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    . (Join-Path $ScriptDir "_lib/copilot-common.ps1")
    . (Join-Path $ScriptDir "_lib/copilot-runtime.ps1")
    $script:CopilotComponent = "hook.copilot-error"

    Read-StdinPayload | Out-Null
    $ErrorName = Read-StdinPayload -Field "error.name"
    $ErrorMessage = Read-StdinPayload -Field "error.message"
    if ([string]::IsNullOrWhiteSpace($ErrorName)) { $ErrorName = "unknown" }
    if ([string]::IsNullOrWhiteSpace($ErrorMessage)) { $ErrorMessage = "unknown" }

    $env:PROJECT_DIR = $ProjectDir
    $env:ERROR_NAME = $ErrorName
    $env:ERROR_MESSAGE = $ErrorMessage
    $PythonScript = @'
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.observability import emit_framework_error, emit_ide_hook_outcome

PR = Path(os.environ["PROJECT_DIR"])
SID = os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID")
TID = os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID")
COMMON = dict(engine="github_copilot", component="hook.copilot-error", source="hook", session_id=SID, trace_id=TID)

emit_ide_hook_outcome(PR, hook_kind="error-occurred", outcome="failure", **COMMON)
emit_framework_error(PR, error_code=os.environ["ERROR_NAME"] or "hook_error", summary=os.environ["ERROR_MESSAGE"], **COMMON)
'@
    Invoke-CopilotFrameworkPythonInline -ProjectRoot $ProjectDir -ScriptText $PythonScript | Out-Null
    exit 0
} catch {
    exit 0
}
