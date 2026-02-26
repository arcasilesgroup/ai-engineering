# Platform Detect

On-demand reference for host OS detection, provider detection, and tool availability.

## Host OS Detection

| Platform | Node.js | Python | Bash | PowerShell |
|----------|---------|--------|------|-----------|
| macOS | `process.platform === 'darwin'` | `sys.platform == 'darwin'` | `[[ "$(uname)" == "Darwin" ]]` | `$IsMacOS` |
| Linux | `process.platform === 'linux'` | `sys.platform == 'linux'` | `[[ "$(uname)" == "Linux" ]]` | `$IsLinux` |
| Windows | `process.platform === 'win32'` | `sys.platform == 'win32'` | N/A (use WSL or Git Bash) | `$IsWindows` |

## VCS Provider Detection

- **GitHub**: `GITHUB_ACTIONS` env var in CI, `.github/` directory, `gh` CLI available.
- **Azure DevOps**: `BUILD_REPOSITORY_PROVIDER` env var, `SYSTEM_TEAMFOUNDATIONCOLLECTIONURI` env var.
- **GitLab**: `GITLAB_CI` env var, `.gitlab-ci.yml` file.
- **Bitbucket**: `BITBUCKET_PIPELINE` env var.
- **Local**: no CI env vars, detect by remote URL (`git remote get-url origin`).

## Tool Availability Check

### Binary Existence

```bash
# Bash — check if binary exists
command -v <binary> &>/dev/null && echo "found" || echo "not found"

# PowerShell — check if binary exists
if (Get-Command <binary> -ErrorAction SilentlyContinue) { "found" } else { "not found" }
```

### Required Tools by Stack

| Stack | Required | Optional |
|-------|----------|----------|
| Python | `uv`, `ruff`, `gitleaks` | `ty`, `semgrep`, `pip-audit` |
| TypeScript | `node`, `npm`/`pnpm`/`bun`, `gitleaks` | `eslint`, `prettier`, `semgrep` |
| .NET | `dotnet`, `gitleaks` | `semgrep` |
| Rust | `rustup`, `cargo`, `gitleaks` | `cargo-audit`, `semgrep` |
| Bash | `shellcheck`, `gitleaks` | `shfmt` |
| PowerShell | `pwsh`, `gitleaks` | `PSScriptAnalyzer` |

### Auto-Remediation Order

When a required tool is missing:

1. **Detect** — check if the tool exists on PATH.
2. **Install** — use the stack-appropriate installer.
   - Python: `uv tool install <tool>` or `pip install <tool>`.
   - Node.js: `npm install -g <tool>` or `npx <tool>`.
   - Rust: `cargo install <tool>`.
   - System: `brew install <tool>` (macOS), `apt install <tool>` (Linux), `winget install <tool>` (Windows).
3. **Configure** — set up config files if needed.
4. **Authenticate** — for tools requiring auth (e.g., `gh auth login`, `az login`).
5. **Re-run** — execute the failing check again.

## Package Manager Detection

| File | Package Manager | Stack |
|------|----------------|-------|
| `pyproject.toml` | uv / pip | Python |
| `package.json` + `package-lock.json` | npm | Node.js |
| `package.json` + `pnpm-lock.yaml` | pnpm | Node.js |
| `package.json` + `bun.lockb` | bun | Node.js |
| `*.csproj` / `*.sln` | dotnet / NuGet | .NET |
| `Cargo.toml` | cargo | Rust |
| `go.mod` | go | Go |

## CI Environment Detection

```bash
# Am I running in CI?
if [[ -n "${CI:-}" ]]; then
  echo "Running in CI"
fi

# Which CI?
if [[ -n "${GITHUB_ACTIONS:-}" ]]; then echo "GitHub Actions"; fi
if [[ -n "${BUILD_BUILDID:-}" ]]; then echo "Azure Pipelines"; fi
if [[ -n "${GITLAB_CI:-}" ]]; then echo "GitLab CI"; fi
```
