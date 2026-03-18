# SonarLint-like Local Profile

## Update Metadata

- Rationale: align severity mapping with quality/core.md gate structure for v2; add per-IDE Connected Mode guidance.
- Expected gain: earlier feedback before pre-commit and pre-push checks; consistent severity across IDE and CI.
- Potential impact: developers may need to tune editor rules to avoid noise while preserving severity.

## Rule Families

- correctness and reliability issues,
- maintainability and complexity issues,
- security-sensitive coding patterns,
- duplication and readability issues.

## Recommended Policy

- Treat blocker and critical findings as errors.
- Treat major findings as warnings that must be resolved before merge.
- Treat minor/info findings as backlog improvements.

## Integration Guidance

- Use this profile as local coding baseline in IDE diagnostics.
- Keep server-side Sonar integration optional; do not require local SonarQube server.
- Preserve parity with framework quality profile in `quality/core.md`.
- Use `ai-eng setup sonarlint` to auto-configure Connected Mode for all detected IDEs.

## IDE-Specific Configuration

### VS Code / Cursor / Windsurf / Antigravity

All VS Code forks read from `.vscode/settings.json` and `.vscode/extensions.json` (D024-008).

- **Extension**: `SonarSource.sonarlint-vscode`
- **Connected Mode settings**:
  - `sonarlint.connectedMode.connections.sonarcloud` (for SonarCloud)
  - `sonarlint.connectedMode.connections.sonarqube` (for self-hosted)
  - `sonarlint.connectedMode.project` (project binding)
- **Auto-configured by**: `ai-eng setup sonarlint`
- **Token**: SonarLint prompts for token on first use; stored in VS Code's secret storage.

### JetBrains IDEs (IntelliJ, Rider, WebStorm, PyCharm, GoLand, etc.)

All JetBrains IDEs read project-level settings from `.idea/`.

- **Plugin**: SonarLint (bundled in JetBrains Marketplace)
- **Connected Mode config**:
  - `.idea/sonarlint.xml` — connection binding and project settings
  - `.idea/sonarlint/connectedMode.json` — modern plugin format
- **Auto-configured by**: `ai-eng setup sonarlint`
- **Token**: SonarLint prompts for token on first use; stored in IDE's credential store.

### Visual Studio 2022

- **Extension**: SonarLint for Visual Studio (VSIX from Marketplace)
- **Connected Mode config**:
  - `.vs/SonarLint/settings.json` — connection and project binding
- **Auto-configured by**: `ai-eng setup sonarlint`
- **Token**: SonarLint prompts for token on first use; stored in Windows Credential Manager.

## Connected Mode Rationale (D024-007)

Connected Mode syncs quality profiles and rules from the SonarCloud/SonarQube server directly to the IDE. This ensures:

1. **Parity**: IDE diagnostics match CI/CD quality gate results exactly.
2. **Zero maintenance**: rule updates on the server auto-propagate to developers.
3. **Consistency**: all team members see the same findings regardless of their IDE.

Teams without SonarCloud/SonarQube still benefit from the local profile (ruff, ty, pytest) which mirrors the same quality contract thresholds.
