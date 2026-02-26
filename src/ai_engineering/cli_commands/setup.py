"""CLI subcommands for platform credential setup.

Provides the ``ai-eng setup`` command group with subcommands for
each supported platform and a ``platforms`` aggregator command.

Architecture: CLI → platform setup classes → credential service → keyring.
No layer skipping — the CLI layer handles user interaction (prompts,
output), delegates validation to platform classes, and persists state
via the credential service.

Security contract: secret input uses ``typer.prompt(hide_input=True)``.
Tokens are **never** echoed, logged, or written to files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.credentials.models import (
    AzureDevOpsConfig,
    CredentialRef,
    GitHubConfig,
    PlatformKind,
    SonarConfig,
)
from ai_engineering.credentials.service import CredentialService
from ai_engineering.paths import resolve_project_root
from ai_engineering.platforms.detector import detect_platforms

setup_app = typer.Typer(
    name="setup",
    help="Configure platform credentials for governance workflows.",
    no_args_is_help=True,
)


def _state_dir(root: Path) -> Path:
    """Return the ``.ai-engineering/state`` directory for *root*."""
    return root / ".ai-engineering" / "state"


# ------------------------------------------------------------------
# ai-eng setup platforms
# ------------------------------------------------------------------


def setup_platforms_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Detect and configure all platforms found in the repository."""
    root = resolve_project_root(target)
    detected = detect_platforms(root)

    if not detected:
        typer.echo("No platform markers detected. Use individual setup commands instead.")
        typer.echo("  ai-eng setup github")
        typer.echo("  ai-eng setup sonar")
        typer.echo("  ai-eng setup azure-devops")
        return

    typer.echo(f"Detected platforms: {', '.join(p.value for p in detected)}")
    typer.echo("")

    for platform in detected:
        if platform == PlatformKind.GITHUB:
            _run_github_setup(root)
        elif platform == PlatformKind.SONAR:
            _run_sonar_setup(root)
        elif platform == PlatformKind.AZURE_DEVOPS:
            _run_azure_devops_setup(root)
        typer.echo("")


# ------------------------------------------------------------------
# ai-eng setup github
# ------------------------------------------------------------------


def setup_github_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Verify GitHub CLI authentication and scopes."""
    root = resolve_project_root(target)
    _run_github_setup(root)


def _run_github_setup(root: Path) -> None:
    """Execute the GitHub setup flow."""
    from ai_engineering.platforms.github import GitHubSetup

    typer.echo("── GitHub Setup ──")

    if not GitHubSetup.is_cli_installed():
        typer.echo("  ✗ gh CLI not found. Install from: https://cli.github.com/")
        return

    typer.echo("  ✓ gh CLI installed")

    status = GitHubSetup.check_scopes()

    if not status.authenticated:
        typer.echo("  ✗ Not authenticated")
        typer.echo(GitHubSetup.get_login_instructions())
        return

    typer.echo(f"  ✓ Authenticated as: {status.username}")

    if status.missing_scopes:
        typer.echo(f"  ⚠ Missing scopes: {', '.join(status.missing_scopes)}")
        typer.echo("  Run: " + " ".join(GitHubSetup.get_login_command()))
    else:
        typer.echo(f"  ✓ Scopes OK: {', '.join(status.scopes or [])}")

    # Update tools.json state.
    cred_svc = CredentialService()
    state = cred_svc.load_tools_state(_state_dir(root))
    state.github = GitHubConfig(
        configured=status.authenticated,
        cli_authenticated=status.authenticated,
        scopes=status.scopes or [],
    )
    cred_svc.save_tools_state(_state_dir(root), state)
    typer.echo("  ✓ State saved to tools.json")


# ------------------------------------------------------------------
# ai-eng setup sonar
# ------------------------------------------------------------------


def setup_sonar_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    url: Annotated[
        str,
        typer.Option("--url", "-u", help="Sonar server URL."),
    ] = "",
    project_key: Annotated[
        str,
        typer.Option("--project-key", "-k", help="Sonar project key."),
    ] = "",
) -> None:
    """Configure SonarCloud / SonarQube credentials."""
    root = resolve_project_root(target)
    _run_sonar_setup(root, url_override=url or None, project_key_override=project_key or None)


def _run_sonar_setup(
    root: Path,
    *,
    url_override: str | None = None,
    project_key_override: str | None = None,
) -> None:
    """Execute the Sonar setup flow."""
    from ai_engineering.platforms.sonar import SONARCLOUD_URL, SonarSetup

    typer.echo("── Sonar Setup ──")

    cred_svc = CredentialService()
    sonar = SonarSetup(cred_svc)

    # 1. Get Sonar URL.
    url = url_override or _read_sonar_url_from_properties(root)
    if not url:
        url = typer.prompt(
            "  Sonar server URL",
            default=SONARCLOUD_URL,
        )

    # 2. Show token generation instructions.
    token_url = SonarSetup.get_token_url(url)
    typer.echo(f"  Open to generate a token: {token_url}")

    # 3. Prompt for token (hidden input).
    token = typer.prompt("  Sonar token", hide_input=True)

    # 4. Validate token.
    typer.echo("  Validating token...")
    result = sonar.validate_token(url, token)

    if not result.valid:
        typer.echo(f"  ✗ Validation failed: {result.error}")
        return

    typer.echo("  ✓ Token valid")

    # 5. Store in keyring.
    sonar.store_token(token)
    typer.echo("  ✓ Token stored in OS secret store")

    # 6. Get project key.
    project_key = project_key_override or _read_sonar_project_key(root) or ""

    # 7. Update tools.json state.
    state = cred_svc.load_tools_state(_state_dir(root))
    state.sonar = SonarConfig(
        configured=True,
        url=url,
        project_key=project_key,
        credential_ref=CredentialRef(
            service_name=cred_svc.service_name("sonar"),
            username="token",
            configured=True,
        ),
    )
    cred_svc.save_tools_state(_state_dir(root), state)
    typer.echo("  ✓ State saved to tools.json")


def _read_sonar_url_from_properties(root: Path) -> str:
    """Read the Sonar server URL from ``sonar-project.properties`` if present."""
    props_file = root / "sonar-project.properties"
    if not props_file.is_file():
        return ""
    try:
        for line in props_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("sonar.host.url="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


def _read_sonar_project_key(root: Path) -> str:
    """Read the Sonar project key from ``sonar-project.properties`` if present."""
    props_file = root / "sonar-project.properties"
    if not props_file.is_file():
        return ""
    try:
        for line in props_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("sonar.projectKey="):
                return line.split("=", 1)[1].strip()
    except OSError:
        pass
    return ""


# ------------------------------------------------------------------
# ai-eng setup azure-devops
# ------------------------------------------------------------------


def setup_azure_devops_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    org_url: Annotated[
        str,
        typer.Option("--org-url", "-o", help="Azure DevOps organisation URL."),
    ] = "",
) -> None:
    """Configure Azure DevOps PAT credentials."""
    root = resolve_project_root(target)
    _run_azure_devops_setup(root, org_url_override=org_url or None)


def _run_azure_devops_setup(root: Path, *, org_url_override: str | None = None) -> None:
    """Execute the Azure DevOps setup flow."""
    from ai_engineering.platforms.azure_devops import AzureDevOpsSetup

    typer.echo("── Azure DevOps Setup ──")

    cred_svc = CredentialService()
    azdo = AzureDevOpsSetup(cred_svc)

    # 1. Get org URL.
    org_url = org_url_override or ""
    if not org_url:
        org_url = typer.prompt("  Azure DevOps organisation URL")

    # 2. Show PAT generation instructions.
    token_url = AzureDevOpsSetup.get_token_url(org_url)
    typer.echo(f"  Open to generate a PAT: {token_url}")

    # 3. Prompt for PAT (hidden input).
    pat = typer.prompt("  Azure DevOps PAT", hide_input=True)

    # 4. Validate PAT.
    typer.echo("  Validating PAT...")
    result = azdo.validate_pat(org_url, pat)

    if not result.valid:
        typer.echo(f"  ✗ Validation failed: {result.error}")
        return

    typer.echo("  ✓ PAT valid")

    # 5. Store in keyring.
    azdo.store_pat(pat)
    typer.echo("  ✓ PAT stored in OS secret store")

    # 6. Update tools.json state.
    state = cred_svc.load_tools_state(_state_dir(root))
    state.azure_devops = AzureDevOpsConfig(
        configured=True,
        org_url=org_url,
        credential_ref=CredentialRef(
            service_name=cred_svc.service_name("azure_devops"),
            username="pat",
            configured=True,
        ),
    )
    cred_svc.save_tools_state(_state_dir(root), state)
    typer.echo("  ✓ State saved to tools.json")
