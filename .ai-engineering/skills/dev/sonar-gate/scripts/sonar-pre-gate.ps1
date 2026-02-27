# sonar-pre-gate.ps1 — Run SonarQube/SonarCloud analysis with quality gate wait.
#
# Usage:
#   .\sonar-pre-gate.ps1 [-SkipIfUnconfigured]
#
# Prerequisites:
#   - sonar-scanner on PATH
#   - SONAR_TOKEN environment variable or keyring entry
#   - sonar-project.properties in project root
#
# Exit codes:
#   0 — quality gate passed (or skipped when unconfigured)
#   1 — quality gate failed
#   2 — configuration error (missing scanner, missing properties)

[CmdletBinding()]
param(
    [switch]$SkipIfUnconfigured
)

$ErrorActionPreference = 'Stop'

# ---------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------

$ProjectRoot = if ($env:PROJECT_ROOT) { $env:PROJECT_ROOT } else { '.' }
$PropsFile = Join-Path $ProjectRoot 'sonar-project.properties'

# ---------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------

# Check sonar-scanner is available.
$scanner = Get-Command 'sonar-scanner' -ErrorAction SilentlyContinue
if (-not $scanner) {
    Write-Warning 'SKIP: sonar-scanner not found on PATH'
    if ($SkipIfUnconfigured) { exit 0 }
    exit 2
}

# Check sonar-project.properties exists.
if (-not (Test-Path $PropsFile)) {
    Write-Warning 'SKIP: sonar-project.properties not found'
    if ($SkipIfUnconfigured) { exit 0 }
    exit 2
}

# Check SONAR_TOKEN is set.
if (-not $env:SONAR_TOKEN) {
    Write-Warning 'SKIP: SONAR_TOKEN not set'
    if ($SkipIfUnconfigured) { exit 0 }
    exit 2
}

# ---------------------------------------------------------------
# Execute Sonar analysis
# ---------------------------------------------------------------

Write-Host 'Running Sonar analysis...'

& sonar-scanner `
    "-Dsonar.qualitygate.wait=true" `
    "-Dsonar.token=$env:SONAR_TOKEN" `
    "-Dproject.settings=$PropsFile"

$exitCode = $LASTEXITCODE

if ($exitCode -eq 0) {
    Write-Host 'PASS: Sonar quality gate passed'
} else {
    Write-Error "FAIL: Sonar quality gate failed (exit code: $exitCode)"
}

exit $exitCode
