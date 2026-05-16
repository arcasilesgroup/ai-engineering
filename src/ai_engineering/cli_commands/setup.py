"""CLI subcommands for platform credential setup.

Provides the ``ai-eng setup`` command group with subcommands for
each supported platform and a ``platforms`` aggregator command.

Architecture: CLI -> platform setup classes -> credential service -> keyring.
No layer skipping -- the CLI layer handles user interaction (prompts,
output), delegates validation to platform classes, and persists state
via the credential service.

Security contract: secret input uses ``typer.prompt(hide_input=True)``.
Tokens are **never** echoed, logged, or written to files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import click.exceptions
import typer

from ai_engineering.cli_envelope import emit_error, emit_success
from ai_engineering.cli_output import is_json_mode
from ai_engineering.cli_ui import error, header, info, kv, success, warning
from ai_engineering.credentials.models import (
    PlatformKind,
)
from ai_engineering.credentials.service import CredentialService
from ai_engineering.paths import resolve_project_root
from ai_engineering.platforms.detector import detect_platforms
from ai_engineering.state.models import CredentialRef as StateCredentialRef
from ai_engineering.state.models import PlatformEntry
from ai_engineering.state.service import load_install_state, save_install_state

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


@setup_app.command("platforms")
def setup_platforms_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    vcs_provider: str | None = None,
) -> None:
    """Detect and configure all platforms found in the repository."""
    root = resolve_project_root(target)

    if is_json_mode():
        detected = detect_platforms(root)
        state = load_install_state(_state_dir(root))
        gh_entry = state.platforms.get("github")
        sonar_entry = state.platforms.get("sonar")
        azdo_entry = state.platforms.get("azure_devops")
        emit_success(
            "ai-eng setup platforms",
            {
                "detected": [p.value for p in detected],
                "configured": {
                    "github": gh_entry.configured if gh_entry else False,
                    "sonar": sonar_entry.configured if sonar_entry else False,
                    "azure_devops": azdo_entry.configured if azdo_entry else False,
                },
            },
        )
        return

    detected = detect_platforms(root)

    if detected:
        kv("Detected platforms", ", ".join(p.value for p in detected))
        typer.echo("")

        for platform in detected:
            if platform == PlatformKind.GITHUB:
                _run_github_setup(root)
            elif platform == PlatformKind.SONAR:
                _run_sonar_setup(root)
            elif platform == PlatformKind.AZURE_DEVOPS:
                _run_azure_devops_setup(root)
            typer.echo("")
    else:
        info("No platform markers auto-detected.")
        typer.echo("")

    # Offer to configure platforms that were not auto-detected.
    all_platforms = set(PlatformKind)
    undetected = all_platforms - set(detected)

    # Filter out opposite VCS platform — only offer VCS-agnostic platforms + matching VCS.
    if vcs_provider == "azure_devops":
        undetected.discard(PlatformKind.GITHUB)
    elif vcs_provider == "github":
        undetected.discard(PlatformKind.AZURE_DEVOPS)

    if undetected:
        names = ", ".join(p.value for p in sorted(undetected, key=lambda p: p.value))
        info(f"Not auto-detected: {names}")
        for platform in sorted(undetected, key=lambda p: p.value):
            try:
                if typer.confirm(f"  Configure {platform.value}?", default=False):
                    if platform == PlatformKind.GITHUB:
                        _run_github_setup(root)
                    elif platform == PlatformKind.SONAR:
                        _run_sonar_setup(root)
                    elif platform == PlatformKind.AZURE_DEVOPS:
                        _run_azure_devops_setup(root)
                    typer.echo("")
            except (KeyboardInterrupt, EOFError, click.exceptions.Abort):
                break

    # After platform setup, offer SonarLint IDE configuration if Sonar is configured.
    state = load_install_state(_state_dir(root))
    sonar_entry = state.platforms.get("sonar")
    if sonar_entry and sonar_entry.configured and sonar_entry.url:
        header("SonarLint IDE Configuration")
        if typer.confirm("  Configure SonarLint Connected Mode in your IDEs?", default=True):
            _run_sonarlint_setup(root)


# ------------------------------------------------------------------
# ai-eng setup github
# ------------------------------------------------------------------


@setup_app.command("github")
def setup_github_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
) -> None:
    """Verify GitHub CLI authentication and scopes."""
    if is_json_mode():
        from ai_engineering.platforms.github import GitHubSetup

        root = resolve_project_root(target)
        cli_installed = GitHubSetup.is_cli_installed()
        status = GitHubSetup.check_scopes() if cli_installed else None
        emit_success(
            "ai-eng setup github",
            {
                "cli_installed": cli_installed,
                "authenticated": status.authenticated if status else False,
                "username": status.username if status and status.authenticated else "",
            },
        )
        return
    root = resolve_project_root(target)
    _run_github_setup(root)


def _run_github_setup(root: Path) -> None:
    """Execute the GitHub setup flow."""
    from ai_engineering.platforms.github import GitHubSetup

    header("GitHub Setup")

    if not GitHubSetup.is_cli_installed():
        error("gh CLI not found. Install from: https://cli.github.com/")
        return

    success("gh CLI installed")

    status = GitHubSetup.check_scopes()

    if not status.authenticated:
        error("Not authenticated")
        typer.echo(GitHubSetup.get_login_instructions())
        return

    success(f"Authenticated as: {status.username}")

    if status.missing_scopes:
        warning(f"Missing scopes: {', '.join(status.missing_scopes)}")
        info("Run: " + " ".join(GitHubSetup.get_login_command()))
    else:
        success(f"Scopes OK: {', '.join(status.scopes or [])}")

    # Update install_state.platforms (state.db singleton row).
    state = load_install_state(_state_dir(root))
    state.platforms["github"] = PlatformEntry(
        configured=status.authenticated,
        url="https://github.com",
    )
    save_install_state(_state_dir(root), state)
    success("State saved to install_state table")


# ------------------------------------------------------------------
# ai-eng setup sonar
# ------------------------------------------------------------------


@setup_app.command("sonar")
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
    organization: Annotated[
        str,
        typer.Option("--organization", "-o", help="Sonar organization (SonarCloud)."),
    ] = "",
) -> None:
    """Configure SonarCloud / SonarQube credentials."""
    if is_json_mode():
        emit_error(
            "ai-eng setup sonar",
            "Interactive command requires terminal input",
            "INTERACTIVE_REQUIRED",
            "Run without --json",
        )
        return
    root = resolve_project_root(target)
    _run_sonar_setup(
        root,
        url_override=url or None,
        project_key_override=project_key or None,
        organization_override=organization or None,
    )


def _run_sonar_setup(
    root: Path,
    *,
    url_override: str | None = None,
    project_key_override: str | None = None,
    organization_override: str | None = None,
) -> None:
    """Execute the Sonar setup flow."""
    from ai_engineering.platforms.sonar import SONARCLOUD_URL, SonarSetup

    header("Sonar Setup")

    cred_svc = CredentialService()
    sonar = SonarSetup(cred_svc)

    # 1. Get Sonar URL.
    url = url_override or _read_sonar_property(root, "sonar.host.url")
    if not url:
        url = typer.prompt(
            "  Sonar server base URL (e.g. https://sonarcloud.io)",
            default=SONARCLOUD_URL,
        )

    # 2. Show token generation instructions.
    token_url = SonarSetup.get_token_url(url)
    info(f"Open to generate a token: {token_url}")

    # 3. Prompt for token (hidden input).
    token = typer.prompt("  Sonar token", hide_input=True)

    # 4. Validate token.
    info("Validating token...")
    result = sonar.validate_token(url, token)

    if not result.valid:
        error(f"Validation failed: {result.error}")
        return

    success("Token valid")

    # 5. Store in keyring.
    sonar.store_token(token)
    success("Token stored in OS secret store")

    # 6. Get project key.
    project_key = project_key_override or _read_sonar_property(root, "sonar.projectKey") or ""
    organization = organization_override or _read_sonar_property(root, "sonar.organization") or ""

    # 7. Update install_state.platforms (state.db singleton row).
    state = load_install_state(_state_dir(root))
    state.platforms["sonar"] = PlatformEntry(
        configured=True,
        url=url,
        project_key=project_key,
        organization=organization,
        credential_ref=StateCredentialRef(
            service=cred_svc.service_name("sonar"),
            username="token",
        ),
    )
    save_install_state(_state_dir(root), state)
    success("State saved to install_state table")


def _read_sonar_property(root: Path, key: str) -> str | None:
    """Read a property value from ``sonar-project.properties``."""
    props = root / "sonar-project.properties"
    if not props.exists():
        return None
    for line in props.read_text(encoding="utf-8").splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()
    return None


# ------------------------------------------------------------------
# ai-eng setup azure-devops
# ------------------------------------------------------------------


@setup_app.command("azure-devops")
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
    if is_json_mode():
        emit_error(
            "ai-eng setup azure-devops",
            "Interactive command requires terminal input",
            "INTERACTIVE_REQUIRED",
            "Run without --json",
        )
        return
    root = resolve_project_root(target)
    _run_azure_devops_setup(root, org_url_override=org_url or None)


def _run_azure_devops_setup(root: Path, *, org_url_override: str | None = None) -> None:
    """Execute the Azure DevOps setup flow."""
    from ai_engineering.platforms.azure_devops import AzureDevOpsSetup

    header("Azure DevOps Setup")

    cred_svc = CredentialService()
    azdo = AzureDevOpsSetup(cred_svc)

    # 1. Get org URL.
    org_url = org_url_override or ""
    if not org_url:
        org_url = typer.prompt("  Azure DevOps organisation URL")

    # 2. Show PAT generation instructions.
    token_url = AzureDevOpsSetup.get_token_url(org_url)
    info(f"Open to generate a PAT: {token_url}")

    # 3. Prompt for PAT (hidden input).
    pat = typer.prompt("  Azure DevOps PAT", hide_input=True)

    # 4. Validate PAT.
    info("Validating PAT...")
    result = azdo.validate_pat(org_url, pat)

    if not result.valid:
        error(f"Validation failed: {result.error}")
        return

    success("PAT valid")

    # 5. Store in keyring.
    azdo.store_pat(pat)
    success("PAT stored in OS secret store")

    # 6. Update install_state.platforms (state.db singleton row).
    state = load_install_state(_state_dir(root))
    state.platforms["azure_devops"] = PlatformEntry(
        configured=True,
        url=org_url,
        credential_ref=StateCredentialRef(
            service=cred_svc.service_name("azure_devops"),
            username="pat",
        ),
    )
    save_install_state(_state_dir(root), state)
    success("State saved to install_state table")


# ------------------------------------------------------------------
# ai-eng setup sonarlint
# ------------------------------------------------------------------


@setup_app.command("sonarlint")
def setup_sonarlint_cmd(
    target: Annotated[
        Path | None,
        typer.Argument(help="Target project root. Defaults to cwd."),
    ] = None,
    url: Annotated[
        str,
        typer.Option("--url", "-u", help="Sonar server URL override."),
    ] = "",
    project_key: Annotated[
        str,
        typer.Option("--project-key", "-k", help="Sonar project key override."),
    ] = "",
) -> None:
    """Configure SonarLint Connected Mode in all detected IDEs."""
    if is_json_mode():
        emit_error(
            "ai-eng setup sonarlint",
            "Interactive command requires terminal input",
            "INTERACTIVE_REQUIRED",
            "Run without --json",
        )
        return
    root = resolve_project_root(target)
    _run_sonarlint_setup(root, url_override=url or None, project_key_override=project_key or None)


def _run_sonarlint_setup(
    root: Path,
    *,
    url_override: str | None = None,
    project_key_override: str | None = None,
) -> None:
    """Execute the SonarLint IDE configuration flow."""
    from ai_engineering.platforms.sonarlint import (
        IDEFamily,
        configure_all_ides,
        detect_ide_families,
    )

    header("SonarLint IDE Setup")

    # 1. Resolve Sonar connection info.
    state = load_install_state(_state_dir(root))
    sonar_entry = state.platforms.get("sonar")

    sonar_url = (
        url_override
        or (sonar_entry.url if sonar_entry else "")
        or _read_sonar_property(root, "sonar.host.url")
    )
    project_key = (
        project_key_override
        or (sonar_entry.project_key if sonar_entry else "")
        or _read_sonar_property(root, "sonar.projectKey")
    )

    if not sonar_url:
        warning("No Sonar server URL configured.")
        info("Run 'ai-eng setup sonar' first to configure SonarCloud/SonarQube credentials.")
        return

    if not project_key:
        warning("No Sonar project key found.")
        info("Set sonar.projectKey in sonar-project.properties or use --project-key.")
        return

    # 2. Detect IDE families.
    families = detect_ide_families(root)

    if not families:
        info("No IDE workspace markers detected (.vscode/, .idea/, .vs/).")
        info("Create the IDE config folder first, or specify IDEs manually.")
        typer.echo("")
        if typer.confirm(
            "  Create .vscode/ for VS Code / Cursor / Windsurf / Antigravity?",
            default=True,
        ):
            (root / ".vscode").mkdir(parents=True, exist_ok=True)
            families.append(IDEFamily.VSCODE)
        if typer.confirm(
            "  Create .idea/ for JetBrains IDEs (IntelliJ, Rider, etc.)?",
            default=False,
        ):
            (root / ".idea").mkdir(parents=True, exist_ok=True)
            families.append(IDEFamily.JETBRAINS)
        if typer.confirm("  Create .vs/ for Visual Studio 2022?", default=False):
            (root / ".vs").mkdir(parents=True, exist_ok=True)
            families.append(IDEFamily.VS2022)

    if not families:
        info("No IDEs selected. Skipping SonarLint setup.")
        return

    kv("Detected IDEs", ", ".join(f.value for f in families))
    kv("Sonar URL", sonar_url)
    kv("Project key", project_key)
    typer.echo("")

    # 3. Configure all detected IDEs.
    summary = configure_all_ides(root, sonar_url, project_key, ide_families=families)

    for result in summary.results:
        if result.success:
            success(f"{result.ide_family}: {', '.join(result.files_written)}")
        else:
            error(f"{result.ide_family}: {result.error}")

    if summary.any_success:
        typer.echo("")
        info("SonarLint Connected Mode configured. Open your IDE to activate.")
        info("Token authentication will be handled by SonarLint in the IDE.")
