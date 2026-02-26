# Framework Bash/PowerShell Stack Standards

## Update Metadata

- Rationale: establish shell scripting patterns for hooks, automation, and cross-OS scripts.
- Expected gain: consistent shell script quality, portability, and security across Bash and PowerShell.
- Potential impact: all hook scripts and automation follow enforceable patterns.

## Stack Scope

- Primary languages: Bash (Linux/macOS), PowerShell (Windows/cross-platform).
- Supporting formats: YAML, JSON, TOML.
- Toolchain baseline: `shellcheck`, `shfmt` (Bash); `PSScriptAnalyzer` (PowerShell).
- Distribution: scripts bundled with project or framework installation.

## Required Tooling

### Bash

- Lint: `shellcheck` (SC rules).
- Format: `shfmt` (Google style or project convention).
- Execution: Bash 4+ (or POSIX sh for maximum portability).

### PowerShell

- Lint: `PSScriptAnalyzer` (`Invoke-ScriptAnalyzer`).
- Format: `Invoke-Formatter` or editor-based formatting.
- Execution: PowerShell 7+ (cross-platform) or Windows PowerShell 5.1.

## Minimum Gate Set

### Bash

- Pre-commit: `shellcheck *.sh`, `shfmt -d *.sh`, `gitleaks`.
- Pre-push: full shellcheck with `--severity=warning`.

### PowerShell

- Pre-commit: `Invoke-ScriptAnalyzer -Path *.ps1 -Severity Warning`, `gitleaks`.
- Pre-push: full analysis with `-Severity Information`.

## Quality Baseline

- Bash: `set -euo pipefail` at script top. Quote all variable expansions.
- PowerShell: `Set-StrictMode -Version Latest`, `$ErrorActionPreference = 'Stop'`.
- All scripts must have usage comments or `--help` output.
- Exit codes: 0 for success, non-zero for failure with descriptive stderr messages.
- No hardcoded paths — use environment variables or relative paths from script location.

## Code Patterns

### Bash

- **Shebang**: `#!/usr/bin/env bash` (not `#!/bin/bash`).
- **Error handling**: `set -euo pipefail`. Trap ERR for cleanup: `trap 'cleanup' ERR EXIT`.
- **Variables**: `local` for function variables. UPPER_CASE for exported/environment variables.
- **Functions**: use `function_name() { }` syntax. Small, single-purpose.
- **Conditionals**: `[[ ]]` for tests (not `[ ]`). Use `&&`/`||` for simple conditionals.
- **Loops**: prefer `while read -r line` for line processing. Avoid parsing `ls` output.
- **Portability**: avoid bashisms when targeting POSIX sh. Use `command -v` instead of `which`.
- **Temporary files**: `mktemp` with cleanup in trap.

### PowerShell

- **Parameters**: use `[CmdletBinding()]` and `param()` block. Type all parameters.
- **Error handling**: `try/catch/finally`. Use `-ErrorAction Stop` on critical commands.
- **Pipeline**: leverage pipeline for data transformation. Avoid `ForEach-Object` when `Where-Object | Select-Object` suffices.
- **Modules**: organize reusable functions in `.psm1` modules.
- **Naming**: Verb-Noun convention (`Get-Config`, `Set-HookPermission`).
- **Output**: return objects, not strings. Use `Write-Verbose`, `Write-Warning`, `Write-Error` appropriately.

### Cross-OS Patterns

- **Dual scripts**: provide both `.sh` and `.ps1` for critical operations (hooks, install).
- **Path handling**: Bash uses `/`, PowerShell uses `Join-Path`. Never hardcode separators.
- **Line endings**: `.sh` files use LF. `.ps1` files use CRLF. Configure `.gitattributes` accordingly.
- **Exit codes**: consistent between Bash and PowerShell equivalents.

## Testing Patterns

- Bash: `bats` (Bash Automated Testing System) for unit tests.
- PowerShell: `Pester` for unit and integration tests.
- Both: verify exit codes, stdout/stderr output, and file system side effects.
- Cross-OS: CI matrix with Linux + Windows runners.

## Update Contract

This file is framework-managed and may be updated by framework releases.
