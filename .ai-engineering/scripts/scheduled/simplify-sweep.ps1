#!/usr/bin/env pwsh
# Scheduled wrapper for /ai-simplify-sweep (spec-121).
#
# Cadence: weekly. Recommended cron: `0 4 * * 1` (Monday 04:00 UTC).
# Hard rule (inherited from the skill): NEVER auto-merge. Always opens
# a draft PR for human review.
#
# This wrapper exists so the schedule layer (cron, /schedule skill,
# launchd, systemd timer, Windows Task Scheduler) has a single
# deterministic entrypoint instead of invoking a slash command directly.
#
# Parity port of simplify-sweep.sh — see that file for cadence + rules.
#
# Behaviour:
# - If `ai-eng` CLI is on PATH and supports `simplify --conservative`,
#   invoke it and capture exit code.
# - Else, log a `framework_operation` event with
#   `operation=simplify_sweep_scheduled_run`, `outcome=skipped` and exit 0.
# - Never raises, never blocks the schedule.

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
    $Line = '{"component":"scheduled.simplify-sweep","kind":"framework_operation","operation":"simplify_sweep_scheduled_run","outcome":"' +
        $Outcome + '","detail":' + $Detail +
        ',"timestamp":"' + $Ts + '","schemaVersion":"1.0","source":"scheduled","engine":"cron","project":"ai-engineering"}'
    try {
        Add-Content -Path $EventsFile -Value $Line -ErrorAction SilentlyContinue
    } catch {
        # silent: parity with sh `|| true` behaviour
    }
}

if (-not (Get-Command ai-eng -ErrorAction SilentlyContinue)) {
    Emit-Event "skipped" '{"reason":"ai-eng_not_on_path"}'
    exit 0
}

# Conservative simplify; rely on the skill's PR-opening logic.
try {
    & ai-eng simplify --conservative --no-pr 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Emit-Event "success" '{"mode":"conservative","pr":"deferred_to_skill"}'
    } else {
        Emit-Event "failure" '{"mode":"conservative"}'
    }
} catch {
    Emit-Event "failure" '{"mode":"conservative"}'
}

exit 0
