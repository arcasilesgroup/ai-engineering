"""spec-127 M1 (sub-002 T-F.2): pre-commit registry must invoke ``skill_lint``.

Asserts that ``PRE_COMMIT_CHECKS['common']`` carries an entry whose
command runs ``python -m skill_lint --check``. The check is registered
under the ``common`` bucket because conformance is stack-agnostic —
the executor walks ``common`` first, parallel with stack-specific
entries, so the ≤200 ms D-127-08 hot-path budget is preserved.
"""

from __future__ import annotations

import shutil

import pytest

from ai_engineering.policy.checks.stack_runner import PRE_COMMIT_CHECKS


@pytest.mark.unit
def test_pre_commit_common_includes_skill_lint() -> None:
    common = PRE_COMMIT_CHECKS.get("common", [])
    names = [c.name for c in common]
    assert "skill_lint" in names, (
        f"PRE_COMMIT_CHECKS['common'] must include 'skill_lint'; got {names}"
    )


@pytest.mark.unit
def test_skill_lint_check_command_shape() -> None:
    common = PRE_COMMIT_CHECKS.get("common", [])
    skill_lint = next((c for c in common if c.name == "skill_lint"), None)
    assert skill_lint is not None
    # Command must invoke the Python module entry point with --check.
    cmd_tail = skill_lint.cmd[-3:]
    assert cmd_tail == ["-m", "skill_lint", "--check"], (
        f"skill_lint pre-commit cmd shape unexpected: {skill_lint.cmd}"
    )


@pytest.mark.unit
def test_skill_lint_is_required() -> None:
    """The declared contract must match what the runner actually does.

    ``run_tool_check`` sets ``passed = proc.returncode == 0``
    unconditionally; ``required`` is consulted in exactly two places, both
    missing-binary branches (a ``shutil.which`` miss, and
    ``FileNotFoundError``). So ``required=False`` never made this check
    advisory — a non-zero exit has always blocked the pre-commit gate.
    spec-201 D-201-15 promotes the flag so the declaration stops lying.
    """
    common = PRE_COMMIT_CHECKS.get("common", [])
    skill_lint = next((c for c in common if c.name == "skill_lint"), None)
    assert skill_lint is not None
    assert skill_lint.required is True, (
        "skill_lint must be required=True (D-201-15): a non-zero exit already "
        "fails the gate, so required=False only mislabels the contract"
    )


@pytest.mark.unit
def test_skill_lint_interpreter_head_is_resolvable() -> None:
    """The command head must resolve on a host with no activated venv.

    ``required=True`` is only safe if the binary is always findable.
    ``which python`` returns nothing on a plain macOS shell (only
    ``python3`` exists), so a bare ``"python"`` head would turn today's
    silent "python not found -- skipped" pass into a hard
    "python not found -- required." block on every such host, framework
    repo and consumer alike, because ``stack_runner`` ships in the wheel.
    ``stack_runner`` already applies this same fix to ``pytest`` and
    ``ty``, forcing them onto the interpreter that is actually running.
    """
    common = PRE_COMMIT_CHECKS.get("common", [])
    skill_lint = next((c for c in common if c.name == "skill_lint"), None)
    assert skill_lint is not None
    head = skill_lint.cmd[0]
    assert shutil.which(head) is not None, (
        f"skill_lint interpreter head {head!r} does not resolve on PATH; "
        "with required=True that is a hard pre-commit block (spec-201 R-5)"
    )


@pytest.mark.unit
def test_skill_lint_runs_alongside_gitleaks() -> None:
    """skill_lint must not displace gitleaks — both fire on every commit."""
    common_names = [c.name for c in PRE_COMMIT_CHECKS.get("common", [])]
    assert "gitleaks" in common_names
    assert "skill_lint" in common_names
    # Order: gitleaks first (faster fail-stop on secrets), skill_lint
    # after (≤200 ms wall-time).
    g_idx = common_names.index("gitleaks")
    s_idx = common_names.index("skill_lint")
    assert g_idx < s_idx, f"gitleaks should execute before skill_lint (got order {common_names})"
