# =============================================================================
# AI Engineering Framework (ai-engineering) Installer for Windows
# =============================================================================
# This script installs ai-engineering CLI tool on Windows.
#
# Usage (PowerShell):
#   iwr -useb https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/install.ps1 | iex
#
# Or with a specific version:
#   $env:AI_ENGINEERING_VERSION = "1.0.0"; iwr -useb https://raw.githubusercontent.com/arcasilesgroup/ai-engineering/main/install.ps1 | iex
#
# =============================================================================

#Requires -Version 5.1

param(
    [string]$Version = $env:AI_ENGINEERING_VERSION,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

# Configuration
$PackageName = "ai-engineering"
$MinPythonVersion = [version]"3.9"
$GitHubRepo = "arcasilesgroup/ai-engineering"

# Colors for output
function Write-ColorOutput {
    param(
        [string]$Message,
        [string]$Color = "White"
    )
    Write-Host $Message -ForegroundColor $Color
}

function Write-Success { Write-ColorOutput "✅ $args" "Green" }
function Write-Warning { Write-ColorOutput "⚠️  $args" "Yellow" }
function Write-Error { Write-ColorOutput "❌ $args" "Red" }
function Write-Info { Write-ColorOutput "ℹ️  $args" "Cyan" }
function Write-Step { Write-ColorOutput "→ $args" "Gray" }

# Show help
if ($Help) {
    Write-Host ""
    Write-Host "AI Engineering Framework Installer for Windows" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\install.ps1 [-Version <version>] [-Help]"
    Write-Host ""
    Write-Host "Parameters:"
    Write-Host "  -Version    Install a specific version (e.g., 1.0.0)"
    Write-Host "  -Help       Show this help message"
    Write-Host ""
    Write-Host "Examples:"
    Write-Host "  .\install.ps1                    # Install latest version"
    Write-Host "  .\install.ps1 -Version 1.0.0     # Install specific version"
    Write-Host ""
    Write-Host "One-liner installation:"
    Write-Host "  iwr -useb https://raw.githubusercontent.com/$GitHubRepo/main/install.ps1 | iex"
    Write-Host ""
    exit 0
}

# Check if command exists
function Test-CommandExists {
    param([string]$Command)
    $null -ne (Get-Command $Command -ErrorAction SilentlyContinue)
}

# Find Python installation
function Find-Python {
    $pythonCandidates = @(
        "python",
        "python3",
        "py -3"
    )

    foreach ($candidate in $pythonCandidates) {
        try {
            $versionOutput = & cmd /c "$candidate --version 2>&1"
            if ($versionOutput -match "Python (\d+)\.(\d+)\.(\d+)") {
                $foundVersion = [version]"$($Matches[1]).$($Matches[2]).$($Matches[3])"
                if ($foundVersion -ge $MinPythonVersion) {
                    return @{
                        Command = $candidate
                        Version = $foundVersion
                    }
                }
            }
        } catch {
            continue
        }
    }

    # Try py launcher specifically
    try {
        $pyVersion = & py -3 --version 2>&1
        if ($pyVersion -match "Python (\d+)\.(\d+)\.(\d+)") {
            $foundVersion = [version]"$($Matches[1]).$($Matches[2]).$($Matches[3])"
            if ($foundVersion -ge $MinPythonVersion) {
                return @{
                    Command = "py -3"
                    Version = $foundVersion
                }
            }
        }
    } catch {
        # py launcher not available
    }

    return $null
}

# Install Python using winget
function Install-PythonWinget {
    Write-Info "Installing Python via winget..."

    try {
        winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
        return $true
    } catch {
        Write-Warning "Failed to install via winget: $_"
        return $false
    }
}

# Install Python using Microsoft Store (fallback)
function Install-PythonManual {
    Write-Host ""
    Write-Warning "Automatic Python installation failed."
    Write-Host ""
    Write-Host "Please install Python manually:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  Option 1: Microsoft Store" -ForegroundColor Cyan
    Write-Host "    - Open Microsoft Store"
    Write-Host "    - Search for 'Python 3.11'"
    Write-Host "    - Click 'Get' to install"
    Write-Host ""
    Write-Host "  Option 2: Python.org" -ForegroundColor Cyan
    Write-Host "    - Visit https://www.python.org/downloads/windows/"
    Write-Host "    - Download Python 3.11+"
    Write-Host "    - Run installer (check 'Add Python to PATH')"
    Write-Host ""
    Write-Host "After installing Python, run this script again."
    Write-Host ""
}

# Ensure pip is available
function Ensure-Pip {
    param([string]$PythonCommand)

    Write-Step "Checking pip..."

    try {
        $pipCheck = if ($PythonCommand -eq "py -3") {
            & py -3 -m pip --version 2>&1
        } else {
            & cmd /c "$PythonCommand -m pip --version 2>&1"
        }

        if ($LASTEXITCODE -eq 0) {
            Write-Step "pip is available"
            return $true
        }
    } catch {
        # pip not found
    }

    Write-Step "Installing pip..."
    try {
        if ($PythonCommand -eq "py -3") {
            & py -3 -m ensurepip --upgrade
        } else {
            & cmd /c "$PythonCommand -m ensurepip --upgrade"
        }
        return $true
    } catch {
        Write-Warning "Could not install pip automatically"
        return $false
    }
}

# Install ai-engineering package
function Install-AiEngineering {
    param(
        [string]$PythonCommand,
        [string]$Version
    )

    Write-Info "Installing ai-engineering..."

    $packageSpec = if ($Version) {
        "$PackageName==$Version"
    } else {
        $PackageName
    }

    try {
        if ($PythonCommand -eq "py -3") {
            & py -3 -m pip install --upgrade $packageSpec
        } else {
            & cmd /c "$PythonCommand -m pip install --upgrade $packageSpec"
        }

        if ($LASTEXITCODE -eq 0) {
            return $true
        }
    } catch {
        Write-Error "Failed to install ai-engineering: $_"
    }

    return $false
}

# Verify installation
function Test-Installation {
    Write-Step "Verifying installation..."

    # Refresh PATH
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")

    try {
        $versionOutput = & ai-engineering --version 2>&1
        if ($versionOutput -match "(\d+\.\d+\.\d+)") {
            $installedVersion = $Matches[1]

            Write-Host ""
            Write-Success "ai-engineering installed successfully!"
            Write-Host "   Version: $installedVersion" -ForegroundColor Cyan
            Write-Host ""
            Write-Host "Quick Start:" -ForegroundColor Cyan
            Write-Host '   ai-engineering init --name "MyProject" --stack dotnet'
            Write-Host "   ai-engineering sync github"
            Write-Host "   ai-engineering validate"
            Write-Host ""
            Write-Host "For help:" -ForegroundColor Cyan
            Write-Host "   ai-engineering --help"
            Write-Host ""
            return $true
        }
    } catch {
        # ai-engineering not found in PATH
    }

    Write-Host ""
    Write-Warning "ai-engineering installed but not found in PATH."
    Write-Host ""
    Write-Host "You may need to:" -ForegroundColor Yellow
    Write-Host "  1. Restart your terminal/PowerShell"
    Write-Host "  2. Or add Python Scripts to PATH manually:"
    Write-Host ""

    # Find Python Scripts directory
    $pythonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python311\Scripts",
        "$env:LOCALAPPDATA\Programs\Python\Python310\Scripts",
        "$env:APPDATA\Python\Python311\Scripts",
        "$env:APPDATA\Python\Python310\Scripts"
    )

    foreach ($path in $pythonPaths) {
        if (Test-Path $path) {
            Write-Host "     Add to PATH: $path" -ForegroundColor Gray
            break
        }
    }

    Write-Host ""
    Write-Host "Then run: ai-engineering --help"
    Write-Host ""

    return $false
}

# Main installation flow
function Main {
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║        AI Engineering Framework (ai-engineering) Installer     ║" -ForegroundColor Cyan
    Write-Host "╚══════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""

    # Check for Python
    Write-Step "Looking for Python $MinPythonVersion+..."
    $python = Find-Python

    if ($null -eq $python) {
        Write-Warning "Python $MinPythonVersion or higher not found."
        Write-Host ""

        # Try to install via winget
        if (Test-CommandExists "winget") {
            $installed = Install-PythonWinget

            if ($installed) {
                # Refresh PATH and try again
                $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
                Start-Sleep -Seconds 2
                $python = Find-Python
            }
        }

        if ($null -eq $python) {
            Install-PythonManual
            exit 1
        }
    }

    Write-Host "Found Python: $($python.Command) ($($python.Version))" -ForegroundColor Cyan

    # Ensure pip
    if (-not (Ensure-Pip -PythonCommand $python.Command)) {
        Write-Error "Failed to ensure pip is available"
        exit 1
    }

    # Install ai-engineering
    if (-not (Install-AiEngineering -PythonCommand $python.Command -Version $Version)) {
        Write-Error "Failed to install ai-engineering"
        exit 1
    }

    # Verify
    Test-Installation
}

# Run main
Main
