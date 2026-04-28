"""RED-phase tests for spec-101 T-1.7: 12 install mechanism classes.

Per spec D-101-02, every mechanism MUST route subprocess invocation through
`_safe_run` (the user-scope guard). Each mechanism returns an `InstallResult`
capturing success/failure plus stderr on failure. The package
`ai_engineering.installer.mechanisms` does NOT exist yet -- it is created
in T-1.8 GREEN. These tests fail with `ModuleNotFoundError` until then.

Coverage per mechanism:
- Construction with valid args succeeds.
- `install()` calls `_safe_run` with the expected argv shape (mock captures argv).
- `install()` returns an `InstallResult` (success/failure structure).
- Failure path: subprocess returns non-zero -> `InstallResult.failed=True` with
  stderr captured.

Plus parametric `test_all_12_mechanisms_have_install_method` asserts every
class is exposed and callable, and `GitHubReleaseBinaryMechanism` SHA256
mismatch raises `Sha256MismatchError`.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch

import pytest

# These imports MUST FAIL with ModuleNotFoundError until T-1.8 lands.
from ai_engineering.installer.mechanisms import (
    BrewMechanism,
    CargoInstallMechanism,
    ComposerGlobalMechanism,
    DotnetToolMechanism,
    GitHubReleaseBinaryMechanism,
    GoInstallMechanism,
    InstallResult,
    NpmDevMechanism,
    ScoopMechanism,
    SdkmanMechanism,
    Sha256MismatchError,
    UvPipVenvMechanism,
    UvToolMechanism,
    WingetMechanism,
)

# Module path used by mechanisms to invoke the user-scope guard. Tests patch
# this so we can capture argv and simulate subprocess outcomes without
# touching the real subprocess module.
_SAFE_RUN_PATH = "ai_engineering.installer.mechanisms._safe_run"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok_result(stdout: str = "", stderr: str = "") -> SimpleNamespace:
    """Mimic a CompletedProcess-like success object returned by `_safe_run`."""
    return SimpleNamespace(returncode=0, stdout=stdout, stderr=stderr)


def _fail_result(stderr: str = "boom: install failed") -> SimpleNamespace:
    """Mimic a CompletedProcess-like failure object returned by `_safe_run`."""
    return SimpleNamespace(returncode=1, stdout="", stderr=stderr)


def _capture_argv(mock_safe_run: Any) -> list[str]:
    """Return the argv list passed to the most recent `_safe_run` call."""
    assert mock_safe_run.call_count >= 1, "_safe_run was not invoked"
    args, _kwargs = mock_safe_run.call_args
    # `_safe_run` signature is `_safe_run(argv, ...)` per spec.
    argv = args[0] if args else _kwargs.get("argv")
    assert isinstance(argv, list), f"expected argv list, got {type(argv).__name__}"
    return argv


# ---------------------------------------------------------------------------
# 1. BrewMechanism
# ---------------------------------------------------------------------------


class TestBrewMechanism:
    """`BrewMechanism(formula)` runs `brew install <formula>` via `_safe_run`."""

    def test_construction_with_valid_args(self) -> None:
        mech = BrewMechanism("gitleaks")
        assert mech.formula == "gitleaks"

    def test_install_invokes_safe_run_with_brew_argv(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            BrewMechanism("gitleaks").install()
        argv = _capture_argv(mock_run)
        assert argv[0] == "brew"
        assert "install" in argv
        assert "gitleaks" in argv

    def test_install_returns_install_result(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = BrewMechanism("gitleaks").install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("brew: formula not found")):
            result = BrewMechanism("nonexistent").install()
        assert isinstance(result, InstallResult)
        assert result.failed is True
        assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 2. GitHubReleaseBinaryMechanism (SHA256-pinned)
# ---------------------------------------------------------------------------


class TestGitHubReleaseBinaryMechanism:
    """Signed-release fallback: download via `curl`, verify SHA256, `chmod +x`."""

    def test_construction_with_valid_args(self) -> None:
        mech = GitHubReleaseBinaryMechanism(
            repo="gitleaks/gitleaks",
            binary="gitleaks",
            sha256_pinned=True,
        )
        assert mech.repo == "gitleaks/gitleaks"
        assert mech.binary == "gitleaks"
        assert mech.sha256_pinned is True

    def test_install_invokes_safe_run_with_curl_argv(self) -> None:
        # Patch _verify_sha256 to a no-op so this test focuses on argv shape;
        # SHA-pin enforcement has a dedicated test below.
        with (
            patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run,
            patch("ai_engineering.installer.mechanisms._verify_sha256"),
        ):
            GitHubReleaseBinaryMechanism(
                "gitleaks/gitleaks", "gitleaks", sha256_pinned=True
            ).install()
        # First call MUST be a `curl`-flavoured download routed through `_safe_run`.
        first_argv = mock_run.call_args_list[0].args[0]
        assert first_argv[0] == "curl", f"expected curl as argv[0], got {first_argv[0]}"
        assert any("gitleaks/gitleaks" in tok for tok in first_argv), (
            "argv must reference the repo path"
        )

    def test_install_returns_install_result(self) -> None:
        with (
            patch(_SAFE_RUN_PATH, return_value=_ok_result()),
            patch("ai_engineering.installer.mechanisms._verify_sha256"),
        ):
            result = GitHubReleaseBinaryMechanism(
                "gitleaks/gitleaks", "gitleaks", sha256_pinned=True
            ).install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        # _safe_run failure short-circuits BEFORE _verify_sha256 fires, so no
        # need to patch the verifier here.
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("curl: 404 not found")):
            result = GitHubReleaseBinaryMechanism(
                "missing/repo", "missing", sha256_pinned=True
            ).install()
        assert result.failed is True
        assert "404" in result.stderr

    def test_sha256_mismatch_raises_typed_error(self) -> None:
        """Per spec: SHA256 mismatch raises `Sha256MismatchError` with expected vs received."""
        with (
            patch(_SAFE_RUN_PATH, return_value=_ok_result()),
            patch(
                "ai_engineering.installer.mechanisms._verify_sha256",
                side_effect=Sha256MismatchError(
                    expected="aaaa1111", received="bbbb2222", path="/tmp/gitleaks"
                ),
            ),
            pytest.raises(Sha256MismatchError) as excinfo,
        ):
            GitHubReleaseBinaryMechanism(
                "gitleaks/gitleaks", "gitleaks", sha256_pinned=True
            ).install()
        # The error MUST surface both expected and received digests so users
        # can diff manually -- never silently fall through.
        msg = str(excinfo.value)
        assert "aaaa1111" in msg
        assert "bbbb2222" in msg


# ---------------------------------------------------------------------------
# 3. WingetMechanism
# ---------------------------------------------------------------------------


class TestWingetMechanism:
    """`WingetMechanism(package_id, scope='user')` -> winget install --scope user --id <id>."""

    def test_construction_with_valid_args(self) -> None:
        mech = WingetMechanism("gitleaks.gitleaks")
        assert mech.package_id == "gitleaks.gitleaks"
        assert mech.scope == "user"  # default per spec

    def test_construction_accepts_explicit_scope(self) -> None:
        mech = WingetMechanism("gitleaks.gitleaks", scope="user")
        assert mech.scope == "user"

    def test_install_invokes_safe_run_with_winget_argv(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            WingetMechanism("gitleaks.gitleaks").install()
        argv = _capture_argv(mock_run)
        assert argv[0] == "winget"
        assert "install" in argv
        assert "gitleaks.gitleaks" in argv
        # Must include user-scope flag pair per D-101-02.
        assert "--scope" in argv
        assert argv[argv.index("--scope") + 1] == "user"

    def test_install_returns_install_result(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = WingetMechanism("gitleaks.gitleaks").install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("winget: package not found")):
            result = WingetMechanism("does.not.exist").install()
        assert result.failed is True
        assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 4. ScoopMechanism
# ---------------------------------------------------------------------------


class TestScoopMechanism:
    """`ScoopMechanism(package)` -> `scoop install <package>`."""

    def test_construction_with_valid_args(self) -> None:
        mech = ScoopMechanism("gitleaks")
        assert mech.package == "gitleaks"

    def test_install_invokes_safe_run_with_scoop_argv(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            ScoopMechanism("gitleaks").install()
        argv = _capture_argv(mock_run)
        assert argv[0] == "scoop"
        assert "install" in argv
        assert "gitleaks" in argv

    def test_install_returns_install_result(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = ScoopMechanism("gitleaks").install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("scoop: bucket not found")):
            result = ScoopMechanism("missing").install()
        assert result.failed is True
        assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 5. UvToolMechanism
# ---------------------------------------------------------------------------


class TestUvToolMechanism:
    """`UvToolMechanism(package)` -> `uv tool install <package>` (user-global)."""

    def test_construction_with_valid_args(self) -> None:
        mech = UvToolMechanism("ruff")
        assert mech.package == "ruff"

    def test_install_invokes_safe_run_with_uv_tool_argv(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            UvToolMechanism("ruff").install()
        argv = _capture_argv(mock_run)
        assert argv[0] == "uv"
        assert argv[1] == "tool"
        assert argv[2] == "install"
        assert "ruff" in argv

    def test_install_returns_install_result(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = UvToolMechanism("ruff").install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("uv: package not found")):
            result = UvToolMechanism("nonexistent").install()
        assert result.failed is True
        assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 6. UvPipVenvMechanism
# ---------------------------------------------------------------------------


class TestUvPipVenvMechanism:
    """`UvPipVenvMechanism(package, venv)` -> uv pip install --python <venv>/bin/python <pkg>."""

    def test_construction_with_valid_args(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        mech = UvPipVenvMechanism("pytest", venv=venv)
        assert mech.package == "pytest"
        assert mech.venv == venv

    def test_install_invokes_safe_run_with_uv_pip_argv(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            UvPipVenvMechanism("pytest", venv=venv).install()
        argv = _capture_argv(mock_run)
        assert argv[0] == "uv"
        assert "pip" in argv
        assert "install" in argv
        assert "--python" in argv
        # The python interpreter MUST be inside the supplied venv.
        py_idx = argv.index("--python") + 1
        assert str(venv) in argv[py_idx]
        assert "pytest" in argv

    def test_install_returns_install_result(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = UvPipVenvMechanism("pytest", venv=venv).install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self, tmp_path: Path) -> None:
        venv = tmp_path / ".venv"
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("uv: venv missing")):
            result = UvPipVenvMechanism("pytest", venv=venv).install()
        assert result.failed is True
        assert "missing" in result.stderr


# ---------------------------------------------------------------------------
# 7. NpmDevMechanism
# ---------------------------------------------------------------------------


class TestNpmDevMechanism:
    """`NpmDevMechanism(package)` -> `npm install --save-dev <package>` (project-local)."""

    def test_construction_with_valid_args(self) -> None:
        mech = NpmDevMechanism("prettier")
        assert mech.package == "prettier"

    def test_install_invokes_safe_run_with_npm_argv(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            NpmDevMechanism("prettier").install()
        argv = _capture_argv(mock_run)
        assert argv[0] == "npm"
        assert "install" in argv
        assert "--save-dev" in argv
        assert "prettier" in argv
        # MUST NOT be a global install (forbidden per D-101-02).
        assert "-g" not in argv
        assert "--global" not in argv

    def test_install_returns_install_result(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = NpmDevMechanism("prettier").install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("npm: ENOENT package.json")):
            result = NpmDevMechanism("prettier").install()
        assert result.failed is True
        assert "ENOENT" in result.stderr


# ---------------------------------------------------------------------------
# 8. DotnetToolMechanism
# ---------------------------------------------------------------------------


class TestDotnetToolMechanism:
    """`DotnetToolMechanism(package)` -> `dotnet tool install --global <package>` (user-scope)."""

    def test_construction_with_valid_args(self) -> None:
        mech = DotnetToolMechanism("dotnet-format")
        assert mech.package == "dotnet-format"

    def test_install_invokes_safe_run_with_dotnet_argv(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            DotnetToolMechanism("dotnet-format").install()
        argv = _capture_argv(mock_run)
        assert argv[0] == "dotnet"
        assert argv[1] == "tool"
        assert argv[2] == "install"
        assert "--global" in argv  # `--global` is user-scope for dotnet despite the name
        assert "dotnet-format" in argv

    def test_install_returns_install_result(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = DotnetToolMechanism("dotnet-format").install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("dotnet: NU1101 not found")):
            result = DotnetToolMechanism("nonexistent").install()
        assert result.failed is True
        assert "NU1101" in result.stderr


# ---------------------------------------------------------------------------
# 9. CargoInstallMechanism
# ---------------------------------------------------------------------------


class TestCargoInstallMechanism:
    """`CargoInstallMechanism(crate)` -> `cargo install <crate>`."""

    def test_construction_with_valid_args(self) -> None:
        mech = CargoInstallMechanism("cargo-audit")
        assert mech.crate == "cargo-audit"

    def test_install_invokes_safe_run_with_cargo_argv(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            CargoInstallMechanism("cargo-audit").install()
        argv = _capture_argv(mock_run)
        assert argv[0] == "cargo"
        assert "install" in argv
        assert "cargo-audit" in argv

    def test_install_returns_install_result(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = CargoInstallMechanism("cargo-audit").install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("cargo: crate not found")):
            result = CargoInstallMechanism("missing-crate").install()
        assert result.failed is True
        assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 10. GoInstallMechanism
# ---------------------------------------------------------------------------


class TestGoInstallMechanism:
    """`GoInstallMechanism(import_path)` -> `go install <path>`."""

    def test_construction_with_valid_args(self) -> None:
        mech = GoInstallMechanism("honnef.co/go/tools/cmd/staticcheck@latest")
        assert mech.import_path == "honnef.co/go/tools/cmd/staticcheck@latest"

    def test_install_invokes_safe_run_with_go_argv(self) -> None:
        path = "honnef.co/go/tools/cmd/staticcheck@latest"
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            GoInstallMechanism(path).install()
        argv = _capture_argv(mock_run)
        assert argv[0] == "go"
        assert "install" in argv
        assert path in argv

    def test_install_returns_install_result(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = GoInstallMechanism("example.com/foo@latest").install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("go: module not found")):
            result = GoInstallMechanism("missing/module@latest").install()
        assert result.failed is True
        assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 11. ComposerGlobalMechanism
# ---------------------------------------------------------------------------


class TestComposerGlobalMechanism:
    """`ComposerGlobalMechanism(package)` -> `composer global require <package>` (PHP)."""

    def test_construction_with_valid_args(self) -> None:
        mech = ComposerGlobalMechanism("phpstan/phpstan")
        assert mech.package == "phpstan/phpstan"

    def test_install_invokes_safe_run_with_composer_argv(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            ComposerGlobalMechanism("phpstan/phpstan").install()
        argv = _capture_argv(mock_run)
        assert argv[0] == "composer"
        assert "global" in argv
        assert "require" in argv
        assert "phpstan/phpstan" in argv

    def test_install_returns_install_result(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = ComposerGlobalMechanism("phpstan/phpstan").install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("composer: package not found")):
            result = ComposerGlobalMechanism("missing/pkg").install()
        assert result.failed is True
        assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# 12. SdkmanMechanism
# ---------------------------------------------------------------------------


class TestSdkmanMechanism:
    """`SdkmanMechanism(candidate, version)` -> SDKMAN install (JDK helper for java/kotlin)."""

    def test_construction_with_valid_args(self) -> None:
        mech = SdkmanMechanism("java", "21.0.2-tem")
        assert mech.candidate == "java"
        assert mech.version == "21.0.2-tem"

    def test_install_invokes_safe_run_with_sdk_argv(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()) as mock_run:
            SdkmanMechanism("java", "21.0.2-tem").install()
        argv = _capture_argv(mock_run)
        # SDKMAN's CLI is `sdk`; the install verb must appear and both
        # candidate and version values must be present.
        assert argv[0] == "sdk"
        assert "install" in argv
        assert "java" in argv
        assert "21.0.2-tem" in argv

    def test_install_returns_install_result(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_ok_result()):
            result = SdkmanMechanism("java", "21.0.2-tem").install()
        assert isinstance(result, InstallResult)
        assert result.failed is False

    def test_install_failure_captures_stderr(self) -> None:
        with patch(_SAFE_RUN_PATH, return_value=_fail_result("sdk: candidate not found")):
            result = SdkmanMechanism("java", "99.0.0-bogus").install()
        assert result.failed is True
        assert "not found" in result.stderr


# ---------------------------------------------------------------------------
# Parametric coverage: all 12 mechanisms exposed and callable
# ---------------------------------------------------------------------------


_ALL_MECHANISM_CLASSES: tuple[type, ...] = (
    BrewMechanism,
    GitHubReleaseBinaryMechanism,
    WingetMechanism,
    ScoopMechanism,
    UvToolMechanism,
    UvPipVenvMechanism,
    NpmDevMechanism,
    DotnetToolMechanism,
    CargoInstallMechanism,
    GoInstallMechanism,
    ComposerGlobalMechanism,
    SdkmanMechanism,
)


def test_all_12_mechanisms_have_install_method() -> None:
    """Every one of the 12 mechanism classes is exposed AND has a callable `install`."""
    assert len(_ALL_MECHANISM_CLASSES) == 12, (
        f"expected 12 mechanism classes, got {len(_ALL_MECHANISM_CLASSES)}"
    )
    for cls in _ALL_MECHANISM_CLASSES:
        install = getattr(cls, "install", None)
        assert install is not None, f"{cls.__name__} is missing `install`"
        assert callable(install), f"{cls.__name__}.install is not callable"
