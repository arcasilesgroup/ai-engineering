"""Tests for install-method detection (spec version-update-notice, sub-002).

``install_method.detect`` inspects the running environment and returns
``(method, upgrade_argv)`` where ``method`` is a human-readable label and
``upgrade_argv`` is the exact command list to upgrade the package. Detection
is pure and accepts injected ``prefix`` / ``package_file`` paths so the
heuristics are deterministic under test.
"""

from __future__ import annotations

import sys
from pathlib import Path

from ai_engineering.version import install_method


class TestDetectPipx:
    """pipx-managed installs upgrade via ``pipx upgrade``."""

    def test_pipx_venvs_path(self) -> None:
        # Arrange
        pkg = Path(
            "/home/u/.local/pipx/venvs/ai-engineering/lib/python3.11/site-packages/ai_engineering/__init__.py"
        )
        prefix = Path("/home/u/.local/pipx/venvs/ai-engineering")

        # Act
        method, argv = install_method.detect(prefix=prefix, package_file=pkg)

        # Assert
        assert method == "pipx"
        assert argv == ["pipx", "upgrade", "ai-engineering"]

    def test_pipx_windows_path(self) -> None:
        # Arrange — Windows-style pipx path uses backslashes / pipx segment.
        pkg = Path(
            "C:/Users/u/pipx/venvs/ai-engineering/Lib/site-packages/ai_engineering/__init__.py"
        )
        prefix = Path("C:/Users/u/pipx/venvs/ai-engineering")

        # Act
        method, argv = install_method.detect(prefix=prefix, package_file=pkg)

        # Assert
        assert method == "pipx"
        assert argv == ["pipx", "upgrade", "ai-engineering"]


class TestDetectUvTool:
    """uv-tool installs upgrade via ``uv tool upgrade``."""

    def test_uv_tools_path(self) -> None:
        # Arrange
        prefix = Path("/home/u/.local/share/uv/tools/ai-engineering")
        pkg = prefix / "lib/python3.11/site-packages/ai_engineering/__init__.py"

        # Act
        method, argv = install_method.detect(prefix=prefix, package_file=pkg)

        # Assert
        assert method == "uv tool"
        assert argv == ["uv", "tool", "upgrade", "ai-engineering"]


class TestDetectBrew:
    """Homebrew installs upgrade via ``brew upgrade``."""

    def test_cellar_path(self) -> None:
        # Arrange
        prefix = Path("/opt/homebrew/Cellar/ai-engineering/0.8.4/libexec")
        pkg = prefix / "lib/python3.11/site-packages/ai_engineering/__init__.py"

        # Act
        method, argv = install_method.detect(prefix=prefix, package_file=pkg)

        # Assert
        assert method == "brew"
        assert argv == ["brew", "upgrade", "ai-engineering"]


class TestDetectPipDefault:
    """Anything else falls back to a pip upgrade against this interpreter."""

    def test_plain_venv_falls_back_to_pip(self) -> None:
        # Arrange
        prefix = Path("/home/u/repos/ai-engineering/.venv")
        pkg = prefix / "lib/python3.11/site-packages/ai_engineering/__init__.py"

        # Act
        method, argv = install_method.detect(prefix=prefix, package_file=pkg)

        # Assert
        assert method == "pip"
        assert argv == [sys.executable, "-m", "pip", "install", "-U", "ai-engineering"]

    def test_system_site_packages_falls_back_to_pip(self) -> None:
        # Arrange
        prefix = Path("/usr")
        pkg = Path("/usr/lib/python3.11/site-packages/ai_engineering/__init__.py")

        # Act
        method, argv = install_method.detect(prefix=prefix, package_file=pkg)

        # Assert
        assert method == "pip"
        assert argv[0] == sys.executable


class TestDetectPipMissing:
    """A pipx/uv standalone tool whose path dodges detection has no usable pip.

    Running ``sys.executable -m pip`` there targets the tool's private venv
    (often pip-less) and fails or upgrades the wrong env. ``detect`` must NOT
    return a doomed pip command in that case — it returns ``unknown`` so the
    caller can print manual guidance instead of executing.
    """

    def test_pip_unavailable_returns_unknown_no_doomed_argv(self) -> None:
        # Arrange — a path that matches none of the manager heuristics, and a
        # venv where ``pip`` is not importable (injected seam).
        prefix = Path("/opt/standalone/ai-engineering")
        pkg = prefix / "lib/python3.11/site-packages/ai_engineering/__init__.py"

        # Act
        method, argv = install_method.detect(prefix=prefix, package_file=pkg, pip_available=False)

        # Assert — distinct method, and NOT a pip-install command list.
        assert method == "unknown"
        assert argv != [sys.executable, "-m", "pip", "install", "-U", "ai-engineering"]

    def test_pip_available_keeps_pip_fallback(self) -> None:
        # Arrange — same unmatched path, but pip IS importable.
        prefix = Path("/opt/standalone/ai-engineering")
        pkg = prefix / "lib/python3.11/site-packages/ai_engineering/__init__.py"

        # Act
        method, argv = install_method.detect(prefix=prefix, package_file=pkg, pip_available=True)

        # Assert — unchanged pip behaviour.
        assert method == "pip"
        assert argv == [sys.executable, "-m", "pip", "install", "-U", "ai-engineering"]


class TestDetectDefaults:
    """Calling detect() with no args inspects the live interpreter."""

    def test_no_args_returns_method_and_argv(self) -> None:
        # Act
        method, argv = install_method.detect()

        # Assert — deterministic shape regardless of environment.
        assert isinstance(method, str) and method
        assert isinstance(argv, list)
        assert all(isinstance(part, str) for part in argv)
