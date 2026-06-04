#!/usr/bin/env pwsh
# Scheduled wrapper for /ai-session-watch-sweep (spec-165).
#
# Cadence: weekly. Recommended cron: `0 4 * * 2` (Tuesday 04:00 UTC).
# Hard rules (inherited from the skill): NEVER auto-merge, NEVER auto-file
# work items. The consolidation always opens a draft PR for human review.
#
# Parity port of session-watch-sweep.sh. The session-watch --review
# consolidation is LLM-driven (no deterministic `ai-eng` subcommand), so
# this wrapper only records the scheduled cycle (observability) — the
# actual review runs via the agent path (`/schedule weekly
# /ai-session-watch-sweep`). Never raises, never blocks the schedule.

$ErrorActionPreference = 'Stop'

$ProjectRoot = $env:AIENG_PROJECT_ROOT
if ([string]::IsNullOrEmpty($ProjectRoot)) {
    try {
        $gitRoot = (& git rev-parse --show-toplevel 2>$null)
        if ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrEmpty($gitRoot)) {
            $ProjectRoot = $gitRoot.Trim()
        } else {
            $ProjectRoot = (Get-Location).Path
        }
    } catch {
        $ProjectRoot = (Get-Location).Path
    }
}
Set-Location $ProjectRoot

$EventsFile = Join-Path $ProjectRoot ".ai-engineering/state/framework-events.ndjson"
$Ts = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

function Emit-Event {
    param(
        [string]$Outcome,
        [string]$Detail
    )
    # Best-effort NDJSON append. Schema parity is not enforced here —
    # the spec-120 SQLite indexer handles malformed lines defensively.
    $EventsDir = Split-Path $EventsFile -Parent
    if (-not (Test-Path $EventsDir)) {
        try {
            New-Item -ItemType Directory -Force -Path $EventsDir | Out-Null
        } catch {
            return
        }
    }
    $Line = '{"component":"scheduled.session-watch-sweep","kind":"framework_operation","operation":"session_watch_sweep_scheduled_run","outcome":"' +
        $Outcome + '","detail":' + $Detail +
        ',"timestamp":"' + $Ts + '","schemaVersion":"1.0","source":"scheduled","engine":"cron","project":"ai-engineering"}'
    try {
        Add-Content -Path $EventsFile -Value $Line -ErrorAction SilentlyContinue
    } catch {
        # silent: parity with sh `|| true` behaviour
    }
}

# The review is LLM-driven; the agent path (/schedule) performs it. This
# wrapper records the cycle so a missing agent run is observable.
Emit-Event "skipped" '{"reason":"requires_agent_review","via":"/schedule weekly /ai-session-watch-sweep"}'
exit 0
