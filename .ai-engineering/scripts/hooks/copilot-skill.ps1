# Copilot userPromptSubmitted telemetry hook.
# PowerShell implementation for Windows compatibility.
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    . (Join-Path $ScriptDir "_lib/copilot-common.ps1")
    . (Join-Path $ScriptDir "_lib/copilot-runtime.ps1")
    $script:CopilotComponent = "hook.copilot-skill"

    $Prompt = Read-StdinPayload -Field "prompt"
    if ([string]::IsNullOrWhiteSpace($Prompt)) { exit 0 }
    $Match = [regex]::Match($Prompt, "^/ai-([a-zA-Z-]+)")
    if (-not $Match.Success) { exit 0 }

    $env:PROJECT_DIR = $ProjectDir
    $env:SKILL_NAME = "ai-$($Match.Groups[1].Value.ToLowerInvariant())"
    $PythonScript = @'
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.observability import emit_declared_context_loads, emit_ide_hook_outcome, emit_skill_invoked
from _lib.instincts import extract_instincts

PR = Path(os.environ["PROJECT_DIR"])
SK = os.environ["SKILL_NAME"]
SID = os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID")
TID = os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID")
COMMON = dict(engine="github_copilot", component="hook.copilot-skill", source="hook", session_id=SID, trace_id=TID)

entry = emit_skill_invoked(PR, skill_name=SK, **COMMON)
emit_declared_context_loads(PR, initiator_kind="skill", initiator_name=SK, correlation_id=entry["correlationId"], **COMMON)
emit_ide_hook_outcome(PR, hook_kind="user-prompt-submit", outcome="success", correlation_id=entry["correlationId"], **COMMON)
if SK == "ai-start":
    extract_instincts(PR)
'@
    Invoke-CopilotFrameworkPythonInline -ProjectRoot $ProjectDir -ScriptText $PythonScript | Out-Null
    exit 0
} catch {
    exit 0
}
