# PowerShell Standards

> Conventions for PowerShell scripts and modules.

---

## Script Structure

### Standard Header

```powershell
<#
.SYNOPSIS
    Brief description of the script.

.DESCRIPTION
    Detailed description of what the script does.

.PARAMETER Name
    Description of the Name parameter.

.PARAMETER Force
    Description of the Force switch.

.EXAMPLE
    .\script.ps1 -Name "example"
    Description of what this example does.

.NOTES
    Author: Team Name
    Version: 1.0.0
    Date: 2024-01-01
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$Name,

    [Parameter()]
    [switch]$Force
)

#Requires -Version 7.0
#Requires -Modules Az.Accounts

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# Script body here
```

---

## Naming Conventions

### Verb-Noun Pattern

```powershell
# ✅ Use approved verbs (Get-Verb for list)
Get-UserData
Set-Configuration
New-ResourceGroup
Remove-TempFiles
Test-Connection
Invoke-Deployment

# ❌ Avoid unapproved verbs
Create-User     # Use New-User
Delete-File     # Use Remove-File
Execute-Task    # Use Invoke-Task
```

### Naming Style

| Element | Convention | Example |
|---------|------------|---------|
| Functions | PascalCase | `Get-UserData` |
| Parameters | PascalCase | `-UserName`, `-Force` |
| Variables | PascalCase or camelCase | `$UserName`, `$configPath` |
| Private functions | Prefix with underscore | `_Get-InternalData` |

---

## Parameters

### Parameter Attributes

```powershell
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    # Required parameter
    [Parameter(Mandatory = $true, Position = 0)]
    [ValidateNotNullOrEmpty()]
    [string]$Name,

    # Validated parameter
    [Parameter()]
    [ValidateSet("Dev", "Staging", "Prod")]
    [string]$Environment = "Dev",

    # Path parameter with validation
    [Parameter()]
    [ValidateScript({ Test-Path $_ })]
    [string]$ConfigPath,

    # Array parameter
    [Parameter()]
    [string[]]$Tags,

    # Switch parameter
    [Parameter()]
    [switch]$Force,

    # Credential parameter
    [Parameter()]
    [PSCredential]$Credential
)
```

### Common Validation

```powershell
# Not null or empty
[ValidateNotNullOrEmpty()]

# Set of allowed values
[ValidateSet("Option1", "Option2", "Option3")]

# Range
[ValidateRange(1, 100)]

# Pattern (regex)
[ValidatePattern("^[a-z]{3}-[0-9]{4}$")]

# Custom script
[ValidateScript({ $_ -gt 0 })]

# Length
[ValidateLength(1, 50)]
```

---

## Error Handling

### Try/Catch Pattern

```powershell
try {
    # Code that might fail
    $result = Invoke-RestMethod -Uri $uri -ErrorAction Stop
}
catch [System.Net.WebException] {
    # Handle specific exception
    Write-Error "Network error: $($_.Exception.Message)"
    throw
}
catch {
    # Handle all other exceptions
    Write-Error "Unexpected error: $($_.Exception.Message)"
    throw
}
finally {
    # Cleanup code (always runs)
    if ($connection) {
        $connection.Dispose()
    }
}
```

### Error Action

```powershell
# Stop on error (recommended for scripts)
$ErrorActionPreference = "Stop"

# Per-command control
Get-Item "nonexistent" -ErrorAction SilentlyContinue
Invoke-WebRequest $url -ErrorAction Stop
```

---

## Output

### Write Methods

```powershell
# Information to pipeline (can be captured)
Write-Output "Processing complete"

# Verbose output (shown with -Verbose)
Write-Verbose "Starting processing of $ItemCount items"

# Debug output (shown with -Debug)
Write-Debug "Variable value: $($variable | ConvertTo-Json)"

# Warning output
Write-Warning "Configuration file not found, using defaults"

# Error output
Write-Error "Failed to connect to server"

# Host output (always shown, not capturable)
Write-Host "Interactive message" -ForegroundColor Green
```

### Progress

```powershell
for ($i = 0; $i -lt $total; $i++) {
    Write-Progress -Activity "Processing" -Status "Item $i of $total" `
        -PercentComplete (($i / $total) * 100)
    
    # Process item
}
Write-Progress -Activity "Processing" -Completed
```

---

## Best Practices

### Do

```powershell
# ✅ Use meaningful variable names
$resourceGroupName = "rg-myapp-prod"

# ✅ Use splatting for long commands
$params = @{
    ResourceGroupName = $resourceGroupName
    Location          = "westeurope"
    Name              = $appName
    Tags              = $tags
}
New-AzResourceGroup @params

# ✅ Use $PSScriptRoot for relative paths
$configPath = Join-Path $PSScriptRoot "config.json"

# ✅ Use ShouldProcess for destructive operations
if ($PSCmdlet.ShouldProcess($ResourceName, "Delete")) {
    Remove-AzResource -ResourceId $resourceId
}
```

### Don't

```powershell
# ❌ Use aliases in scripts (use in interactive only)
gci | % { $_.Name }    # BAD
Get-ChildItem | ForEach-Object { $_.Name }  # GOOD

# ❌ Use backticks for line continuation (except when necessary)
Get-Process `
    -Name "notepad" `
    -ComputerName "server"

# ✅ Use splatting instead
$params = @{
    Name = "notepad"
    ComputerName = "server"
}
Get-Process @params

# ❌ Hardcode paths
$config = "C:\Users\me\config.json"  # BAD

# ✅ Use environment variables or parameters
$config = $env:CONFIG_PATH  # GOOD
```

---

## Module Structure

```
MyModule/
├── MyModule.psd1           # Module manifest
├── MyModule.psm1           # Root module
├── Public/                 # Exported functions
│   ├── Get-Something.ps1
│   └── Set-Something.ps1
├── Private/                # Internal functions
│   └── _Helper.ps1
└── Tests/
    └── MyModule.Tests.ps1
```

---

## Testing (Pester)

```powershell
Describe "Get-UserData" {
    BeforeAll {
        . $PSScriptRoot\..\Public\Get-UserData.ps1
    }

    It "Returns user when exists" {
        $result = Get-UserData -UserId "123"
        $result | Should -Not -BeNullOrEmpty
        $result.Id | Should -Be "123"
    }

    It "Throws when user not found" {
        { Get-UserData -UserId "invalid" } | Should -Throw
    }
}
```

Run tests:
```powershell
Invoke-Pester -Path .\Tests -Output Detailed
```
