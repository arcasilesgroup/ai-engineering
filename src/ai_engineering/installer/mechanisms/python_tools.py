"""Python installer mechanisms."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ai_engineering.installer.results import InstallResult

from ._common import run_install


@dataclass(frozen=True)
class UvToolMechanism:
    """Install via ``uv tool install <package>`` (user-global)."""

    package: str

    def install(self) -> InstallResult:
        """Run ``uv tool install <package>`` via the package safe-run hook."""
        return run_install(
            ["uv", "tool", "install", self.package],
            mechanism=type(self).__name__,
        )


@dataclass(frozen=True)
class UvPipVenvMechanism:
    """Install via ``uv pip install --python <venv>/bin/python <pkg>``."""

    package: str
    venv: Path

    def install(self) -> InstallResult:
        """Run ``uv pip install`` against the target venv Python."""
        python_path = self.venv / "bin" / "python"
        return run_install(
            ["uv", "pip", "install", "--python", str(python_path), self.package],
            mechanism=type(self).__name__,
        )


__all__ = ["UvPipVenvMechanism", "UvToolMechanism"]
