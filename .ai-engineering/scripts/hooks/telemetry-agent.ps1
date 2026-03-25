# Telemetry hook: emit agent_dispatched event (Windows stub).
# Fail-open: exit 0 always.

$ErrorActionPreference = "SilentlyContinue"

try {
    $input_data = $input | ConvertFrom-Json -ErrorAction SilentlyContinue
    $agent_type = $input_data.tool_input.subagent_type
    if (-not $agent_type) { exit 0 }
    $desc = $input_data.tool_input.description

    # Normalize: lowercase + ensure ai- prefix
    $AgentType = $agent_type.ToLower() -replace '^ai[-:]', ''
    $AgentType = "ai-$AgentType"

    $RootDir = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { (Get-Location).Path }

    # Escape description for JSON
    $SafeDesc = ($desc -replace '"', "'") -replace "`n", " "

    # Write directly to audit log — no CLI dependency
    $AuditLog = Join-Path $RootDir ".ai-engineering/state/audit-log.ndjson"
    $Timestamp = (Get-Date -AsUTC -Format "yyyy-MM-ddTHH:mm:ssZ")
    $Branch = git -C $RootDir rev-parse --abbrev-ref HEAD 2>$null
    $Commit = git -C $RootDir rev-parse --short HEAD 2>$null
    $Entry = @{actor="ai";agent=$AgentType;branch=$Branch;commit_sha=$Commit;detail=@{agent=$AgentType;description=$SafeDesc};event="agent_dispatched";source="hook";timestamp=$Timestamp} | ConvertTo-Json -Compress
    Add-Content -Path $AuditLog -Value $Entry -ErrorAction SilentlyContinue

    # Debug mode
    if ($env:AIENG_TELEMETRY_DEBUG -eq "1") {
        $DebugLog = Join-Path $RootDir ".ai-engineering/state/telemetry-debug.log"
        Add-Content -Path $DebugLog -Value "[$Timestamp] agent_dispatched: $AgentType (desc: $SafeDesc)" -ErrorAction SilentlyContinue
    }
} catch {
    # Fail-open
}

exit 0
