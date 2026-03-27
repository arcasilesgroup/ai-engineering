# Copilot wrapper for instinct-observe.py.
# Usage: copilot-instinct-observe.ps1 pre|post
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"

function Convert-ToSnakeCase {
    param([string]$Value)

    if ([string]::IsNullOrWhiteSpace($Value)) {
        return $Value
    }

    $Step1 = [regex]::Replace($Value, "(.)([A-Z][a-z]+)", '$1_$2')
    return ([regex]::Replace($Step1, "([a-z0-9])([A-Z])", '$1_$2')).ToLowerInvariant()
}

function Convert-NormalizedValue {
    param([object]$Value)

    if ($null -eq $Value) {
        return $null
    }

    if ($Value -is [System.Management.Automation.PSCustomObject]) {
        $Normalized = [ordered]@{}
        foreach ($Property in $Value.PSObject.Properties) {
            $Name = $Property.Name
            switch ($Name) {
                "toolArgs" { $Name = "tool_input"; break }
                "toolName" { $Name = "tool_name"; break }
                default { $Name = Convert-ToSnakeCase $Name }
            }
            $Normalized[$Name] = Convert-NormalizedValue $Property.Value
        }
        return [pscustomobject]$Normalized
    }

    if ($Value -is [System.Collections.IDictionary]) {
        $Normalized = [ordered]@{}
        foreach ($Entry in $Value.GetEnumerator()) {
            $Name = [string]$Entry.Key
            switch ($Name) {
                "toolArgs" { $Name = "tool_input"; break }
                "toolName" { $Name = "tool_name"; break }
                default { $Name = Convert-ToSnakeCase $Name }
            }
            $Normalized[$Name] = Convert-NormalizedValue $Entry.Value
        }
        return [pscustomobject]$Normalized
    }

    if (($Value -is [System.Collections.IEnumerable]) -and -not ($Value -is [string])) {
        $Items = @()
        foreach ($Item in $Value) {
            $Items += ,(Convert-NormalizedValue $Item)
        }
        return $Items
    }

    return $Value
}

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    if ($args.Count -gt 0) {
        $Phase = $args[0]
    } else {
        $Phase = "post"
    }
    $InputJson = [Console]::In.ReadToEnd()
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        exit 0
    }

    if ([string]::IsNullOrWhiteSpace($InputJson)) {
        $CanonicalJson = "{}"
    } else {
        try {
            $Payload = $InputJson | ConvertFrom-Json
            $CanonicalJson = (Convert-NormalizedValue $Payload) | ConvertTo-Json -Compress -Depth 20
        } catch {
            $CanonicalJson = "{}"
        }
    }

    if ($Phase -eq "pre") {
        $env:CLAUDE_HOOK_EVENT_NAME = "PreToolUse"
    } else {
        $env:CLAUDE_HOOK_EVENT_NAME = "PostToolUse"
    }
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"
    $CanonicalJson | & python (Join-Path $ScriptDir "instinct-observe.py") | Out-Null
    exit 0
} catch {
    exit 0
}
