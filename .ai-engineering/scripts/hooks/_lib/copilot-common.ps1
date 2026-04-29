# spec-114 D-114-01: shared PowerShell lib for Copilot hook adapters.
#
# Sealed contract: imports nothing beyond PowerShell builtins and
# Get-Content / ConvertFrom-Json / ConvertTo-Json. The .ps1 adapters
# dot-source this file via a one-line preamble and use the four functions
# below to remove the boilerplate that previously lived inline in every
# copilot-*.ps1.
#
# Functions (PowerShell verb-noun):
#   Read-StdinPayload [-Field <jq-like path>]
#   Emit-Event -Kind <s> -Component <s> -Outcome <s> [-Detail <hashtable>]
#   Should-FailOpen
#   Log-ToStderr -Level <s> -Message <s>
#
# Convention: callers set $script:CopilotComponent (e.g. "hook.copilot-skill")
# before invoking Emit-Event/Log-ToStderr so the component label is threaded
# through automatically.

# --- helpers ---------------------------------------------------------------

function Get-CopilotProjectRoot {
    param([string]$StartDir = $PSScriptRoot)
    if ([string]::IsNullOrWhiteSpace($StartDir)) {
        $StartDir = (Get-Location).Path
    }
    $current = $StartDir
    for ($i = 0; $i -lt 6; $i++) {
        if (Test-Path (Join-Path $current ".ai-engineering")) {
            return $current
        }
        $parent = Split-Path -Parent $current
        if ([string]::IsNullOrEmpty($parent) -or $parent -eq $current) { break }
        $current = $parent
    }
    return $StartDir
}

function Get-CopilotCorrelationId {
    if ($env:COPILOT_TRACE_ID) { return $env:COPILOT_TRACE_ID }
    if ($env:GITHUB_COPILOT_TRACE_ID) { return $env:GITHUB_COPILOT_TRACE_ID }
    return ([guid]::NewGuid().ToString("N"))
}

function Get-CopilotSessionId {
    if ($env:COPILOT_SESSION_ID) { return $env:COPILOT_SESSION_ID }
    if ($env:GITHUB_COPILOT_SESSION_ID) { return $env:GITHUB_COPILOT_SESSION_ID }
    return $null
}

function Get-CopilotPrevEventHash {
    param([string]$EventsPath)
    if (-not (Test-Path $EventsPath)) { return $null }
    try {
        $lines = Get-Content -Path $EventsPath -ErrorAction Stop
        if (-not $lines) { return $null }
        $last = $lines[-1]
        if ([string]::IsNullOrWhiteSpace($last)) { return $null }
        $obj = $last | ConvertFrom-Json -ErrorAction Stop
        if ($null -eq $obj) { return $null }
        $hash = [ordered]@{}
        foreach ($prop in $obj.PSObject.Properties) {
            if ($prop.Name -eq "prev_event_hash" -or $prop.Name -eq "prevEventHash") { continue }
            $hash[$prop.Name] = $prop.Value
        }
        $canonical = $hash | ConvertTo-Json -Compress -Depth 20
        $sha256 = [System.Security.Cryptography.SHA256]::Create()
        try {
            $bytes = [System.Text.Encoding]::UTF8.GetBytes($canonical)
            $digest = $sha256.ComputeHash($bytes)
            return ($digest | ForEach-Object { $_.ToString("x2") }) -join ""
        } finally {
            $sha256.Dispose()
        }
    } catch {
        return $null
    }
}

# --- 1. Read-StdinPayload --------------------------------------------------

# Reads JSON from stdin into $script:CopilotPayload. When -Field is provided
# the value at that property path (dot-separated) is returned as a string,
# or empty string when missing.
function Read-StdinPayload {
    param([string]$Field = "")
    if (-not $script:CopilotPayloadRead) {
        try {
            $raw = [Console]::In.ReadToEnd()
        } catch {
            $raw = ""
        }
        $script:CopilotPayloadRaw = $raw
        if ([string]::IsNullOrWhiteSpace($raw)) {
            $script:CopilotPayload = $null
        } else {
            try {
                $script:CopilotPayload = $raw | ConvertFrom-Json
            } catch {
                $script:CopilotPayload = $null
            }
        }
        $script:CopilotPayloadRead = $true
    }
    if ([string]::IsNullOrEmpty($Field)) { return }
    if ($null -eq $script:CopilotPayload) { return "" }
    $cursor = $script:CopilotPayload
    foreach ($segment in $Field.Split(".")) {
        if ($null -eq $cursor) { return "" }
        $prop = $cursor.PSObject.Properties[$segment]
        if ($null -eq $prop) { return "" }
        $cursor = $prop.Value
    }
    if ($null -eq $cursor) { return "" }
    return [string]$cursor
}

# --- 2. Emit-Event ---------------------------------------------------------

function Emit-Event {
    param(
        [Parameter(Mandatory = $true)][string]$Kind,
        [string]$Component = "",
        [string]$Outcome = "success",
        [hashtable]$Detail = @{}
    )
    if ([string]::IsNullOrEmpty($Component)) {
        if ($script:CopilotComponent) {
            $Component = $script:CopilotComponent
        } else {
            $Component = "hook.copilot-unknown"
        }
    }
    try {
        $projectRoot = Get-CopilotProjectRoot
        $eventsPath = Join-Path $projectRoot ".ai-engineering/state/framework-events.ndjson"
        $eventsDir = Split-Path -Parent $eventsPath
        if (-not (Test-Path $eventsDir)) {
            New-Item -ItemType Directory -Path $eventsDir -Force | Out-Null
        }
        $entry = [ordered]@{
            kind             = $Kind
            engine           = "github_copilot"
            timestamp        = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            component        = $Component
            outcome          = $Outcome
            correlationId    = (Get-CopilotCorrelationId)
            schemaVersion    = "1.0"
            project          = (Split-Path -Leaf $projectRoot)
            source           = "hook"
            detail           = $Detail
            prev_event_hash  = (Get-CopilotPrevEventHash -EventsPath $eventsPath)
        }
        $sessionId = Get-CopilotSessionId
        if ($sessionId) { $entry["sessionId"] = $sessionId }
        $line = $entry | ConvertTo-Json -Compress -Depth 20
        Add-Content -Path $eventsPath -Value $line -Encoding UTF8
    } catch {
        # Fail-open: hooks must never block the IDE flow.
        return
    }
}

# --- 3. Should-FailOpen ----------------------------------------------------

# Sets $ErrorActionPreference so the caller's `catch {}` blocks always
# resolve to exit 0; the actual `try/catch { exit 0 }` wrapper still lives
# in the caller (PowerShell scope rules prevent installing a trap at
# dot-source time that survives the caller's frame).
function Should-FailOpen {
    Set-Variable -Name ErrorActionPreference -Value "SilentlyContinue" -Scope 1
}

# --- 4. Log-ToStderr -------------------------------------------------------

function Log-ToStderr {
    param(
        [string]$Level = "info",
        [string]$Message = ""
    )
    $component = if ($script:CopilotComponent) { $script:CopilotComponent } else { "hook.copilot-unknown" }
    try {
        [Console]::Error.WriteLine("[$Level] ${component}: $Message")
    } catch {
        return
    }
}
