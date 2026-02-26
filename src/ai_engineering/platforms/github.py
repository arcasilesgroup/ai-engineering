"""GitHub platform setup — verify ``gh`` CLI auth and scopes.

Uses the ``gh`` CLI (not API tokens) for authentication following
GitHub's recommended OAuth device flow. This setup class verifies
existing auth rather than storing separate credentials.

Security contract: no tokens are stored by this module — ``gh``
manages its own credential storage via the OS keychain.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Scopes required for full ai-engineering governance workflows.
_REQUIRED_SCOPES: frozenset[str] = frozenset({"repo", "workflow", "read:org"})

# Timeout for subprocess calls (seconds).
_SUBPROCESS_TIMEOUT: int = 15


@dataclass
class GitHubStatus:
    """Result of GitHub CLI status check."""

    cli_installed: bool = False
    authenticated: bool = False
    username: str = ""
    scopes: list[str] | None = None
    missing_scopes: list[str] | None = None
    error: str = ""


class GitHubSetup:
    """Verify and guide GitHub CLI authentication.

    This class does **not** store credentials — it delegates entirely
    to ``gh auth``, which uses the OS keychain. The setup flow:

    1. Check ``gh`` CLI is installed.
    2. Verify ``gh auth status`` reports authenticated.
    3. Check OAuth scopes include ``repo``, ``workflow``, ``read:org``.
    4. Guide the user through ``gh auth login`` if needed.
    """

    @staticmethod
    def is_cli_installed() -> bool:
        """Return ``True`` if the ``gh`` CLI is available on PATH."""
        return shutil.which("gh") is not None

    @staticmethod
    def check_auth_status() -> GitHubStatus:
        """Check the current ``gh`` CLI authentication status.

        Returns a :class:`GitHubStatus` with details about the
        authenticated user and scopes, or error information.
        """
        status = GitHubStatus()

        if not GitHubSetup.is_cli_installed():
            status.error = "gh CLI not installed"
            return status

        status.cli_installed = True

        try:
            result = subprocess.run(
                ["gh", "auth", "status", "--show-token"],
                capture_output=True,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            status.error = f"Failed to run gh auth status: {exc}"
            return status

        output = result.stdout + result.stderr
        if result.returncode != 0:
            status.error = "Not authenticated with gh CLI"
            return status

        status.authenticated = True

        # Parse username from `gh auth status` output.
        for line in output.splitlines():
            stripped = line.strip()
            if "Logged in to" in stripped and "account" in stripped:
                # Format: "Logged in to github.com account USERNAME ..."
                parts = stripped.split("account")
                if len(parts) > 1:
                    status.username = parts[1].strip().split()[0].strip("()")
                break

        return status

    @staticmethod
    def check_scopes() -> GitHubStatus:
        """Check the authenticated user's OAuth scopes.

        Queries ``gh api`` to determine which scopes are available
        and reports any missing required scopes.
        """
        status = GitHubSetup.check_auth_status()
        if not status.authenticated:
            return status

        try:
            result = subprocess.run(
                ["gh", "api", "-i", "https://api.github.com/user"],
                capture_output=True,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
            status.error = f"Failed to check scopes: {exc}"
            return status

        if result.returncode != 0:
            status.error = "Failed to query GitHub API for scope check"
            return status

        # Parse X-OAuth-Scopes header from response headers.
        scopes: list[str] = []
        for line in result.stdout.splitlines():
            if line.lower().startswith("x-oauth-scopes:"):
                scope_str = line.split(":", 1)[1].strip()
                scopes = [s.strip() for s in scope_str.split(",") if s.strip()]
                break

        status.scopes = scopes
        status.missing_scopes = sorted(_REQUIRED_SCOPES - set(scopes))
        return status

    @staticmethod
    def get_login_command() -> list[str]:
        """Return the command to authenticate with ``gh`` CLI.

        The returned command uses interactive OAuth device flow with
        the required scopes.
        """
        scopes_str = ",".join(sorted(_REQUIRED_SCOPES))
        return ["gh", "auth", "login", "--scopes", scopes_str]

    @staticmethod
    def get_login_instructions() -> str:
        """Return user-facing instructions for GitHub CLI setup."""
        cmd = " ".join(GitHubSetup.get_login_command())
        return (
            "GitHub CLI authentication required.\n"
            f"\n  Run: {cmd}\n"
            "\nThis will open a browser for GitHub OAuth device flow.\n"
            "Required scopes: repo, workflow, read:org"
        )

    @staticmethod
    def get_user_info() -> dict[str, str]:
        """Return basic GitHub user info via ``gh api``.

        Returns a dict with ``login`` and ``name`` keys, or empty
        dict on failure.
        """
        try:
            result = subprocess.run(
                ["gh", "api", "/user", "--jq", ".login,.name"],
                capture_output=True,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().splitlines()
                return {
                    "login": lines[0] if lines else "",
                    "name": lines[1] if len(lines) > 1 else "",
                }
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return {}
