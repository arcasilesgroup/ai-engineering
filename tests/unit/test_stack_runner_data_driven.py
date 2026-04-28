"""spec-101 T-2.23 RED + T-2.24 GREEN -- data-driven stack_runner registry.

These tests exercise the data-driven dispatch contract introduced by D-101-01
+ D-101-15 + R-15:

* :func:`get_checks_for_stage` resolves the per-stage check list from
  :func:`ai_engineering.state.manifest.load_required_tools` at runtime --
  there is no hard-coded ``PRE_COMMIT_CHECKS`` / ``PRE_PUSH_CHECKS`` registry
  the new entry-point may consult.
* A declared stack without a matching ``required_tools.<stack>`` block
  surfaces an :class:`UnknownStackError` (bubbled from the loader) -- closing
  R-15 (manifest drift between ``providers.stacks`` and check registry).
* A tool with ``scope=ToolScope.PROJECT_LOCAL`` routes through
  :func:`ai_engineering.installer.launchers.resolve_project_local` instead
  of ``shutil.which`` -- D-101-15.
* A tool with ``scope=ToolScope.USER_GLOBAL`` (or
  ``USER_GLOBAL_UV_TOOL``) continues to resolve via ``shutil.which``.

The loader is monkey-patched so tests are deterministic and independent of
the on-disk manifest.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from ai_engineering.policy.gates import GateResult
from ai_engineering.state.manifest import LoadResult, UnknownStackError
from ai_engineering.state.models import (
    GateHook,
    ToolScope,
    ToolSpec,
)

if TYPE_CHECKING:  # pragma: no cover - typing-only
    pass


# ---------------------------------------------------------------------------
# Fixtures: deterministic ``LoadResult`` factories
# ---------------------------------------------------------------------------


def _baseline_only() -> LoadResult:
    """LoadResult containing only baseline tools (gitleaks, semgrep)."""
    return LoadResult(
        tools=[
            ToolSpec(name="gitleaks", scope=ToolScope.USER_GLOBAL),
            ToolSpec(name="semgrep", scope=ToolScope.USER_GLOBAL),
        ],
        skipped_stacks=[],
    )


def _python_stack() -> LoadResult:
    """LoadResult mirroring the canonical python stack tools."""
    return LoadResult(
        tools=[
            ToolSpec(name="gitleaks", scope=ToolScope.USER_GLOBAL),
            ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL),
            ToolSpec(name="ty", scope=ToolScope.USER_GLOBAL_UV_TOOL),
            ToolSpec(name="pip-audit", scope=ToolScope.USER_GLOBAL_UV_TOOL),
            ToolSpec(name="pytest", scope=ToolScope.USER_GLOBAL),
        ],
        skipped_stacks=[],
    )


def _typescript_stack() -> LoadResult:
    """LoadResult for typescript stack -- 4 project_local tools."""
    return LoadResult(
        tools=[
            ToolSpec(name="gitleaks", scope=ToolScope.USER_GLOBAL),
            ToolSpec(name="prettier", scope=ToolScope.PROJECT_LOCAL),
            ToolSpec(name="eslint", scope=ToolScope.PROJECT_LOCAL),
            ToolSpec(name="tsc", scope=ToolScope.PROJECT_LOCAL),
            ToolSpec(name="vitest", scope=ToolScope.PROJECT_LOCAL),
        ],
        skipped_stacks=[],
    )


# ---------------------------------------------------------------------------
# T-2.23: get_checks_for_stage entry-point exists + is callable
# ---------------------------------------------------------------------------


class TestGetChecksForStageContract:
    """``get_checks_for_stage`` must exist and accept (stage, stacks, root)."""

    def test_function_is_importable(self) -> None:
        """``get_checks_for_stage`` must be exported from ``stack_runner``."""
        from ai_engineering.policy.checks.stack_runner import get_checks_for_stage

        assert callable(get_checks_for_stage)

    def test_function_returns_list(self, tmp_path: Path) -> None:
        """``get_checks_for_stage`` returns a list (possibly empty)."""
        from ai_engineering.policy.checks.stack_runner import get_checks_for_stage

        with patch(
            "ai_engineering.policy.checks.stack_runner.load_required_tools",
            return_value=_baseline_only(),
        ):
            result = get_checks_for_stage(GateHook.PRE_COMMIT, ["python"], project_root=tmp_path)

        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# T-2.23: Data-driven resolution -- no hard-coded dict consultation
# ---------------------------------------------------------------------------


class TestDataDrivenResolution:
    """Stage check lists must come from ``load_required_tools`` at runtime."""

    def test_calls_load_required_tools_with_stacks(self, tmp_path: Path) -> None:
        """``get_checks_for_stage`` must invoke the loader with caller's stacks."""
        from ai_engineering.policy.checks.stack_runner import get_checks_for_stage

        with patch(
            "ai_engineering.policy.checks.stack_runner.load_required_tools",
            return_value=_python_stack(),
        ) as loader_mock:
            get_checks_for_stage(GateHook.PRE_COMMIT, ["python"], project_root=tmp_path)

        loader_mock.assert_called_once()
        args = loader_mock.call_args.args
        kwargs = loader_mock.call_args.kwargs
        passed = args[0] if args else kwargs.get("stacks")
        assert list(passed) == ["python"]

    def test_loader_receives_project_root_via_root_kw(self, tmp_path: Path) -> None:
        """The loader must receive ``root=`` so the manifest is read from cwd."""
        from ai_engineering.policy.checks.stack_runner import get_checks_for_stage

        with patch(
            "ai_engineering.policy.checks.stack_runner.load_required_tools",
            return_value=_python_stack(),
        ) as loader_mock:
            get_checks_for_stage(GateHook.PRE_COMMIT, ["python"], project_root=tmp_path)

        # The loader must receive ``root=tmp_path`` so the manifest is sourced
        # from the gate's cwd rather than the global Path.cwd() default.
        kwargs = loader_mock.call_args.kwargs
        assert kwargs.get("root") == tmp_path

    def test_pre_commit_includes_linters_and_formatters(self, tmp_path: Path) -> None:
        """Linter/formatter tools (ruff, gitleaks) appear in pre-commit stage."""
        from ai_engineering.policy.checks.stack_runner import get_checks_for_stage

        with patch(
            "ai_engineering.policy.checks.stack_runner.load_required_tools",
            return_value=_python_stack(),
        ):
            checks = get_checks_for_stage(GateHook.PRE_COMMIT, ["python"], project_root=tmp_path)

        names = {c.name for c in checks}
        # ruff + gitleaks are pre-commit canonical members.
        assert "gitleaks" in names or any("gitleaks" in n for n in names)
        assert any("ruff" in n for n in names)

    def test_pre_push_includes_security_and_test_runners(self, tmp_path: Path) -> None:
        """Security/test tools (semgrep, pytest, pip-audit) appear in pre-push."""
        from ai_engineering.policy.checks.stack_runner import get_checks_for_stage

        with patch(
            "ai_engineering.policy.checks.stack_runner.load_required_tools",
            return_value=_python_stack(),
        ):
            checks = get_checks_for_stage(GateHook.PRE_PUSH, ["python"], project_root=tmp_path)

        names = {c.name for c in checks}
        # pip-audit + pytest are canonical pre-push members.
        assert any("pip-audit" in n or "pip_audit" in n for n in names)
        # pytest -> stack-tests
        assert any("test" in n.lower() for n in names)


# ---------------------------------------------------------------------------
# T-2.23: R-15 -- declared stack without registry entry surfaces error
# ---------------------------------------------------------------------------


class TestUnknownStackErrorPropagates:
    """R-15: declared stack without ``required_tools.<stack>`` -> error."""

    def test_unknown_stack_raises_loader_error(self, tmp_path: Path) -> None:
        """Loader raises ``UnknownStackError`` -> caller surfaces it.

        The loader (``state.manifest.load_required_tools``) raises
        ``UnknownStackError`` for a stack not present in the canonical
        14-stack registry. The data-driven dispatcher must NOT swallow
        the error -- propagating it closes R-15 (silent no-op when
        manifest declares a stack with no checks registered).
        """
        from ai_engineering.policy.checks.stack_runner import get_checks_for_stage

        # Don't mock the loader -- let the real one fire and raise.
        with pytest.raises(UnknownStackError):
            get_checks_for_stage(
                GateHook.PRE_COMMIT,
                ["totally_not_a_stack_name"],
                project_root=tmp_path,
            )


# ---------------------------------------------------------------------------
# T-2.23: project_local routes through ``resolve_project_local``
# ---------------------------------------------------------------------------


class TestProjectLocalDispatch:
    """``scope=PROJECT_LOCAL`` routes through ``resolve_project_local``."""

    def test_project_local_invokes_launcher(self, tmp_path: Path) -> None:
        """A project_local tool must call ``resolve_project_local``."""
        from ai_engineering.policy.checks.stack_runner import run_tool_check_for_spec

        # Seed node_modules/.bin/eslint so the launcher resolves cleanly.
        bin_dir = tmp_path / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "eslint").write_text("")

        eslint_spec = ToolSpec(name="eslint", scope=ToolScope.PROJECT_LOCAL)
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_proc = subprocess.CompletedProcess(
            args=["npx", "eslint", "."], returncode=0, stdout="ok", stderr=""
        )

        # Capture the launcher invocation by patching the launcher module.
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.resolve_project_local",
                return_value=["npx", "eslint"],
            ) as launcher_mock,
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run",
                return_value=mock_proc,
            ) as run_mock,
        ):
            run_tool_check_for_spec(
                result,
                tool_spec=eslint_spec,
                stack="typescript",
                check_name="eslint",
                args=["."],
                cwd=tmp_path,
            )

        launcher_mock.assert_called_once()
        # First positional must be the ToolSpec; ``stack="typescript"`` kw passed.
        call_args = launcher_mock.call_args
        passed_spec = call_args.args[0] if call_args.args else call_args.kwargs.get("tool_spec")
        assert passed_spec.name == "eslint"
        # The launcher's argv MUST be merged with args and dispatched to subprocess.run.
        run_mock.assert_called_once()
        run_argv = (
            run_mock.call_args.args[0]
            if run_mock.call_args.args
            else run_mock.call_args.kwargs.get("args") or []
        )
        # We expect the cmd to begin with the launcher argv (npx eslint).
        assert run_argv[0] == "npx"
        assert run_argv[1] == "eslint"
        assert "." in run_argv

    def test_project_local_missing_dep_records_actionable_message(
        self,
        tmp_path: Path,
    ) -> None:
        """Missing launcher dep -> the gate records the recovery message."""
        from ai_engineering.installer.launchers import MISSING_DEP_SENTINEL
        from ai_engineering.policy.checks.stack_runner import run_tool_check_for_spec

        eslint_spec = ToolSpec(name="eslint", scope=ToolScope.PROJECT_LOCAL)
        result = GateResult(hook=GateHook.PRE_COMMIT)

        # The launcher returns a sentinel argv when node_modules/.bin/eslint
        # is absent. The gate must record this as a failed check whose output
        # surfaces the actionable recovery message.
        sentinel_argv = [MISSING_DEP_SENTINEL, "run", "'npm", "install'", "to", "install", "eslint"]
        with patch(
            "ai_engineering.policy.checks.stack_runner.resolve_project_local",
            return_value=sentinel_argv,
        ):
            run_tool_check_for_spec(
                result,
                tool_spec=eslint_spec,
                stack="typescript",
                check_name="eslint",
                args=["."],
                cwd=tmp_path,
            )

        # Expect exactly one recorded check, failed, with a useful message.
        assert len(result.checks) == 1
        check = result.checks[0]
        assert check.passed is False
        assert "npm install" in check.output

    def test_user_global_does_not_call_launcher(self, tmp_path: Path) -> None:
        """``scope=USER_GLOBAL`` resolves via ``shutil.which`` -- not launcher."""
        from ai_engineering.policy.checks.stack_runner import run_tool_check_for_spec

        gitleaks_spec = ToolSpec(name="gitleaks", scope=ToolScope.USER_GLOBAL)
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_proc = subprocess.CompletedProcess(
            args=["gitleaks", "protect"], returncode=0, stdout="ok", stderr=""
        )

        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.resolve_project_local",
                return_value=["should", "never", "happen"],
            ) as launcher_mock,
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value="/usr/bin/gitleaks",
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run",
                return_value=mock_proc,
            ),
        ):
            run_tool_check_for_spec(
                result,
                tool_spec=gitleaks_spec,
                stack="baseline",
                check_name="gitleaks",
                args=["protect", "--staged"],
                cwd=tmp_path,
            )

        launcher_mock.assert_not_called()

    def test_user_global_uv_tool_does_not_call_launcher(self, tmp_path: Path) -> None:
        """``scope=USER_GLOBAL_UV_TOOL`` (ruff/ty) also resolves via shutil.which."""
        from ai_engineering.policy.checks.stack_runner import run_tool_check_for_spec

        ruff_spec = ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL)
        result = GateResult(hook=GateHook.PRE_COMMIT)
        mock_proc = subprocess.CompletedProcess(
            args=["ruff", "check"], returncode=0, stdout="ok", stderr=""
        )

        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.resolve_project_local",
                return_value=["should", "never", "happen"],
            ) as launcher_mock,
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value="/Users/x/.local/bin/ruff",
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run",
                return_value=mock_proc,
            ),
        ):
            run_tool_check_for_spec(
                result,
                tool_spec=ruff_spec,
                stack="python",
                check_name="ruff-check",
                args=["check", "."],
                cwd=tmp_path,
            )

        launcher_mock.assert_not_called()


# ---------------------------------------------------------------------------
# T-2.23: project_local check appears in get_checks_for_stage output
# ---------------------------------------------------------------------------


class TestProjectLocalChecksAppearInStage:
    """The data-driven dispatcher must surface project_local tools too."""

    def test_typescript_stack_emits_project_local_checks(self, tmp_path: Path) -> None:
        """Typescript stack -> pre-commit list contains eslint + prettier."""
        from ai_engineering.policy.checks.stack_runner import get_checks_for_stage

        with patch(
            "ai_engineering.policy.checks.stack_runner.load_required_tools",
            return_value=_typescript_stack(),
        ):
            checks = get_checks_for_stage(
                GateHook.PRE_COMMIT, ["typescript"], project_root=tmp_path
            )

        names = {c.name for c in checks}
        assert any("eslint" in n for n in names)
        assert any("prettier" in n for n in names)

    def test_typescript_stack_pre_push_includes_tsc_and_vitest(
        self,
        tmp_path: Path,
    ) -> None:
        """Typescript pre-push -> tsc + vitest (test/typecheck stage)."""
        from ai_engineering.policy.checks.stack_runner import get_checks_for_stage

        with patch(
            "ai_engineering.policy.checks.stack_runner.load_required_tools",
            return_value=_typescript_stack(),
        ):
            checks = get_checks_for_stage(GateHook.PRE_PUSH, ["typescript"], project_root=tmp_path)

        names = {c.name for c in checks}
        assert any("tsc" in n for n in names)
        assert any("vitest" in n for n in names)


# ---------------------------------------------------------------------------
# T-2.23: Backwards compatibility -- legacy entrypoint keeps working
# ---------------------------------------------------------------------------


class TestBackwardsCompatibility:
    """Existing ``run_checks_for_stacks`` + ``PRE_COMMIT_CHECKS`` are preserved.

    The shim exists so the in-place gates.py and the existing test suite
    continue to function while consumers migrate to ``get_checks_for_stage``.
    """

    def test_legacy_dicts_still_exported(self) -> None:
        """``PRE_COMMIT_CHECKS`` and ``PRE_PUSH_CHECKS`` remain importable."""
        from ai_engineering.policy.checks.stack_runner import (
            PRE_COMMIT_CHECKS,
            PRE_PUSH_CHECKS,
        )

        assert isinstance(PRE_COMMIT_CHECKS, dict)
        assert isinstance(PRE_PUSH_CHECKS, dict)

    def test_run_checks_for_stacks_still_callable(self, tmp_path: Path) -> None:
        """The legacy registry-driven path keeps working for python."""
        from ai_engineering.policy.checks.stack_runner import (
            PRE_COMMIT_CHECKS,
            run_checks_for_stacks,
        )

        result = GateResult(hook=GateHook.PRE_COMMIT)
        with patch(
            "ai_engineering.policy.checks.stack_runner.shutil.which",
            return_value=None,  # all tools missing -> graceful skip
        ):
            run_checks_for_stacks(tmp_path, result, PRE_COMMIT_CHECKS, ["python"])

        # Should produce check entries without raising.
        assert isinstance(result.checks, list)
