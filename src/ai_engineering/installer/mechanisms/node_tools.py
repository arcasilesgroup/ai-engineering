"""Node/package-manager installer mechanisms."""

from __future__ import annotations

from dataclasses import dataclass

from ai_engineering.installer.results import InstallResult

from ._common import run_install


@dataclass(frozen=True)
class NpmDevMechanism:
    """Install via ``npm install --save-dev <package>`` (project-local)."""

    package: str

    def install(self) -> InstallResult:
        """Run ``npm install --save-dev <package>`` via the safe-run hook."""
        return run_install(
            ["npm", "install", "--save-dev", self.package],
            mechanism=type(self).__name__,
        )


__all__ = ["NpmDevMechanism"]
