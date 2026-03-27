# Copilot postToolUse telemetry hook.
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

    try {
        if ([string]::IsNullOrWhiteSpace($InputJson)) {
            $Payload = $null
        } else {
            $Payload = $InputJson | ConvertFrom-Json
        }
    } catch {
        $Payload = $null
    }

    $ToolName = Get-JsonValue $Payload "toolName"
    $ToolLower = $ToolName.ToLowerInvariant()
    $IsAgentDispatch = $false

    switch -Regex ($ToolLower) {
        "^(build|explorer|plan|review|verify|guard|guide|simplifier|task)$" {
            $IsAgentDispatch = $true
            break
        }
        "agent" {
            $IsAgentDispatch = $true
            break
        }
    }

    if (-not $IsAgentDispatch) {
        exit 0
    }

    $AgentType = ""
    $ToolArgs = $null
    if ($null -ne $Payload) {
        $toolArgsProp = $Payload.PSObject.Properties["toolArgs"]
        if ($null -ne $toolArgsProp) {
            $ToolArgs = $toolArgsProp.Value
        }
    }

    if ($ToolArgs -is [string]) {
        try {
            $ToolArgs = $ToolArgs | ConvertFrom-Json
        } catch {
            $ToolArgs = $null
        }
    }

    if ($null -ne $ToolArgs) {
        $agentTypeProp = $ToolArgs.PSObject.Properties["agent_type"]
        if ($null -ne $agentTypeProp) {
            $AgentType = [string]$agentTypeProp.Value
        }
    }

    if ([string]::IsNullOrWhiteSpace($AgentType)) {
        $AgentType = $ToolName
    }

    if ([string]::IsNullOrWhiteSpace($AgentType)) {
        exit 0
    }

    $AgentType = $AgentType.ToLowerInvariant()
    if ($AgentType.StartsWith("ai-")) {
        $AgentType = $AgentType.Substring(3)
    } elseif ($AgentType.StartsWith("ai:")) {
        $AgentType = $AgentType.Substring(3)
    }

    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        exit 0
    }

    $env:PROJECT_DIR = $ProjectDir
    $env:AGENT_TYPE = "ai-$AgentType"
    $PythonScript = @'
import os
from pathlib import Path

from ai_engineering.state.observability import emit_agent_dispatched, emit_ide_hook_outcome

emit_agent_dispatched(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    agent_name=os.environ["AGENT_TYPE"],
    component="hook.copilot-agent",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
)
emit_ide_hook_outcome(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    hook_kind="post-tool-use",
    component="hook.copilot-agent",
    outcome="success",
    source="hook",
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
    trace_id=os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID"),
)
'@
    $PythonScript | & python - 2>$null | Out-Null
    exit 0
} catch {
    exit 0
}
