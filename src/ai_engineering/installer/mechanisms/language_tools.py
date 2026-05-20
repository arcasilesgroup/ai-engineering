"""Language ecosystem installer mechanisms."""

from __future__ import annotations

from dataclasses import dataclass

from ai_engineering.installer.results import InstallResult

from ._common import run_install


@dataclass(frozen=True)
class DotnetToolMechanism:
    """Install via ``dotnet tool install --global <package>``."""

    package: str

    def install(self) -> InstallResult:
        """Run the .NET user-scope global tool install."""
        return run_install(
            ["dotnet", "tool", "install", "--global", self.package],
            mechanism=type(self).__name__,
        )


@dataclass(frozen=True)
class CargoInstallMechanism:
    """Install via ``cargo install <crate>``."""

    crate: str

    def install(self) -> InstallResult:
        """Run ``cargo install <crate>``."""
        return run_install(["cargo", "install", self.crate], mechanism=type(self).__name__)


@dataclass(frozen=True)
class GoInstallMechanism:
    """Install via ``go install <import_path>``."""

    import_path: str

    def install(self) -> InstallResult:
        """Run ``go install <import_path>``."""
        return run_install(["go", "install", self.import_path], mechanism=type(self).__name__)


@dataclass(frozen=True)
class ComposerGlobalMechanism:
    """Install via ``composer global require <package>``."""

    package: str

    def install(self) -> InstallResult:
        """Run ``composer global require <package>``."""
        return run_install(
            ["composer", "global", "require", self.package],
            mechanism=type(self).__name__,
        )


@dataclass(frozen=True)
class SdkmanMechanism:
    """Install via SDKMAN: ``sdk install <candidate> <version>``."""

    candidate: str
    version: str

    def install(self) -> InstallResult:
        """Run ``sdk install <candidate> <version>``."""
        return run_install(
            ["sdk", "install", self.candidate, self.version],
            mechanism=type(self).__name__,
        )


__all__ = [
    "CargoInstallMechanism",
    "ComposerGlobalMechanism",
    "DotnetToolMechanism",
    "GoInstallMechanism",
    "SdkmanMechanism",
]
