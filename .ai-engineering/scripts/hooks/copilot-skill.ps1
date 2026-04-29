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
from _lib.observability import (
    emit_declared_context_loads,
    emit_ide_hook_outcome,
    emit_skill_invoked,
)
from _lib.instincts import extract_instincts

entry = emit_skill_invoked(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    skill_name=os.environ["SKILL_NAME"],
    component="hook.copilot-skill",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
)
emit_declared_context_loads(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    initiator_kind="skill",
    initiator_name=os.environ["SKILL_NAME"],
    component="hook.copilot-skill",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
    correlation_id=entry["correlationId"],
)
emit_ide_hook_outcome(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    hook_kind="user-prompt-submit",
    component="hook.copilot-skill",
    outcome="success",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
    correlation_id=entry["correlationId"],
)
if os.environ["SKILL_NAME"] == "ai-start":
    extract_instincts(Path(os.environ["PROJECT_DIR"]))
'@
    Invoke-CopilotFrameworkPythonInline -ProjectRoot $ProjectDir -ScriptText $PythonScript | Out-Null
    exit 0
} catch {
    exit 0
}
