# Shared runtime launcher for Copilot hook helpers.
# Resolves an explicit project runtime instead of inheriting host python.

function Get-CopilotFrameworkPythonPath {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot
    )

    $VenvRoot = Join-Path $ProjectRoot ".venv"
    $Candidates = @(
        (Join-Path (Join-Path $VenvRoot "Scripts") "python.exe"),
        (Join-Path (Join-Path $VenvRoot "Scripts") "python"),
        (Join-Path (Join-Path $VenvRoot "bin") "python")
    )

    foreach ($Candidate in $Candidates) {
        if (Test-Path $Candidate) {
            return $Candidate
        }
    }

    return $null
}

function Invoke-CopilotFrameworkPythonScript {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$ScriptPath,
        [object[]]$Arguments = @()
    )

    $StdinContent = @($input)
    $PythonPath = Get-CopilotFrameworkPythonPath -ProjectRoot $ProjectRoot
    if ($null -ne $PythonPath) {
        if ($StdinContent.Count -gt 0) {
            ($StdinContent -join [Environment]::NewLine) | & $PythonPath $ScriptPath @Arguments
        } else {
            & $PythonPath $ScriptPath @Arguments
        }
        return
    }

    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Push-Location $ProjectRoot
        try {
            if ($StdinContent.Count -gt 0) {
                ($StdinContent -join [Environment]::NewLine) | & uv run python $ScriptPath @Arguments
            } else {
                & uv run python $ScriptPath @Arguments
            }
        } finally {
            Pop-Location
        }
        return
    }

    $global:LASTEXITCODE = 127
    return
}

function Invoke-CopilotFrameworkPythonInline {
    param(
        [Parameter(Mandatory = $true)][string]$ProjectRoot,
        [Parameter(Mandatory = $true)][string]$ScriptText,
        [object[]]$Arguments = @()
    )

    $StdinContent = @($input)
    $PythonPath = Get-CopilotFrameworkPythonPath -ProjectRoot $ProjectRoot
    if ($null -ne $PythonPath) {
        if ($StdinContent.Count -gt 0) {
            ($StdinContent -join [Environment]::NewLine) | & $PythonPath - @Arguments
        } else {
            $ScriptText | & $PythonPath - @Arguments
        }
        return
    }

    if (Get-Command uv -ErrorAction SilentlyContinue) {
        Push-Location $ProjectRoot
        try {
            if ($StdinContent.Count -gt 0) {
                ($StdinContent -join [Environment]::NewLine) | & uv run python - @Arguments
            } else {
                $ScriptText | & uv run python - @Arguments
            }
        } finally {
            Pop-Location
        }
        return
    }

    $global:LASTEXITCODE = 127
    return
}
