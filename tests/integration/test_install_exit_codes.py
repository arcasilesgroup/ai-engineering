"""Integration tests for spec-101 install EXIT 80 / EXIT 81 (T-2.3 RED + T-2.4 GREEN).

Spec-101 D-101-11 reserves two exit codes outside the sysexits.h 64-78 range:

* **EXIT 81** -- ``prereq missing`` (uv absent, uv version out of range, or any
  declared SDK prereq missing).
* **EXIT 80** -- ``tool install failed`` (any required tool's mechanism
  ``install()`` returned ``failed=True``).

Strict precedence: missing prereqs short-circuit BEFORE the tools phase runs.
A project with both a missing prereq AND a broken tool surface returns 81,
not 80.

These tests verify the ``ai-eng install`` CLI surface end-to-end:

* EXIT 0 happy path (all prereqs + tools succeed).
* EXIT 80 when a tool install fails.
* EXIT 81 when uv is missing.
* Precedence: missing-uv beats failing-tool.

The tests rely on two test-only env hooks:

* ``AIENG_TEST=1`` -- enables deterministic install-pipeline mocking. Without
  this hook, ``ai-eng install`` exercises the production install path.
* ``AIENG_TEST_SIMULATE_FAIL=<tool>`` -- forces the named tool's mechanism
  ``install()`` to return ``failed=True``.

The exit constants live in ``ai_engineering.cli_commands._exit_codes`` so test
imports remain stable across refactors.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_commands._exit_codes import (
    EXIT_PREREQS_MISSING,
    EXIT_TOOLS_FAILED,
)
from ai_engineering.cli_factory import create_app

if TYPE_CHECKING:  # pragma: no cover - typing only
    pass


runner = CliRunner()


@pytest.fixture()
def app() -> object:
    """Create a fresh CLI app instance for each test."""
    return create_app()


@pytest.fixture()
def project_dir(tmp_path: Path) -> Path:
    """Create a minimal git repo so install validation passes."""
    subprocess.run(
        ["git", "init", "-b", "main", str(tmp_path)],
        check=True,
        capture_output=True,
    )
    return tmp_path


# ---------------------------------------------------------------------------
# EXIT-code constants must be reserved values per spec-101 D-101-11.
# ---------------------------------------------------------------------------


class TestExitCodeConstants:
    """The two reserved exit codes are stable, importable constants."""

    def test_exit_tools_failed_is_80(self) -> None:
        assert EXIT_TOOLS_FAILED == 80

    def test_exit_prereqs_missing_is_81(self) -> None:
        assert EXIT_PREREQS_MISSING == 81

    def test_exit_codes_outside_sysexits_range(self) -> None:
        """Per D-101-11, both codes must sit outside the sysexits 64-78 band."""
        assert EXIT_TOOLS_FAILED > 78
        assert EXIT_PREREQS_MISSING > 78


# ---------------------------------------------------------------------------
# EXIT 0 -- happy path with prereqs + tools succeeding.
# ---------------------------------------------------------------------------


class TestExitZeroHappyPath:
    """All prereqs + tools succeeding yields EXIT 0."""

    def test_install_with_valid_uv_and_tools_exits_zero(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``ai-eng install`` with mocked happy paths -> exit 0.

        Wave 27 (Test-1): hermetic seam. Without
        ``AIENG_TEST_SIMULATE_INSTALL_OK="*"`` this test ran the real
        install pipeline (~5.65s) -- network-dependent, slow, and a
        false-negative source on offline runners. Setting both env vars
        forces every required-tool mechanism into the synthetic-success
        path so the test stays under 1s and never spawns network calls.
        """
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "*")

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", "python"],
        )
        assert result.exit_code == 0, f"Expected exit 0; got {result.exit_code}\n{result.output}"


# ---------------------------------------------------------------------------
# EXIT 80 -- tool install failure path.
# ---------------------------------------------------------------------------


class TestExitEightyToolFailure:
    """A failed tool install surfaces EXIT 80 -- but only when auto-remediation can't fix it.

    spec-109 D-109-05 introduced post-pipeline auto-remediation: a tool whose
    install mechanism fails will still get a second-pass repair via the doctor
    fix path. To exercise the original spec-101 fail-on-first-attempt EXIT 80
    semantics this test runs with ``--no-auto-remediate`` (R-109-01) so the
    second pass is suppressed.
    """

    def test_simulated_tool_install_failure_exits_eighty_no_remediate(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``AIENG_TEST_SIMULATE_FAIL=ruff`` + ``--no-auto-remediate`` -> exit 80."""
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", "python", "--no-auto-remediate"],
        )
        assert result.exit_code == EXIT_TOOLS_FAILED, (
            f"Expected EXIT 80 (tools failed); got {result.exit_code}\n{result.output}"
        )

    def test_simulated_tool_install_failure_auto_remediates_to_zero(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """spec-109: simulated tool failure that auto-remediates exits 0.

        Doctor's fix path also resolves to a synthetic install; this proves
        that auto-remediation closes the loop on the same fault that EXIT 80
        used to surface.
        """
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")
        # Sister hook: doctor fix attempts via TOOL_REGISTRY mechanism; under
        # AIENG_TEST=1 the registry mechanism honours AIENG_TEST_SIMULATE_INSTALL_OK
        # to fake a successful install for the named tool.
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "ruff")

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", "python"],
        )
        # spec-109 D-109-06: success post-auto-remediate -> EXIT 0.
        assert result.exit_code == 0, (
            f"Expected EXIT 0 (auto-remediated); got {result.exit_code}\n{result.output}"
        )


# ---------------------------------------------------------------------------
# EXIT 81 -- prereq missing path.
# ---------------------------------------------------------------------------


class TestExitEightyOnePrereqMissing:
    """Missing uv prereq surfaces EXIT 81."""

    def test_uv_absent_exits_eighty_one(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``AIENG_TEST_SIMULATE_PREREQ_MISSING=uv`` -> exit 81."""
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_PREREQ_MISSING", "uv")

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", "python"],
        )
        assert result.exit_code == EXIT_PREREQS_MISSING, (
            f"Expected EXIT 81 (prereqs missing); got {result.exit_code}\n{result.output}"
        )


# ---------------------------------------------------------------------------
# Precedence: prereq missing beats tool failure (81 wins over 80).
# ---------------------------------------------------------------------------


class TestPrereqPrecedenceBeatsTools:
    """When both prereqs are missing AND tools would fail, EXIT 81 wins."""

    def test_missing_prereq_short_circuits_before_tools(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Both fail-flags set -> exit 81, never 80 (tools phase never runs).

        ``--no-auto-remediate`` is set so a transient prereq miss does not turn
        into an EXIT 0 via remediation -- the precedence test must still see
        the prereq exit code.
        """
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_PREREQ_MISSING", "uv")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", "python", "--no-auto-remediate"],
        )
        assert result.exit_code == EXIT_PREREQS_MISSING, (
            f"Expected EXIT 81 (prereq precedence); got {result.exit_code}\n{result.output}"
        )
