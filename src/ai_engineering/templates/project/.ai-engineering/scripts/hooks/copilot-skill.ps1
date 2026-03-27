# Copilot userPromptSubmitted telemetry hook.
# PowerShell implementation for Windows compatibility.
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"

function Get-JsonValue {
    param(
        [object]$Payload,
        [string]$Property
    )

    if ($null -eq $Payload) {
        return ""
    }

    $prop = $Payload.PSObject.Properties[$Property]
    if ($null -eq $prop) {
        return ""
    }

    return [string]$prop.Value
}

try {
    $InputJson = [Console]::In.ReadToEnd()
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    $Prompt = ""

    if (-not [string]::IsNullOrWhiteSpace($InputJson)) {
        try {
            $Payload = $InputJson | ConvertFrom-Json -Depth 10
        } catch {
            $Payload = $null
        }
        $Prompt = Get-JsonValue $Payload "prompt"
    }

    if ([string]::IsNullOrWhiteSpace($Prompt)) {
        exit 0
    }

    $Match = [regex]::Match($Prompt, "^/ai-([a-zA-Z-]+)")
    if (-not $Match.Success) {
        exit 0
    }

    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        exit 0
    }

    $env:PROJECT_DIR = $ProjectDir
    $env:SKILL_NAME = "ai-$($Match.Groups[1].Value.ToLowerInvariant())"
    $PythonScript = @'
import os
from pathlib import Path

from ai_engineering.state.observability import (
    emit_declared_context_loads,
    emit_ide_hook_outcome,
    emit_skill_invoked,
)
from ai_engineering.state.instincts import extract_instincts, maybe_refresh_instinct_context

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
    correlation_id=entry.correlation_id,
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
    correlation_id=entry.correlation_id,
)
if os.environ["SKILL_NAME"] == "ai-onboard":
    extract_instincts(Path(os.environ["PROJECT_DIR"]))
    maybe_refresh_instinct_context(Path(os.environ["PROJECT_DIR"]))
'@
    $PythonScript | & python - 2>$null | Out-Null
    exit 0
} catch {
    exit 0
}
