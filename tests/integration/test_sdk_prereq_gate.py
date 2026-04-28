"""Integration tests for spec-101 SDK prereq gate (T-2.7 RED + T-2.8 GREEN).

Spec D-101-14 reserves a NEW phase BEFORE the tools phase that probes the
9 SDK-required stacks (java, kotlin, swift, dart, csharp, go, rust, php, cpp)
via :func:`ai_engineering.prereqs.sdk.probe_sdk` and surfaces EXIT 81 when
any declared stack's SDK is absent or below ``min_version``.

The contract enforced by this file:

1. **EXIT 81 per stack**: a project declaring a single SDK-required stack
   with no SDK present yields EXIT 81. The error message MUST name the
   stack, the missing SDK, and the install link from
   :data:`ai_engineering.state.manifest._CANONICAL_SDK_PREREQS`.
2. **EXIT 81 includes ``<probe>`` cmd**: the message MUST suggest the exact
   probe command the user runs after manual install (per spec D-101-14).
3. **No EXIT 81 when SDK present**: when the probe returns ``present=True``
   and ``meets_min_version=True``, the install proceeds to the tools phase.
4. **D-101-13 carve-out**: a stack whose ``platform_unsupported_stack``
   covers the current OS (e.g. swift on linux) MUST NOT trigger an SDK
   probe -- the stack is already filtered before tools install runs.

Implementation hooks the tests rely on:

* ``ai_engineering.installer.phases.sdk_prereqs.check_sdk_prereqs`` -- the
  function the CLI calls before the tools phase. Raises
  :class:`PrereqMissing` on any failure.
* The CLI ``install_cmd`` in ``cli_commands/core.py`` catches
  :class:`PrereqMissing` and emits :data:`EXIT_PREREQS_MISSING`.

Tests rely on ``probe_sdk`` being patched -- the production probe spawns
real subprocesses, which is non-deterministic in CI. Patching the dispatch
layer keeps the tests hermetic.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_commands._exit_codes import EXIT_PREREQS_MISSING
from ai_engineering.cli_factory import create_app
from ai_engineering.prereqs.sdk import ProbeResult

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass


runner = CliRunner()


# Canonical install-link map from spec D-101-14. Mirrors
# ``state.manifest._CANONICAL_SDK_PREREQS`` so the test fails loud if either
# side drifts. Each entry: (stack, install_link, probe_argv_token).
_SDK_INSTALL_LINKS: dict[str, tuple[str, str]] = {
    "java": ("https://adoptium.net/", "java -version"),
    "kotlin": ("https://adoptium.net/", "java -version"),
    "go": ("https://go.dev/dl/", "go version"),
    "rust": ("https://rustup.rs/", "rustc --version"),
    "csharp": ("https://dotnet.microsoft.com/download", "dotnet --version"),
    "php": ("https://www.php.net/downloads", "php --version"),
    "dart": ("https://dart.dev/get-dart", "dart --version"),
    "swift": ("https://www.swift.org/install/", "swift --version"),
    "cpp": ("https://llvm.org/builds/", "clang --version"),
}


# Fixture path -- canonical 15-key required_tools manifest.
FIXTURE_PATH = (
    Path(__file__).resolve().parent.parent
    / "fixtures"
    / "test_manifests"
    / "spec101_required_tools.yml"
)


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Stage a temp project root with a spec-101 manifest fixture and git init."""
    subprocess.run(
        ["git", "init", "-b", "main", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    return tmp_path


@pytest.fixture()
def app() -> object:
    return create_app()


def _stub_probe(
    *,
    present_for: set[str] | None = None,
) -> Callable[[str], ProbeResult]:
    """Build a stub ``probe_sdk`` that returns absent for stacks not in the set.

    Stacks listed in ``present_for`` resolve to ``ProbeResult(present=True,
    meets_min_version=True)``; all others resolve to absent.
    """
    present_for = present_for or set()

    def _stub(stack: str) -> ProbeResult:
        if stack in present_for:
            return ProbeResult(
                stack=stack,
                status="ok",
                present=True,
                version="999.0.0",
                meets_min_version=True,
                error_message=None,
            )
        return ProbeResult(
            stack=stack,
            status="absent",
            present=False,
            version=None,
            meets_min_version=False,
            error_message=f"{stack} SDK not found on PATH",
        )

    return _stub


# ---------------------------------------------------------------------------
# Layer 1 -- per-stack EXIT 81 with actionable install link.
# ---------------------------------------------------------------------------


class TestPerStackPrereqGate:
    """Each declared SDK-required stack with absent SDK -> EXIT 81 + link."""

    @pytest.mark.parametrize(
        "stack",
        [
            pytest.param("java", id="java"),
            pytest.param("kotlin", id="kotlin"),
            pytest.param("go", id="go"),
            pytest.param("rust", id="rust"),
            pytest.param("csharp", id="csharp"),
            pytest.param("php", id="php"),
            pytest.param("dart", id="dart"),
            pytest.param("cpp", id="cpp"),
        ],
    )
    def test_missing_sdk_exits_eighty_one(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
        stack: str,
    ) -> None:
        """A project declaring ``stack`` with absent SDK -> exit 81."""
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setattr(
            "ai_engineering.installer.phases.sdk_prereqs.probe_sdk",
            _stub_probe(present_for=set()),
        )

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", stack],
        )

        assert result.exit_code == EXIT_PREREQS_MISSING, (
            f"Expected EXIT 81 for {stack} with absent SDK; got {result.exit_code}\n{result.output}"
        )

    @pytest.mark.parametrize(
        "stack",
        [
            pytest.param("java", id="java"),
            pytest.param("kotlin", id="kotlin"),
            pytest.param("go", id="go"),
            pytest.param("rust", id="rust"),
            pytest.param("csharp", id="csharp"),
            pytest.param("php", id="php"),
            pytest.param("dart", id="dart"),
            pytest.param("cpp", id="cpp"),
        ],
    )
    def test_missing_sdk_message_includes_install_link(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
        stack: str,
    ) -> None:
        """The EXIT 81 message MUST carry the spec-D-101-14 install link."""
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setattr(
            "ai_engineering.installer.phases.sdk_prereqs.probe_sdk",
            _stub_probe(present_for=set()),
        )

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", stack],
        )

        link, _probe = _SDK_INSTALL_LINKS[stack]
        assert link in result.output, (
            f"Expected install link {link!r} in output for {stack}; got:\n{result.output}"
        )

    @pytest.mark.parametrize(
        "stack",
        [
            pytest.param("java", id="java"),
            pytest.param("kotlin", id="kotlin"),
            pytest.param("go", id="go"),
            pytest.param("rust", id="rust"),
            pytest.param("csharp", id="csharp"),
            pytest.param("php", id="php"),
            pytest.param("dart", id="dart"),
            pytest.param("cpp", id="cpp"),
        ],
    )
    def test_missing_sdk_message_includes_probe_command(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
        stack: str,
    ) -> None:
        """Per spec D-101-14, the message must name the verify command."""
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setattr(
            "ai_engineering.installer.phases.sdk_prereqs.probe_sdk",
            _stub_probe(present_for=set()),
        )

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", stack],
        )

        _link, probe = _SDK_INSTALL_LINKS[stack]
        assert probe in result.output, (
            f"Expected probe cmd {probe!r} in output for {stack}; got:\n{result.output}"
        )


# ---------------------------------------------------------------------------
# Layer 2 -- swift-on-darwin gating (D-101-13 + D-101-14 intersection).
# ---------------------------------------------------------------------------


class TestSwiftDarwinGate:
    """``swift`` triggers the SDK probe ONLY on darwin; linux/windows get the
    stack-level skip carve-out and bypass the SDK probe entirely."""

    def test_missing_swift_on_darwin_exits_eighty_one(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """darwin without swift toolchain -> EXIT 81."""
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setattr("platform.system", lambda: "Darwin")
        monkeypatch.setattr(
            "ai_engineering.installer.phases.sdk_prereqs.probe_sdk",
            _stub_probe(present_for=set()),
        )

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", "swift"],
        )

        assert result.exit_code == EXIT_PREREQS_MISSING, (
            f"Expected EXIT 81 for swift on darwin without toolchain; "
            f"got {result.exit_code}\n{result.output}"
        )
        assert "https://www.swift.org/install/" in result.output, (
            f"Expected swift install link in output; got:\n{result.output}"
        )

    @pytest.mark.parametrize(
        "current_os, system_name",
        [
            pytest.param("linux", "Linux", id="linux"),
            pytest.param("windows", "Windows", id="windows"),
        ],
    )
    def test_swift_on_unsupported_os_skips_sdk_probe(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
        current_os: str,
        system_name: str,
    ) -> None:
        """``platform_unsupported_stack`` covers OS -> no SDK probe -> no EXIT 81.

        The install must NOT exit 81 for the swift stack on linux/windows
        because D-101-13 carves out the stack entirely. Whether tools-phase
        eventually exits 0 depends on baseline-tool install which we don't
        constrain here -- we only assert the SDK gate did NOT short-circuit.
        """
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setattr("platform.system", lambda: system_name)

        # Track whether probe_sdk was invoked for swift -- per the carve-out
        # the gate must not call probe_sdk for stacks whose
        # platform_unsupported_stack covers the current OS.
        invoked: list[str] = []

        def _spy(stack: str) -> ProbeResult:
            invoked.append(stack)
            return ProbeResult(
                stack=stack,
                status="absent",
                present=False,
                version=None,
                meets_min_version=False,
                error_message=f"{stack} SDK not found",
            )

        monkeypatch.setattr(
            "ai_engineering.installer.phases.sdk_prereqs.probe_sdk",
            _spy,
        )

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", "swift"],
        )

        # Either exit 0 (happy install) or EXIT 80 (tools failure on the
        # baseline tools), but NEVER EXIT 81.
        assert result.exit_code != EXIT_PREREQS_MISSING, (
            f"swift on {current_os} must NOT trigger SDK gate (carve-out per "
            f"D-101-13); got exit {result.exit_code}\n{result.output}"
        )
        assert "swift" not in invoked, (
            f"probe_sdk was invoked for swift on {current_os}; the SDK gate "
            "must skip stacks whose platform_unsupported_stack covers the "
            f"current OS. invocations: {invoked!r}"
        )


# ---------------------------------------------------------------------------
# Layer 3 -- happy path: SDK present -> install proceeds.
# ---------------------------------------------------------------------------


class TestSdkPresentHappyPath:
    """When all declared SDKs are present, the gate does not block."""

    @pytest.mark.parametrize(
        "stack",
        [
            pytest.param("java", id="java"),
            pytest.param("go", id="go"),
            pytest.param("rust", id="rust"),
            pytest.param("csharp", id="csharp"),
            pytest.param("php", id="php"),
            pytest.param("dart", id="dart"),
            pytest.param("cpp", id="cpp"),
            pytest.param("kotlin", id="kotlin"),
        ],
    )
    def test_sdk_present_does_not_exit_eighty_one(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
        stack: str,
    ) -> None:
        """SDK probe returns present -> exit code is NOT 81."""
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setattr(
            "ai_engineering.installer.phases.sdk_prereqs.probe_sdk",
            _stub_probe(present_for={stack}),
        )

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", stack],
        )

        assert result.exit_code != EXIT_PREREQS_MISSING, (
            f"SDK gate must NOT exit 81 when {stack} probe reports present; "
            f"got exit {result.exit_code}\n{result.output}"
        )


# ---------------------------------------------------------------------------
# Layer 4 -- non-SDK stacks (python, typescript, etc.) bypass the gate.
# ---------------------------------------------------------------------------


class TestNonSdkStacksBypass:
    """Non-SDK stacks (python, typescript, javascript, sql, bash) must not
    trigger any SDK probe -- the canonical 9-set gates the gate."""

    def test_python_stack_does_not_invoke_sdk_probe(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """python stack -> probe_sdk is never called."""
        monkeypatch.setenv("AIENG_TEST", "1")
        invoked: list[str] = []

        def _spy(stack: str) -> ProbeResult:
            invoked.append(stack)
            return ProbeResult(
                stack=stack,
                status="absent",
                present=False,
                version=None,
                meets_min_version=False,
            )

        monkeypatch.setattr(
            "ai_engineering.installer.phases.sdk_prereqs.probe_sdk",
            _spy,
        )

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", "python"],
        )

        assert invoked == [], (
            f"probe_sdk must NOT be called for non-SDK stacks; invocations: {invoked!r}"
        )
        assert result.exit_code != EXIT_PREREQS_MISSING, (
            f"python stack must not produce EXIT 81; got {result.exit_code}\n{result.output}"
        )
