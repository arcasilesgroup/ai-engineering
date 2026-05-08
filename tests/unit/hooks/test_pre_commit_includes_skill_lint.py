"""spec-127 M1 (sub-002 T-F.2): pre-commit registry must invoke ``skill_lint``.

Asserts that ``PRE_COMMIT_CHECKS['common']`` carries an entry whose
command runs ``python -m skill_lint --check``. The check is registered
under the ``common`` bucket because conformance is stack-agnostic —
the executor walks ``common`` first, parallel with stack-specific
entries, so the ≤200 ms D-127-08 hot-path budget is preserved.
"""

from __future__ import annotations

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
