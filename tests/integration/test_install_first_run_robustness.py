"""End-to-end first-install robustness validation (spec-109).

The user complaint that triggered spec-109: ``ai-eng install`` always failed
the first time on a clean project, requiring ``ai-eng doctor`` then
``ai-eng doctor --fix``. These tests prove the new behaviour:

* HooksPhase still runs even when ToolsPhase recorded a non-critical failure.
* The pipeline summary lists the non-critical failure but does NOT stop.
* Auto-remediation closes the gap so the user sees EXIT 0 + a clean report.
* ``--no-auto-remediate`` still surfaces EXIT 80 for CI gating.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from ai_engineering.cli_commands._exit_codes import EXIT_TOOLS_FAILED
from ai_engineering.cli_factory import create_app

runner = CliRunner()


@pytest.fixture
def app() -> object:
    return create_app()


@pytest.fixture
def project_dir(tmp_path: Path) -> Path:
    project = tmp_path / "probando"
    project.mkdir()
    (project / "pyproject.toml").write_text(
        '[project]\nname = "probando"\nversion = "0.0.1"\n',
        encoding="utf-8",
    )
    return project


class TestHooksRunsAfterToolsFailure:
    """Regression: HooksPhase must still run when ToolsPhase fails."""

    def test_hooks_installed_despite_tool_failure(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """spec-109 D-109-02 + D-109-03: ToolsPhase non-critical -> HooksPhase still runs."""
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")
        # Auto-remediate disabled so we observe the pipeline state directly.
        # We are NOT measuring the success of remediation here; only that
        # HooksPhase produced its files even with a tool failure upstream.

        result = runner.invoke(
            app,
            [
                "install",
                str(project_dir),
                "--stack",
                "python",
                "--no-auto-remediate",
            ],
        )

        # Pipeline ran end-to-end; user sees EXIT 80 because remediate was off.
        assert result.exit_code == EXIT_TOOLS_FAILED, result.output

        # And critically -- the hooks ARE on disk.
        for hook in ("pre-commit", "commit-msg", "pre-push"):
            assert (project_dir / ".git" / "hooks" / hook).is_file(), (
                f"hook {hook!r} missing under .git/hooks/ -- "
                "HooksPhase did not run after ToolsPhase failed"
            )


class TestAutoRemediateClosesTheLoop:
    """spec-109 D-109-05: install + auto-remediate produces EXIT 0 + healthy state."""

    def test_install_remediates_to_exit_zero(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Tool failure that is auto-remediable -> install exits 0.

        spec-113 G-12: doctor's fix path now reaches every WARN-fixable tool
        (not only the tool the install pipeline simulated as failed). On
        runners without brew (CI Linux/Windows) the gitleaks/jq fallback
        attempts a real GitHub-release download whose asset name is not
        ``gitleaks`` (it is e.g. ``gitleaks_8.21.3_linux_x64.tar.gz``); the
        wildcard SIMULATE_INSTALL_OK keeps the test boundary at the
        mechanism dispatcher rather than the real network. spec-113's
        honest auto-remediate (G-5) requires applied != [] for success, so
        every fix-attempted tool must short-circuit to synthetic OK.
        """
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_INSTALL_OK", "*")

        result = runner.invoke(
            app,
            ["install", str(project_dir), "--stack", "python"],
        )

        assert result.exit_code == 0, result.output
        # Hooks present.
        for hook in ("pre-commit", "commit-msg", "pre-push"):
            assert (project_dir / ".git" / "hooks" / hook).is_file()


class TestRenderBeforeExit:
    """spec-109 D-109-04: pipeline steps render BEFORE the exit raise.

    Pre-spec-109 the CLI emitted "see warnings above" then exited before
    rendering the steps -- so the user saw the error with no warnings above.
    """

    def test_pipeline_step_lines_visible_when_remediation_off(
        self,
        project_dir: Path,
        app: object,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("AIENG_TEST", "1")
        monkeypatch.setenv("AIENG_TEST_SIMULATE_FAIL", "ruff")

        result = runner.invoke(
            app,
            [
                "install",
                str(project_dir),
                "--stack",
                "python",
                "--no-auto-remediate",
            ],
        )

        # We are checking the COMBINED stdout+stderr stream the user sees.
        combined = result.output

        # The user must SEE the per-phase result -- "Tool verification" is the
        # canonical label for the tools phase rendered by _render_pipeline_steps.
        assert "Tool verification" in combined, (
            "Tool verification step was not rendered to the user (spec-109 D-109-04 regression)"
        )
        # And the failed-phase explanation surfaces explicitly.
        assert (
            "non-critical" in combined.lower()
            or "auto-remediation disabled" in combined.lower()
            or "doctor --fix" in combined.lower()
        ), "Expected the user-facing message to point at remediation; got:\n" + combined
