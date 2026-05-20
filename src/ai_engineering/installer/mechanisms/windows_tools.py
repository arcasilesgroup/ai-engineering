"""Windows installer mechanisms."""

from __future__ import annotations

from dataclasses import dataclass

from ai_engineering.installer.results import InstallResult

from ._common import run_install


@dataclass(frozen=True)
class WingetMechanism:
    """Install via Windows Package Manager with explicit user scope."""

    package_id: str
    scope: str = "user"

    def install(self) -> InstallResult:
        """Run ``winget install --scope user <package_id>``."""
        return run_install(
            ["winget", "install", "--scope", self.scope, self.package_id],
            mechanism=type(self).__name__,
        )


@dataclass(frozen=True)
class ScoopMechanism:
    """Install via Scoop on Windows (user-scope by design)."""

    package: str

    def install(self) -> InstallResult:
        """Run ``scoop install <package>`` via the safe-run hook."""
        return run_install(["scoop", "install", self.package], mechanism=type(self).__name__)


__all__ = ["ScoopMechanism", "WingetMechanism"]
