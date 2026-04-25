"""RED tests for spec-101 T-2.21/T-2.22: hook generator mode branching.

Drives the design of the ``mode`` parameter on ``generate_bash_hook`` and
``generate_powershell_hook`` per D-101-12. The hook preamble must branch on
the active :class:`PythonEnvMode` so each mode's environment shape is
established BEFORE the gate runs:

* ``uv-tool``: gate binaries live in the user-scope ``uv tool`` install
  prefix (``$HOME/.local/share/uv/tools/<bin>/``). The hook script MUST
  NOT prepend ``.venv/bin`` -- there is no project venv in this mode and
  the spurious export shadows the user-scope binaries.
* ``venv``: legacy per-cwd ``.venv/``. The hook keeps the current
  ``$ROOT_DIR/.venv/bin`` PATH prepend so ``ai-eng`` resolves out of the
  project venv even from GUI git clients.
* ``shared-parent``: the hook exports ``UV_PROJECT_ENVIRONMENT`` BEFORE
  invoking the gate so ``uv run`` resolves the same shared venv from
  every worktree of the repository.

These tests intentionally fail (RED phase) -- ``generate_bash_hook`` and
``generate_powershell_hook`` are extended to accept ``mode`` in T-2.22.
"""

from __future__ import annotations

import pytest

from ai_engineering.hooks.manager import (
    generate_bash_hook,
    generate_powershell_hook,
)
from ai_engineering.state.models import GateHook, PythonEnvMode

# ---------------------------------------------------------------------------
# Fixture: the three modes get their own preamble snapshot per shell
# ---------------------------------------------------------------------------


_BASH_VENV_BIN_FRAGMENTS = (
    '"$ROOT_DIR/.venv/bin"',
    '"$ROOT_DIR/.venv/Scripts"',
)

_PWSH_VENV_BIN_FRAGMENT = ".venv/Scripts"


# ---------------------------------------------------------------------------
# Bash hook -- mode branching
# ---------------------------------------------------------------------------


class TestGenerateBashHookUvTool:
    """``mode=uv-tool`` -- bash hook OMITS the ``.venv/bin`` PATH prepend."""

    def test_omits_venv_bin_path_export(self) -> None:
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.UV_TOOL)
        # The whole point of uv-tool mode is no project venv -- the hook
        # script must not pretend one exists.
        for fragment in _BASH_VENV_BIN_FRAGMENTS:
            assert fragment not in script

    def test_does_not_export_uv_project_environment(self) -> None:
        # ``UV_PROJECT_ENVIRONMENT`` is shared-parent's contract; uv-tool
        # uses the user-scope tool install layout instead.
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.UV_TOOL)
        assert "UV_PROJECT_ENVIRONMENT" not in script

    def test_invokes_gate_command(self) -> None:
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.UV_TOOL)
        assert "ai-eng gate pre-commit" in script

    def test_starts_with_bash_shebang(self) -> None:
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.UV_TOOL)
        assert script.startswith("#!/usr/bin/env bash")

    def test_keeps_strict_mode(self) -> None:
        # ``set -euo pipefail`` is load-bearing across all modes -- a hook
        # silently swallowing failures defeats the gate surface entirely.
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.UV_TOOL)
        assert "set -euo pipefail" in script


class TestGenerateBashHookVenv:
    """``mode=venv`` -- bash hook keeps the current ``.venv/bin`` PATH prepend."""

    def test_includes_venv_bin_path_export(self) -> None:
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.VENV)
        # Both the POSIX and Windows paths must remain so cross-OS hooks
        # work the same as today.
        for fragment in _BASH_VENV_BIN_FRAGMENTS:
            assert fragment in script

    def test_does_not_export_uv_project_environment(self) -> None:
        # venv mode is per-cwd; no shared-parent semantics -> no env var.
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.VENV)
        assert "UV_PROJECT_ENVIRONMENT" not in script

    def test_path_export_precedes_gate_invocation(self) -> None:
        # PATH must be set BEFORE ``ai-eng`` is invoked, otherwise the
        # binary resolves out of the user's interactive shell PATH instead
        # of the venv -- defeats the whole preamble.
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.VENV)
        venv_pos = script.index(".venv/bin")
        cmd_pos = script.index("ai-eng gate pre-commit")
        assert venv_pos < cmd_pos


class TestGenerateBashHookSharedParent:
    """``mode=shared-parent`` -- bash hook exports ``UV_PROJECT_ENVIRONMENT``."""

    def test_exports_uv_project_environment(self) -> None:
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.SHARED_PARENT)
        assert "UV_PROJECT_ENVIRONMENT" in script

    def test_uv_project_environment_is_dynamic_via_git_rev_parse(self) -> None:
        # Per spec, the export evaluates ``$(git rev-parse --git-common-dir)``
        # at hook-execution time so the value tracks the current worktree.
        # Hardcoded paths would break worktree workflows.
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.SHARED_PARENT)
        assert "git rev-parse --git-common-dir" in script
        assert ".venv" in script

    def test_export_precedes_gate_invocation(self) -> None:
        # The env var must be set BEFORE ``ai-eng gate`` runs so ``uv run``
        # picks up the shared venv root, not a per-worktree one.
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.SHARED_PARENT)
        env_pos = script.index("UV_PROJECT_ENVIRONMENT")
        cmd_pos = script.index("ai-eng gate pre-commit")
        assert env_pos < cmd_pos

    def test_starts_with_bash_shebang(self) -> None:
        script = generate_bash_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.SHARED_PARENT)
        assert script.startswith("#!/usr/bin/env bash")


# ---------------------------------------------------------------------------
# PowerShell hook -- mode branching
# ---------------------------------------------------------------------------


class TestGeneratePowershellHookUvTool:
    """``mode=uv-tool`` -- pwsh hook OMITS the ``.venv/Scripts`` prepend."""

    def test_omits_venv_scripts_path_export(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.UV_TOOL)
        assert _PWSH_VENV_BIN_FRAGMENT not in script

    def test_does_not_export_uv_project_environment(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.UV_TOOL)
        assert "UV_PROJECT_ENVIRONMENT" not in script

    def test_invokes_gate_command(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.UV_TOOL)
        assert "ai-eng gate pre-commit" in script

    def test_keeps_strict_error_action(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.UV_TOOL)
        assert "$ErrorActionPreference = 'Stop'" in script

    def test_keeps_exit_code_propagation(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.UV_TOOL)
        assert "$LASTEXITCODE" in script


class TestGeneratePowershellHookVenv:
    """``mode=venv`` -- pwsh hook keeps the current ``.venv/Scripts`` prepend."""

    def test_includes_venv_scripts_path_export(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.VENV)
        assert _PWSH_VENV_BIN_FRAGMENT in script
        assert "$env:PATH" in script

    def test_does_not_export_uv_project_environment(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.VENV)
        assert "UV_PROJECT_ENVIRONMENT" not in script

    def test_path_export_precedes_gate_invocation(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.VENV)
        venv_pos = script.index(".venv/Scripts")
        cmd_pos = script.index("ai-eng gate pre-commit")
        assert venv_pos < cmd_pos


class TestGeneratePowershellHookSharedParent:
    """``mode=shared-parent`` -- pwsh hook exports ``UV_PROJECT_ENVIRONMENT``."""

    def test_exports_uv_project_environment(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.SHARED_PARENT)
        # PowerShell's env var syntax: ``$env:UV_PROJECT_ENVIRONMENT = ...``
        assert "UV_PROJECT_ENVIRONMENT" in script

    def test_uv_project_environment_invokes_git_rev_parse(self) -> None:
        # PowerShell uses ``$(...)`` style subexpression for command substitution.
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.SHARED_PARENT)
        assert "git rev-parse --git-common-dir" in script
        assert ".venv" in script

    def test_export_precedes_gate_invocation(self) -> None:
        script = generate_powershell_hook(GateHook.PRE_COMMIT, mode=PythonEnvMode.SHARED_PARENT)
        env_pos = script.index("UV_PROJECT_ENVIRONMENT")
        cmd_pos = script.index("ai-eng gate pre-commit")
        assert env_pos < cmd_pos


# ---------------------------------------------------------------------------
# Syntactic sanity -- balanced quotes, no dangling escapes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("mode", list(PythonEnvMode))
@pytest.mark.parametrize(
    "hook",
    [GateHook.PRE_COMMIT, GateHook.COMMIT_MSG, GateHook.PRE_PUSH],
)
class TestModeAcrossAllHooks:
    """Every (mode, hook) pair generates well-formed bash/pwsh."""

    def test_bash_quotes_are_balanced(self, mode: PythonEnvMode, hook: GateHook) -> None:
        script = generate_bash_hook(hook, mode=mode)
        # Double quotes must balance pairwise -- a dangling quote breaks
        # the script silently.
        assert script.count('"') % 2 == 0

    def test_bash_no_trailing_backslash(self, mode: PythonEnvMode, hook: GateHook) -> None:
        # ``\`` at end-of-line continues the line -- if the line below is
        # blank we get an opaque syntax error in bash. Render forbids them.
        script = generate_bash_hook(hook, mode=mode)
        for line in script.splitlines():
            stripped = line.rstrip()
            if stripped.endswith("\\"):
                # Allow continuation lines that have a non-empty next char,
                # but our renderer doesn't use them today.
                pytest.fail(f"unexpected line continuation: {line!r}")

    def test_pwsh_no_unterminated_strings(self, mode: PythonEnvMode, hook: GateHook) -> None:
        # PowerShell single-quote strings -- our renderer uses them only
        # as paired delimiters; an odd count breaks the script.
        script = generate_powershell_hook(hook, mode=mode)
        assert script.count("'") % 2 == 0

    def test_invokes_correct_gate_command(self, mode: PythonEnvMode, hook: GateHook) -> None:
        bash_script = generate_bash_hook(hook, mode=mode)
        pwsh_script = generate_powershell_hook(hook, mode=mode)
        gate_cmd = f"ai-eng gate {hook.value}"
        assert gate_cmd in bash_script
        assert gate_cmd in pwsh_script
