"""Integration tests for spec-113 G-5: honest auto-remediate report message.

Three fixtures:
* full success: applied != [], failed == [] -> "all non-critical failures repaired automatically"
* partial success: applied != [], failed != [] -> count surface emitted
* nothing applied: applied == [] -> NEVER claims "all repaired"
"""

from __future__ import annotations

import pytest

from ai_engineering.cli_commands import core as cli_core
from ai_engineering.installer.auto_remediate import AutoRemediateReport


@pytest.fixture(autouse=True)
def _disable_json_mode() -> None:
    """Force human-readable mode so the renderer fires."""
    from ai_engineering import cli_output

    cli_output.set_json_mode(False)


def test_success_message_only_when_applied_and_clean(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """G-5: 'all non-critical failures repaired' only when applied != [] AND no residue."""
    report = AutoRemediateReport(
        invoked=True,
        applied=["tools.tools-required: installed: gitleaks"],
        failed=[],
        errors=[],
    )
    cli_core._render_auto_remediation_summary(report)
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "all non-critical failures repaired automatically" in combined


def test_partial_outcome_uses_explicit_counts(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """G-5: mixed result emits '<N> repaired (<list>); <M> still require manual action (<list>)'."""
    report = AutoRemediateReport(
        invoked=True,
        applied=["tools.tools-required: installed: gitleaks"],
        failed=["tools.tools-required: install failed: jq"],
        errors=[],
    )
    cli_core._render_auto_remediation_summary(report)
    captured = capsys.readouterr()
    # Collapse any line wrapping in the warning helper before substring asserts.
    combined = " ".join((captured.out + captured.err).split())
    assert "1 repaired" in combined
    assert "gitleaks" in combined
    assert "1 still require manual action" in combined
    assert "jq" in combined
    # Critically: must NOT claim everything was repaired.
    assert "all non-critical failures repaired automatically" not in combined


def test_zero_applied_with_residue_is_honest(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """G-5: zero repaired + residue must NEVER claim success."""
    report = AutoRemediateReport(
        invoked=True,
        applied=[],
        failed=["tools.tools-required: install failed: gitleaks"],
        errors=[],
    )
    cli_core._render_auto_remediation_summary(report)
    captured = capsys.readouterr()
    combined = " ".join((captured.out + captured.err).split())
    assert "all non-critical failures repaired automatically" not in combined
    assert "0 repaired" in combined or "0 fixed" in combined
    assert "gitleaks" in combined


def test_zero_applied_no_residue_is_honest(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """invoked=True with empty applied + empty residue is rare but must not claim success."""
    report = AutoRemediateReport(
        invoked=True,
        applied=[],
        failed=[],
        errors=[],
    )
    cli_core._render_auto_remediation_summary(report)
    captured = capsys.readouterr()
    combined = captured.out + captured.err
    assert "all non-critical failures repaired automatically" not in combined


def test_errors_count_into_residue(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Errors counted in residue alongside failed entries."""
    report = AutoRemediateReport(
        invoked=True,
        applied=["tools.tools-required: installed: gitleaks"],
        failed=[],
        errors=["tools.fix raised: boom"],
    )
    cli_core._render_auto_remediation_summary(report)
    captured = capsys.readouterr()
    combined = " ".join((captured.out + captured.err).split())
    assert "all non-critical failures repaired automatically" not in combined
    assert "1 repaired" in combined
    assert "1 still require manual action" in combined


def test_success_property_requires_applied_non_empty() -> None:
    """The success property tightens to require at least one applied entry."""
    rep_full = AutoRemediateReport(
        invoked=True,
        applied=["x"],
        failed=[],
        errors=[],
    )
    rep_empty = AutoRemediateReport(
        invoked=True,
        applied=[],
        failed=[],
        errors=[],
    )
    rep_partial = AutoRemediateReport(
        invoked=True,
        applied=["x"],
        failed=["y"],
        errors=[],
    )
    assert rep_full.success is True
    assert rep_empty.success is False
    assert rep_partial.success is False
