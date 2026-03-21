# Handler: generate

Create new CI/CD pipeline from project analysis.

## Process

1. **Detect context**:
   - Read project files for stacks: `pyproject.toml` (Python), `*.csproj` (.NET), `package.json` (Node), `Cargo.toml` (Rust).
   - Read `manifest.yml` for VCS provider, Sonar config.
   - Read `cicd.standards_url` from `.ai-engineering/manifest.yml`. If set, fetch and use those standards. If null, generate using AI best practices.

2. **Select provider**:
   - `--provider github`: GitHub Actions (`.github/workflows/`).
   - `--provider azure`: Azure Pipelines (`.azure-pipelines/`).
   - Default: detect from `git remote get-url origin`.

3. **Generate pipelines** -- produce workflow files directly:

   | Provider | Files | Content |
   |----------|-------|---------|
   | GitHub Actions | `ci.yml`, `ai-pr-review.yml` | Multi-job: lint, test, security, gate. Concurrency, timeouts, SHA pinning. |
   | Azure Pipelines | `ci.yml`, `ai-pr-review.yml` | Single-stage: stack checks, security. Triggers and pool config. |

4. **Apply stack checks**:
   - Python: `ruff check`, `ruff format --check`, `pytest`, `pip-audit`, `ty check`.
   - .NET: `dotnet build`, `dotnet test`, `dotnet format --verify-no-changes`.
   - Node: `eslint`, `vitest`, `npm audit`.
   - Rust: `cargo check`, `cargo clippy`, `cargo test`, `cargo audit`.

5. **Apply security**:
   - SHA pin all third-party actions (resolve latest SHA for each action).
   - Add `gitleaks` and `semgrep` jobs.
   - Add `pip-audit` / `npm audit` / `cargo audit` per stack.
   - Configure OIDC for deployment steps where possible.

6. **Apply infrastructure**:
   - `timeout-minutes` on every job.
   - Concurrency group by branch: `group: ${{ github.ref }}`.
   - `dependabot.yml` for automated dependency updates.

7. **Validate** -- `actionlint` on generated files. Fix any issues.

## Output

- Generated workflow files.
- `dependabot.yml` configuration.
- Validation report.
- Branch Protection recommendations.
