$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

# 1. Check uv
if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Error "uv not found. Install: https://docs.astral.sh/uv/"
    exit 1
}

# 2. Editable install as global tool
Write-Host "Installing ai-eng globally (editable)..."
uv tool install --editable $RepoRoot --force

# 3. Verify
if (-not (Get-Command ai-eng -ErrorAction SilentlyContinue)) {
    Write-Warning "ai-eng not in PATH."
    Write-Host "Add to PATH: $env:USERPROFILE\.local\bin"
    exit 1
}

# 4. Done
Write-Host ""
$version = & ai-eng version 2>$null
Write-Host "ai-eng $version"
Write-Host ""
Write-Host "Usage from any directory:"
Write-Host "  ai-eng install .          # Initialize a project"
Write-Host "  ai-eng doctor             # Health check"
Write-Host "  ai-eng update --apply     # Update framework files"
Write-Host ""
Write-Host "Code changes in $RepoRoot\src\ are reflected immediately."
