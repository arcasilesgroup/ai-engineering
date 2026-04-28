"""spec-101 T-2.25 + T-2.26 -- integration test exercising 3 stacks end-to-end.

Each stack drives a different launcher pattern through the data-driven
``stack_runner`` dispatch:

* **Python** -- ``ruff`` is invoked via ``shutil.which`` (USER_GLOBAL_UV_TOOL).
* **TypeScript** -- ``eslint`` is invoked via ``npx`` (PROJECT_LOCAL); the
  fixture seeds ``node_modules/.bin/eslint`` so the launcher resolves cleanly.
* **Go** -- ``staticcheck`` is invoked via ``shutil.which`` against a path that
  represents the user's ``~/go/bin`` (USER_GLOBAL).

Subprocess execution is mocked at the boundary
(``ai_engineering.policy.checks.stack_runner.subprocess.run``) so each test
runs hermetically without exec'ing a real linter.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from ai_engineering.policy.checks.stack_runner import (
    get_checks_for_stage,
    run_checks_for_specs,
)
from ai_engineering.policy.gates import GateResult
from ai_engineering.state.manifest import LoadResult
from ai_engineering.state.models import (
    GateHook,
    ToolScope,
    ToolSpec,
)

if TYPE_CHECKING:  # pragma: no cover - typing-only
    pass


# ---------------------------------------------------------------------------
# Fixture builders -- per-stack manifest + project layout
# ---------------------------------------------------------------------------


def _seed_python_manifest(project_root: Path) -> None:
    """Write a python-only manifest under ``project_root/.ai-engineering/``."""
    ai_dir = project_root / ".ai-engineering"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "manifest.yml").write_text(
        """schema_version: "2.0"
providers:
  vcs: github
  ides: [terminal]
  stacks: [python]
required_tools:
  baseline:
    - {name: gitleaks}
  python:
    - {name: ruff}
""",
        encoding="utf-8",
    )


def _seed_typescript_project(project_root: Path) -> None:
    """Seed a typescript project with package.json + node_modules/.bin/eslint."""
    ai_dir = project_root / ".ai-engineering"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "manifest.yml").write_text(
        """schema_version: "2.0"
providers:
  vcs: github
  ides: [terminal]
  stacks: [typescript]
required_tools:
  baseline:
    - {name: gitleaks}
  typescript:
    - {name: eslint, scope: project_local}
""",
        encoding="utf-8",
    )
    (project_root / "package.json").write_text('{"name":"demo"}', encoding="utf-8")
    bin_dir = project_root / "node_modules" / ".bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "eslint").write_text("#!/usr/bin/env node", encoding="utf-8")


def _seed_go_project(project_root: Path) -> None:
    """Seed a go project with manifest declaring staticcheck (USER_GLOBAL)."""
    ai_dir = project_root / ".ai-engineering"
    ai_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "manifest.yml").write_text(
        """schema_version: "2.0"
providers:
  vcs: github
  ides: [terminal]
  stacks: [go]
required_tools:
  baseline:
    - {name: gitleaks}
  go:
    - {name: staticcheck}
""",
        encoding="utf-8",
    )
    # go.mod marks the project as a Go module
    (project_root / "go.mod").write_text("module demo\n", encoding="utf-8")


def _ok_proc(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="ok", stderr="")


# ---------------------------------------------------------------------------
# Python stack -- USER_GLOBAL via shutil.which
# ---------------------------------------------------------------------------


class TestPythonStackEndToEnd:
    """python stack -> ``ruff check`` invoked via PATH."""

    def test_python_stack_dispatches_ruff_via_shutil_which(self, tmp_path: Path) -> None:
        """``get_checks_for_stage`` + ``run_checks_for_specs`` calls ``ruff`` via PATH."""
        _seed_python_manifest(tmp_path)

        # Replace the loader so we don't depend on the canonical 14-stack
        # registry. The integration here is the full data-driven dispatch
        # path -- the loader's contract is covered by its own unit tests.
        load_result = LoadResult(
            tools=[ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL)],
            skipped_stacks=[],
        )

        result = GateResult(hook=GateHook.PRE_COMMIT)
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.load_required_tools",
                return_value=load_result,
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value="/Users/x/.local/bin/ruff",
            ) as which_mock,
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run",
                return_value=_ok_proc(["ruff", "check", "."]),
            ) as run_mock,
        ):
            specs = get_checks_for_stage(GateHook.PRE_COMMIT, ["python"], project_root=tmp_path)
            run_checks_for_specs(tmp_path, result, specs)

        # ruff was found via shutil.which -- launcher path NOT taken.
        which_mock.assert_called()
        # Subprocess was invoked with ruff at the head, NOT npx.
        assert run_mock.called
        run_argv = run_mock.call_args.args[0]
        assert run_argv[0] == "ruff"
        assert "npx" not in run_argv
        # All checks passed.
        assert all(c.passed for c in result.checks), [(c.name, c.output) for c in result.checks]


# ---------------------------------------------------------------------------
# TypeScript stack -- PROJECT_LOCAL via npx
# ---------------------------------------------------------------------------


class TestTypeScriptStackEndToEnd:
    """typescript stack -> ``eslint`` invoked via ``npx`` launcher."""

    def test_typescript_stack_dispatches_eslint_via_npx(self, tmp_path: Path) -> None:
        """``eslint`` (project_local) routes through ``npx`` per D-101-15."""
        _seed_typescript_project(tmp_path)

        load_result = LoadResult(
            tools=[ToolSpec(name="eslint", scope=ToolScope.PROJECT_LOCAL)],
            skipped_stacks=[],
        )

        result = GateResult(hook=GateHook.PRE_COMMIT)
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.load_required_tools",
                return_value=load_result,
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run",
                return_value=_ok_proc(["npx", "eslint", "."]),
            ) as run_mock,
        ):
            specs = get_checks_for_stage(GateHook.PRE_COMMIT, ["typescript"], project_root=tmp_path)
            run_checks_for_specs(tmp_path, result, specs)

        # Verify the launcher emitted ``npx eslint`` -- the fixture seeded
        # node_modules/.bin/eslint so the launcher resolved cleanly.
        assert run_mock.called
        run_argv = run_mock.call_args.args[0]
        assert run_argv[0] == "npx", f"expected npx head, got {run_argv}"
        assert run_argv[1] == "eslint"
        # All checks passed.
        assert all(c.passed for c in result.checks), [(c.name, c.output) for c in result.checks]

    def test_typescript_stack_missing_node_modules_records_actionable_error(
        self,
        tmp_path: Path,
    ) -> None:
        """Without ``node_modules/.bin/eslint`` the gate surfaces ``npm install``."""
        ai_dir = tmp_path / ".ai-engineering"
        ai_dir.mkdir(parents=True)
        # Manifest seeded but node_modules NOT seeded.
        (ai_dir / "manifest.yml").write_text(
            "schema_version: '2.0'\nproviders:\n  stacks: [typescript]\n"
            "required_tools:\n  baseline:\n    - {name: gitleaks}\n"
            "  typescript:\n    - {name: eslint, scope: project_local}\n",
            encoding="utf-8",
        )

        load_result = LoadResult(
            tools=[ToolSpec(name="eslint", scope=ToolScope.PROJECT_LOCAL)],
            skipped_stacks=[],
        )

        result = GateResult(hook=GateHook.PRE_COMMIT)
        with patch(
            "ai_engineering.policy.checks.stack_runner.load_required_tools",
            return_value=load_result,
        ):
            specs = get_checks_for_stage(GateHook.PRE_COMMIT, ["typescript"], project_root=tmp_path)
            run_checks_for_specs(tmp_path, result, specs)

        # The launcher emitted MISSING_DEP_SENTINEL -> gate recorded a failure
        # whose output names ``npm install`` (the recovery action).
        eslint_checks = [c for c in result.checks if c.name == "eslint"]
        assert eslint_checks, "expected an eslint check to be recorded"
        assert not eslint_checks[0].passed
        assert "npm install" in eslint_checks[0].output


# ---------------------------------------------------------------------------
# Go stack -- USER_GLOBAL via shutil.which (~/go/bin/staticcheck)
# ---------------------------------------------------------------------------


class TestGoStackEndToEnd:
    """go stack -> ``staticcheck`` invoked via ``~/go/bin/staticcheck`` on PATH."""

    def test_go_stack_dispatches_staticcheck_via_shutil_which(
        self,
        tmp_path: Path,
    ) -> None:
        """staticcheck (USER_GLOBAL) routes via PATH; argv head NOT npx."""
        _seed_go_project(tmp_path)

        # Seed a fake staticcheck inside tmp_path/go-bin to simulate ~/go/bin.
        fake_gobin = tmp_path / "go-bin"
        fake_gobin.mkdir(parents=True)
        fake_staticcheck = fake_gobin / "staticcheck"
        fake_staticcheck.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        fake_staticcheck.chmod(0o755)

        load_result = LoadResult(
            tools=[ToolSpec(name="staticcheck", scope=ToolScope.USER_GLOBAL)],
            skipped_stacks=[],
        )

        result = GateResult(hook=GateHook.PRE_COMMIT)
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.load_required_tools",
                return_value=load_result,
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value=str(fake_staticcheck),
            ) as which_mock,
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run",
                return_value=_ok_proc(["staticcheck", "./..."]),
            ) as run_mock,
        ):
            # staticcheck is a linter -> pre-commit stage by default.
            specs = get_checks_for_stage(GateHook.PRE_COMMIT, ["go"], project_root=tmp_path)
            run_checks_for_specs(tmp_path, result, specs)

        # shutil.which was consulted (PATH-based dispatch).
        which_mock.assert_called()
        # Subprocess argv head is staticcheck, NOT npx.
        assert run_mock.called
        run_argv = run_mock.call_args.args[0]
        assert run_argv[0] == "staticcheck"
        assert "npx" not in run_argv
        # All checks passed.
        assert all(c.passed for c in result.checks), [(c.name, c.output) for c in result.checks]


# ---------------------------------------------------------------------------
# All-three-stacks combined sanity check
# ---------------------------------------------------------------------------


class TestThreeStacksTogether:
    """All three stacks resolve and dispatch correctly in the same run."""

    def test_three_stacks_each_uses_its_own_launcher(self, tmp_path: Path) -> None:
        """python -> ruff PATH, typescript -> npx eslint, go -> staticcheck PATH."""
        # Seed all three projects under separate sub-roots.
        py_root = tmp_path / "py"
        ts_root = tmp_path / "ts"
        go_root = tmp_path / "go"
        py_root.mkdir()
        ts_root.mkdir()
        go_root.mkdir()
        _seed_python_manifest(py_root)
        _seed_typescript_project(ts_root)
        _seed_go_project(go_root)

        # Each stack gets its own loader payload.
        py_load = LoadResult(
            tools=[ToolSpec(name="ruff", scope=ToolScope.USER_GLOBAL_UV_TOOL)],
            skipped_stacks=[],
        )
        ts_load = LoadResult(
            tools=[ToolSpec(name="eslint", scope=ToolScope.PROJECT_LOCAL)],
            skipped_stacks=[],
        )
        go_load = LoadResult(
            tools=[ToolSpec(name="staticcheck", scope=ToolScope.USER_GLOBAL)],
            skipped_stacks=[],
        )

        captured_argvs: list[list[str]] = []

        def _record_run(argv: list[str], **_kw: object) -> subprocess.CompletedProcess:
            captured_argvs.append(list(argv))
            return _ok_proc(argv)

        # Python
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.load_required_tools",
                return_value=py_load,
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value="/Users/x/.local/bin/ruff",
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run",
                side_effect=_record_run,
            ),
        ):
            result = GateResult(hook=GateHook.PRE_COMMIT)
            specs = get_checks_for_stage(GateHook.PRE_COMMIT, ["python"], project_root=py_root)
            run_checks_for_specs(py_root, result, specs)

        # TypeScript
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.load_required_tools",
                return_value=ts_load,
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run",
                side_effect=_record_run,
            ),
        ):
            result = GateResult(hook=GateHook.PRE_COMMIT)
            specs = get_checks_for_stage(GateHook.PRE_COMMIT, ["typescript"], project_root=ts_root)
            run_checks_for_specs(ts_root, result, specs)

        # Go
        with (
            patch(
                "ai_engineering.policy.checks.stack_runner.load_required_tools",
                return_value=go_load,
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.shutil.which",
                return_value=str(go_root / "go-bin" / "staticcheck"),
            ),
            patch(
                "ai_engineering.policy.checks.stack_runner.subprocess.run",
                side_effect=_record_run,
            ),
        ):
            (go_root / "go-bin").mkdir(exist_ok=True)
            sc = go_root / "go-bin" / "staticcheck"
            sc.write_text("", encoding="utf-8")
            result = GateResult(hook=GateHook.PRE_COMMIT)
            specs = get_checks_for_stage(GateHook.PRE_COMMIT, ["go"], project_root=go_root)
            run_checks_for_specs(go_root, result, specs)

        # Three subprocess invocations -- each with the launcher matching its
        # stack's scope.
        heads = [argv[0] for argv in captured_argvs]
        assert "ruff" in heads
        assert "npx" in heads  # typescript launcher
        assert "staticcheck" in heads
