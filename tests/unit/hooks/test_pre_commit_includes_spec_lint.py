"""spec-131 S7 (sub-007 T-7.10): pre-commit registry must invoke ``spec_lint``.

Asserts that ``PRE_COMMIT_CHECKS['common']`` carries an entry whose
command runs ``python -m spec_lint --check``. The check is registered
under the ``common`` bucket because schema validation is stack-agnostic
— the executor walks ``common`` first, parallel with stack-specific
entries, so the ≤500 ms R-131-13 hot-path budget is preserved.
"""

from __future__ import annotations

import pytest

from ai_engineering.policy.checks.stack_runner import PRE_COMMIT_CHECKS


@pytest.mark.unit
def test_pre_commit_common_includes_spec_lint() -> None:
    common = PRE_COMMIT_CHECKS.get("common", [])
    names = [c.name for c in common]
    assert "spec_lint" in names, (
        f"PRE_COMMIT_CHECKS['common'] must include 'spec_lint'; got {names}"
    )


@pytest.mark.unit
def test_spec_lint_check_command_shape() -> None:
    common = PRE_COMMIT_CHECKS.get("common", [])
    spec_lint = next((c for c in common if c.name == "spec_lint"), None)
    assert spec_lint is not None
    # Command must invoke the Python module entry point with --check.
    cmd_tail = spec_lint.cmd[-3:]
    assert cmd_tail == ["-m", "spec_lint", "--check"], (
        f"spec_lint pre-commit cmd shape unexpected: {spec_lint.cmd}"
    )


@pytest.mark.unit
def test_spec_lint_runs_alongside_skill_lint_and_gitleaks() -> None:
    """spec_lint joins gitleaks + skill_lint in the common bucket.

    Order convention: gitleaks first (fast fail-stop on secrets),
    skill_lint second (≤200 ms wall-time), spec_lint third (≤500 ms
    wall-time). Total common-bucket wall-time stays well under 1 s
    even when each is invoked serially.
    """
    common_names = [c.name for c in PRE_COMMIT_CHECKS.get("common", [])]
    assert "gitleaks" in common_names
    assert "skill_lint" in common_names
    assert "spec_lint" in common_names

    g_idx = common_names.index("gitleaks")
    sk_idx = common_names.index("skill_lint")
    sp_idx = common_names.index("spec_lint")
    assert g_idx < sk_idx < sp_idx, (
        f"expected gitleaks < skill_lint < spec_lint order; got {common_names}"
    )


@pytest.mark.unit
def test_spec_lint_is_non_required() -> None:
    """``required=False`` so missing python on a stripped checkout never
    blocks the pre-commit gate; CI still enforces via the workflow."""
    common = PRE_COMMIT_CHECKS.get("common", [])
    spec_lint = next((c for c in common if c.name == "spec_lint"), None)
    assert spec_lint is not None
    assert spec_lint.required is False
