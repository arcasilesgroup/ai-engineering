"""spec-101 T-2.27 RED + T-2.28 GREEN -- typescript no-op install handling.

Closes the D-101-01 carve-out for ``scope: project_local`` tools: when a
declared stack contains ONLY project_local tools, the installer phase is
essentially a no-op for that stack -- the framework does NOT install
the tools (npm/composer/maven do). The phase still:

* Records each project_local tool with state
  :class:`ToolInstallState.NOT_INSTALLED_PROJECT_LOCAL` so doctor and the
  state file reflect that the framework intentionally skipped install.
* Emits an info-level warning naming the stack and the language-native
  install command (``npm install`` for typescript, ``composer install``
  for php, etc.).
* For node-based stacks (typescript, javascript): verifies ``package.json``
  exists at the project root. If missing -> EXIT 80 with a clear
  ``npm init -y`` remediation message (R-3 pattern).

Two test classes:

* :class:`TestTypeScriptOnlyNoOpInstall` -- typescript stack with all 4
  project_local tools (prettier, eslint, tsc, vitest) and ``package.json``
  present.
* :class:`TestTypeScriptMissingPackageJsonExits80` -- typescript stack
  without ``package.json``: phase reports the missing prereq, exit 80.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from ai_engineering.installer.phases import (
    InstallContext,
    InstallMode,
)
from ai_engineering.state.manifest import LoadResult
from ai_engineering.state.models import (
    InstallState,
    ToolInstallState,
    ToolScope,
    ToolSpec,
)

if TYPE_CHECKING:  # pragma: no cover - typing-only
    pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _typescript_only_load_result() -> LoadResult:
    """LoadResult for a typescript-only project: 4 project_local tools."""
    return LoadResult(
        tools=[
            ToolSpec(name="prettier", scope=ToolScope.PROJECT_LOCAL),
            ToolSpec(name="eslint", scope=ToolScope.PROJECT_LOCAL),
            ToolSpec(name="tsc", scope=ToolScope.PROJECT_LOCAL),
            ToolSpec(name="vitest", scope=ToolScope.PROJECT_LOCAL),
        ],
        skipped_stacks=[],
    )


def _build_typescript_context(target: Path) -> InstallContext:
    return InstallContext(
        target=target,
        mode=InstallMode.INSTALL,
        providers=["claude_code"],
        vcs_provider="github",
        stacks=["typescript"],
        ides=["terminal"],
        existing_state=InstallState(),
    )


# ---------------------------------------------------------------------------
# T-2.27: typescript-only project with package.json present
# ---------------------------------------------------------------------------


class TestTypeScriptOnlyNoOpInstall:
    """All 4 typescript project_local tools recorded as not_installed_project_local."""

    def _seed_typescript_project(self, project_root: Path) -> None:
        """Create the .ai-engineering directory + package.json."""
        (project_root / ".ai-engineering" / "state").mkdir(parents=True)
        (project_root / "package.json").write_text(
            '{"name":"demo","version":"1.0.0"}',
            encoding="utf-8",
        )

    def test_all_project_local_tools_recorded_as_not_installed_project_local(
        self,
        tmp_path: Path,
    ) -> None:
        """Each of prettier/eslint/tsc/vitest -> state ``NOT_INSTALLED_PROJECT_LOCAL``."""
        from ai_engineering.installer.phases.tools import ToolsPhase

        self._seed_typescript_project(tmp_path)
        context = _build_typescript_context(tmp_path)

        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_typescript_only_load_result(),
        ):
            phase = ToolsPhase()
            plan = phase.plan(context)
            result = phase.execute(plan, context)

        records = context.existing_state.required_tools_state
        for tool_name in ("prettier", "eslint", "tsc", "vitest"):
            assert tool_name in records, (
                f"expected {tool_name} to have a state record, got {list(records.keys())}"
            )
            assert records[tool_name].state == ToolInstallState.NOT_INSTALLED_PROJECT_LOCAL, (
                f"expected {tool_name} state=NOT_INSTALLED_PROJECT_LOCAL, "
                f"got {records[tool_name].state}"
            )

        # Phase result must NOT have any failures -- the tools are deliberately
        # skipped, so EXIT 80 is NOT triggered.
        assert not result.failed, f"unexpected failures: {result.failed}"

    def test_emits_info_log_naming_stack_and_install_command(
        self,
        tmp_path: Path,
    ) -> None:
        """An info-level warning names the stack AND ``npm install`` command."""
        from ai_engineering.installer.phases.tools import ToolsPhase

        self._seed_typescript_project(tmp_path)
        context = _build_typescript_context(tmp_path)

        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_typescript_only_load_result(),
        ):
            phase = ToolsPhase()
            plan = phase.plan(context)
            result = phase.execute(plan, context)

        # Look for the info-level message in result.warnings (the channel
        # the phase already uses for non-fatal informational lines).
        joined = " | ".join(result.warnings).lower()
        assert "typescript" in joined or "project-local" in joined or "project_local" in joined, (
            f"expected typescript/project-local mention in warnings, got: {result.warnings}"
        )
        assert "npm install" in joined, (
            f"expected 'npm install' remediation in warnings, got: {result.warnings}"
        )

    def test_phase_exits_clean_when_all_tools_are_project_local(
        self,
        tmp_path: Path,
    ) -> None:
        """No tools to install + package.json exists -> phase verdict passes."""
        from ai_engineering.installer.phases.tools import ToolsPhase

        self._seed_typescript_project(tmp_path)
        context = _build_typescript_context(tmp_path)

        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_typescript_only_load_result(),
        ):
            phase = ToolsPhase()
            plan = phase.plan(context)
            result = phase.execute(plan, context)
            verdict = phase.verify(result, context)

        assert verdict.passed is True, (
            f"verdict should pass for project_local-only stack: {verdict.errors}"
        )


# ---------------------------------------------------------------------------
# T-2.27: typescript stack WITHOUT package.json -> EXIT 80
# ---------------------------------------------------------------------------


class TestTypeScriptMissingPackageJsonExits80:
    """Missing package.json on a typescript-only project -> EXIT 80 + remediation."""

    def test_missing_package_json_records_failure(self, tmp_path: Path) -> None:
        """No ``package.json`` in cwd -> phase records a failure."""
        from ai_engineering.installer.phases.tools import ToolsPhase

        # State directory present, but NO package.json.
        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        context = _build_typescript_context(tmp_path)

        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_typescript_only_load_result(),
        ):
            phase = ToolsPhase()
            plan = phase.plan(context)
            result = phase.execute(plan, context)

        # Some failure entry references the missing package.json prereq.
        joined = " | ".join(result.failed).lower()
        assert "package.json" in joined or "package-json" in joined, (
            f"expected package.json failure entry, got: {result.failed}"
        )

    def test_missing_package_json_remediation_in_warnings(
        self,
        tmp_path: Path,
    ) -> None:
        """The warnings name ``npm init -y`` so the user can recover."""
        from ai_engineering.installer.phases.tools import ToolsPhase

        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        context = _build_typescript_context(tmp_path)

        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_typescript_only_load_result(),
        ):
            phase = ToolsPhase()
            plan = phase.plan(context)
            result = phase.execute(plan, context)

        joined = " | ".join(result.warnings).lower()
        assert "npm init -y" in joined or "npm init" in joined, (
            f"expected 'npm init -y' remediation in warnings, got: {result.warnings}"
        )

    def test_missing_package_json_makes_verdict_fail(self, tmp_path: Path) -> None:
        """``PhaseVerdict.passed`` is False when package.json is missing -> EXIT 80."""
        from ai_engineering.installer.phases.tools import ToolsPhase

        (tmp_path / ".ai-engineering" / "state").mkdir(parents=True)
        context = _build_typescript_context(tmp_path)

        with patch(
            "ai_engineering.installer.phases.tools.load_required_tools",
            return_value=_typescript_only_load_result(),
        ):
            phase = ToolsPhase()
            plan = phase.plan(context)
            result = phase.execute(plan, context)
            verdict = phase.verify(result, context)

        # PhaseVerdict.passed == False -> the CLI surface raises Exit(80).
        assert verdict.passed is False, (
            "verdict should fail when package.json missing -- got passed=True"
        )
