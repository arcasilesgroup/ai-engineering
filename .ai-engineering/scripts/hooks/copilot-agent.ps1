# Copilot postToolUse telemetry hook.
# PowerShell implementation for Windows compatibility.
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    . (Join-Path $ScriptDir "_lib/copilot-common.ps1")
    . (Join-Path $ScriptDir "_lib/copilot-runtime.ps1")
    $script:CopilotComponent = "hook.copilot-agent"

    Read-StdinPayload | Out-Null
    $ToolName = Read-StdinPayload -Field "toolName"
    $ToolLower = $ToolName.ToLowerInvariant()
    if ($ToolLower -notmatch "^(build|explorer|plan|review|verify|guard|guide|simplifier|task)$" -and $ToolLower -notmatch "agent") { exit 0 }

    $AgentType = ""
    if ($null -ne $script:CopilotPayload) {
        $ToolArgs = $script:CopilotPayload.toolArgs
        if ($ToolArgs -is [string]) { try { $ToolArgs = $ToolArgs | ConvertFrom-Json } catch { $ToolArgs = $null } }
        if ($null -ne $ToolArgs -and $null -ne $ToolArgs.agent_type) { $AgentType = [string]$ToolArgs.agent_type }
    }
    if ([string]::IsNullOrWhiteSpace($AgentType)) { $AgentType = $ToolName }
    if ([string]::IsNullOrWhiteSpace($AgentType)) { exit 0 }
    $AgentType = $AgentType.ToLowerInvariant() -replace "^(ai-|ai:)", ""

    $env:PROJECT_DIR = $ProjectDir
    $env:AGENT_TYPE = "ai-$AgentType"
    $PythonScript = @'
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.observability import emit_agent_dispatched, emit_ide_hook_outcome

PR = Path(os.environ["PROJECT_DIR"])
SID = os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID")
TID = os.environ.get("COPILOT_TRACE_ID") or os.environ.get("GITHUB_COPILOT_TRACE_ID")
COMMON = dict(engine="github_copilot", component="hook.copilot-agent", source="hook", session_id=SID, trace_id=TID)

emit_agent_dispatched(PR, agent_name=os.environ["AGENT_TYPE"], **COMMON)
emit_ide_hook_outcome(PR, hook_kind="post-tool-use", outcome="success", **COMMON)
'@
    Invoke-CopilotFrameworkPythonInline -ProjectRoot $ProjectDir -ScriptText $PythonScript | Out-Null
    exit 0
} catch {
    exit 0
}
