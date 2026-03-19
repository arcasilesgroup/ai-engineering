# Telemetry hook: emit skill_invoked event on PostToolUse(Skill).
# PowerShell stub for Windows compatibility.
# Fail-open: exit 0 always.

$ErrorActionPreference = "SilentlyContinue"

try {
    $input_data = $input | Out-String
    $json = $input_data | ConvertFrom-Json
    $skill = $json.tool_input.skill

    if (-not $skill) { exit 0 }

    # Normalize: lowercase + ensure ai- prefix
    $CanonicalName = $skill.ToLower() -replace '^ai[-:]', ''
    $CanonicalName = "ai-$CanonicalName"

    $RootDir = if ($env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR } else { Split-Path -Parent (Split-Path -Parent $PSScriptRoot) }

    # Write directly to audit log — no CLI dependency
    $AuditLog = Join-Path $RootDir ".ai-engineering/state/audit-log.ndjson"
    $Timestamp = (Get-Date -AsUTC -Format "yyyy-MM-ddTHH:mm:ssZ")
    $Branch = git -C $RootDir rev-parse --abbrev-ref HEAD 2>$null
    $Commit = git -C $RootDir rev-parse --short HEAD 2>$null
    $Entry = @{actor="ai";branch=$Branch;commit_sha=$Commit;detail=@{skill=$CanonicalName};event="skill_invoked";source="hook";timestamp=$Timestamp} | ConvertTo-Json -Compress
    Add-Content -Path $AuditLog -Value $Entry -ErrorAction SilentlyContinue

    # Debug mode
    if ($env:AIENG_TELEMETRY_DEBUG -eq "1") {
        $DebugLog = Join-Path $RootDir ".ai-engineering/state/telemetry-debug.log"
        Add-Content -Path $DebugLog -Value "[$Timestamp] skill_invoked: $CanonicalName (raw: $skill)" -ErrorAction SilentlyContinue
    }
} catch {
    # Fail-open
}

exit 0
