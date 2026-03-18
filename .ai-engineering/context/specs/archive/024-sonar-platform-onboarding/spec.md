---
id: "024"
slug: "sonar-platform-onboarding"
status: "in-progress"
created: "2026-02-26"
---

# Spec 024 — Sonar Scanner Integration & Platform Credential Onboarding

## Problem

Teams that adopt ai-engineering can enforce quality gates locally (ruff, ty, pytest, gitleaks, semgrep), but have **no way to anticipate SonarCloud/SonarQube quality gate failures** before push. Additionally, the install flow does not help teams configure platform credentials (GitHub, Azure DevOps, SonarCloud/SonarQube), forcing manual and error-prone setup that often leads to:

1. **Surprise quality gate failures** in CI/CD when Sonar thresholds differ from local checks.
2. **Insecure credential handling** — tokens stored in `.env` files tracked by git, or hardcoded in scripts.
3. **Incomplete platform setup** — teams skip auth configuration and later hit permission errors in `/pr` or `/commit` workflows.
4. **No re-runnable onboarding** — once the initial install is done, there is no `ai-eng` command to reconfigure platform credentials.

## Solution

Extend the ai-engineering framework with three capabilities:

### 1. Platform Credential Onboarding (`ai-eng setup platforms`)

An interactive, **optional** onboarding flow during `ai-eng install` (and re-runnable via `ai-eng setup`) that:

- **Detects platform context** from repository markers (`.github/`, `azure-pipelines.yml`, `sonar-project.properties`).
- **Guides credential configuration** for GitHub (`gh` CLI OAuth), Azure DevOps (PAT via browser), and SonarCloud/SonarQube (token via browser).
- **Stores credentials exclusively in OS-native secret stores** (Windows Credential Manager, macOS Keychain, Linux libsecret) using the `keyring` Python library.
- **Validates credentials** via platform APIs before persisting.
- **Records platform state** (not secrets) in `.ai-engineering/state/tools.json`.

### 2. Sonar Scanner Quality Gate Integration

A new optional quality gate that runs `sonar-scanner` locally before push:

- Cross-OS scripts (`sonar-pre-gate.sh` / `sonar-pre-gate.ps1`) that execute Sonar analysis with `qualitygate.wait=true`.
- Integration as an optional gate in `audit-code`, `release-gate`, and pre-push hook.
- **Silent skip** when `SONAR_TOKEN` is not configured — never blocks teams that don't use Sonar.
- Threshold mapping that mirrors the existing quality contract (90% coverage, ≤3% duplication, ≤10 cyclomatic complexity, ≤15 cognitive complexity, zero blockers/criticals).

### 3. New CLI Subcommands

| Command | Purpose |
|---------|---------|
| `ai-eng setup platforms` | Full platform onboarding (all detected platforms) |
| `ai-eng setup sonar` | SonarCloud/SonarQube credential setup only |
| `ai-eng setup github` | GitHub CLI auth verification/setup only |
| `ai-eng setup azure-devops` | Azure DevOps PAT setup only |
| `ai-eng setup sonarlint` | Configure SonarLint in all detected IDEs |
| `ai-eng doctor --check-platforms` | Validate stored credentials are still valid |

### 4. SonarLint IDE Configuration (`ai-eng setup sonarlint`)

Automated SonarLint extension configuration across all major IDEs:

- **Detects installed IDEs** from workspace markers (`.vscode/`, `.idea/`, `.vs/`, `.cursor/`, `.windsurf/`, `.antigravity/`).
- **Generates IDE-specific configuration** files for SonarLint with Connected Mode pointing to the configured SonarCloud/SonarQube instance.
- **Supports 4 IDE families**:
  - **VS Code family** (VS Code, Cursor, Windsurf, Antigravity): `.vscode/settings.json` with `sonarlint.connectedMode.*` properties + `extensions.json` recommendation.
  - **JetBrains family** (IntelliJ, Rider, WebStorm, PyCharm, etc.): `.idea/sonarlint/` XML configuration with connection binding.
  - **Visual Studio 2022**: `.vs/SonarLint/settings.json` with connection binding.
- **Adds extension recommendations** where supported (VS Code `extensions.json`).
- **Preserves existing settings** — merges SonarLint keys into existing JSON/XML, never overwrites user content.
- **Silent skip** when Sonar credentials are not configured — suggests running `ai-eng setup sonar` first.

## Scope

### In Scope

- `keyring` dependency addition to `pyproject.toml`.
- New `src/ai_engineering/credentials/` module for OS-native secret storage.
- New `src/ai_engineering/cli_commands/setup.py` module for `setup` subcommand group.
- New `src/ai_engineering/platforms/` module for platform detection and validation.
- New `src/ai_engineering/platforms/sonarlint.py` module for multi-IDE SonarLint configuration.
- New skill: `dev/sonar-gate/SKILL.md` with cross-OS scripts.
- Modifications to `install-check`, `audit-code`, and `release-gate` skills (add optional Sonar gate references).
- New `.ai-engineering/state/tools.json` schema definition.
- `doctor` command extension with `--check-platforms` flag.
- Cross-OS Sonar scanner wrapper scripts (Bash + PowerShell).
- SonarLint Connected Mode configuration for VS Code, Cursor, Windsurf, Antigravity, JetBrains IDEs, Rider, and Visual Studio 2022.
- IDE auto-detection from workspace markers.
- Extension recommendation injection (`extensions.json`).
- Unit and integration tests for credentials module, platform detection, Sonar gate, and SonarLint IDE config.

### Out of Scope

- Running a local SonarQube server — teams bring their own SonarCloud/SonarQube instance.
- Sonar project creation or configuration — teams configure `sonar-project.properties` independently.
- Modifying existing hook scripts beyond adding the optional Sonar gate call.
- Team-managed or project-managed content changes.
- GitHub Actions / Azure Pipelines CI/CD Sonar integration (this spec covers local/pre-push only).
- Other credential types (e.g., npm tokens, Docker registry) — future spec.

## Acceptance Criteria

1. `ai-eng install` presents optional platform onboarding prompts after standard install.
2. `ai-eng setup platforms` detects GitHub/Azure DevOps/Sonar from repository markers.
3. GitHub setup verifies `gh` CLI auth or guides through `gh auth login`.
4. SonarCloud/SonarQube setup validates token via API and stores in OS secret store.
5. Azure DevOps setup validates PAT via API and stores in OS secret store.
6. All credentials stored exclusively via `keyring` — never in plain text on disk.
7. `.ai-engineering/state/tools.json` stores only non-secret metadata (URLs, project keys, `configured: true/false`).
8. `ai-eng doctor --check-platforms` validates that stored credentials are still valid.
9. Sonar pre-gate scripts execute `sonar-scanner` with `qualitygate.wait=true` on both Bash and PowerShell.
10. Sonar gate silently skips when `SONAR_TOKEN` is not configured.
11. `audit-code` skill includes optional Sonar gate step (runs if configured, skips if not).
12. `release-gate` skill includes Sonar gate as an optional dimension.
13. Sonar thresholds mirror the quality contract: 90% coverage, ≤3% duplication, ≤10 CC, ≤15 CogC, 0 blockers/criticals.
14. Cross-OS: all flows work on Windows, macOS, and Linux.
15. Unit tests for `credentials/`, `platforms/`, and Sonar gate logic achieve ≥90% coverage.
16. No secrets appear in terminal output, logs, or tracked files.
17. `gitleaks`/`semgrep` pass with zero findings after implementation.
18. All instruction files updated with new skill references and skill counts.
19. `ai-eng setup sonarlint` detects VS Code, Cursor, Windsurf, Antigravity, JetBrains, Rider, and VS 2022 from workspace markers.
20. SonarLint Connected Mode config generated for each detected IDE family.
21. VS Code family: `settings.json` updated with `sonarlint.connectedMode.*` + `extensions.json` with SonarLint recommendation.
22. JetBrains family: `.idea/sonarlint/` XML binding generated.
23. Visual Studio 2022: `.vs/SonarLint/settings.json` generated.
24. Existing IDE settings preserved (merge, not overwrite).
25. SonarLint setup silently skips when Sonar credentials are not configured.

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D024-001 | Use `keyring` library for OS-native secret storage | Cross-OS abstraction over Windows Credential Manager, macOS Keychain, and Linux libsecret. Pure Python, well-maintained, no native compilation needed. |
| D024-002 | Sonar gate is optional and silent-skip | Framework principle: mandatory gates cannot be weakened, but optional integrations should not block teams that don't use them. |
| D024-003 | Platform onboarding is opt-in during install | Framework contract §6: install must ensure first-commit readiness. Platform auth is helpful but not required for local governance. |
| D024-004 | New `setup` CLI subcommand group instead of extending `install` | `install` has a defined contract (copy templates, hooks, readiness). Platform onboarding is a separate concern with its own re-runnability requirement. |
| D024-005 | `tools.json` in `.ai-engineering/state/` for platform metadata | Follows existing state file pattern. Only non-secret metadata stored. File is system-managed (ownership model). |
| D024-006 | New skill `dev/sonar-gate` rather than embedding in `audit-code` | Skills are single-responsibility. `audit-code` orchestrates gates; `sonar-gate` provides the Sonar-specific procedure. Follows existing pattern (audit-code references quality/core.md). |
| D024-007 | SonarLint IDE config uses Connected Mode, not standalone rules | Connected Mode syncs rules from SonarCloud/SonarQube server, ensuring parity between IDE and CI. Standalone mode would require maintaining separate rule sets. |
| D024-008 | VS Code family IDEs (Cursor, Windsurf, Antigravity) share `.vscode/` config path | All VS Code forks read `settings.json` and `extensions.json` from `.vscode/`. One config serves multiple IDEs. |
| D024-009 | Merge strategy for existing IDE settings JSON files | Read existing JSON, deep-merge SonarLint keys only, write back. Never overwrite user-configured keys outside the `sonarlint` namespace. |
