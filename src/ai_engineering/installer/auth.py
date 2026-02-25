"""VCS authentication checks with API-fallback signaling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_engineering.vcs.protocol import VcsContext, VcsProvider


@dataclass
class AuthResult:
    """Authentication result for install flows."""

    provider: str
    mode: str
    authenticated: bool
    message: str


def check_vcs_auth(provider_name: str, provider: VcsProvider, project_root: Path) -> AuthResult:
    """Check provider auth and choose ``cli`` or ``api`` mode."""
    if not provider.is_available():
        return AuthResult(
            provider=provider_name,
            mode="api",
            authenticated=False,
            message="CLI unavailable; using API fallback mode",
        )

    result = provider.check_auth(VcsContext(project_root=project_root))
    if result.success:
        return AuthResult(
            provider=provider_name,
            mode="cli",
            authenticated=True,
            message="CLI authenticated",
        )

    return AuthResult(
        provider=provider_name,
        mode="api",
        authenticated=False,
        message=f"CLI auth failed; using API fallback mode ({result.output})",
    )
