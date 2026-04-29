"""Integration tests for spec-113 G-11 / D-113-09: VCS warning consolidation."""

from __future__ import annotations

from ai_engineering.doctor.models import CheckResult, CheckStatus
from ai_engineering.doctor.output_formatter import (
    VCSConsolidation,
    consolidate_vcs_warnings,
)


def _warn(name: str, message: str) -> CheckResult:
    return CheckResult(name=name, status=CheckStatus.WARN, message=message)


def _ok(name: str, message: str) -> CheckResult:
    return CheckResult(name=name, status=CheckStatus.OK, message=message)


def test_consolidates_when_all_three_warn() -> None:
    """All three VCS checks WARN with gh missing -> single consolidated message."""
    checks = [
        _warn("tools-vcs", "VCS tool 'gh' not found (provider: github)"),
        _warn("vcs-auth", "gh auth not verifiable until installed"),
        _warn("detection-current", "Could not determine VCS provider from git remote"),
    ]
    result = consolidate_vcs_warnings(
        checks,
        vcs_provider="github",
        install_hint="sudo apt-get install -y gh",
    )
    assert isinstance(result, VCSConsolidation)
    assert result.consolidated is True
    assert "VCS 'github' tooling: gh missing" in result.message
    assert "sudo apt-get install -y gh" in result.message
    assert "auth not verifiable" in result.message
    assert result.suppressed_names == frozenset({"tools-vcs", "vcs-auth", "detection-current"})


def test_no_consolidation_when_any_check_is_ok() -> None:
    """If any of the three is OK, fallback to per-check rendering."""
    checks = [
        _warn("tools-vcs", "VCS tool 'gh' not found (provider: github)"),
        _ok("vcs-auth", "gh authenticated"),
        _warn("detection-current", "Could not determine VCS provider from git remote"),
    ]
    result = consolidate_vcs_warnings(checks, vcs_provider="github")
    assert result.consolidated is False
    assert result.message == ""


def test_no_consolidation_when_root_is_not_gh_missing() -> None:
    """If tools-vcs message is not 'gh not found' shape, fallback."""
    checks = [
        _warn("tools-vcs", "Some other warning"),
        _warn("vcs-auth", "gh auth not verifiable"),
        _warn("detection-current", "Could not determine VCS provider"),
    ]
    result = consolidate_vcs_warnings(checks, vcs_provider="github")
    assert result.consolidated is False


def test_no_consolidation_when_only_two_present() -> None:
    """Need all three checks present to consolidate."""
    checks = [
        _warn("tools-vcs", "VCS tool 'gh' not found"),
        _warn("vcs-auth", "auth not verifiable"),
    ]
    result = consolidate_vcs_warnings(checks, vcs_provider="github")
    assert result.consolidated is False


def test_install_hint_optional() -> None:
    """When install_hint is None, the consolidated message still makes sense."""
    checks = [
        _warn("tools-vcs", "VCS tool 'gh' not found"),
        _warn("vcs-auth", "auth not verifiable"),
        _warn("detection-current", "no remote"),
    ]
    result = consolidate_vcs_warnings(checks, vcs_provider="github", install_hint=None)
    assert result.consolidated is True
    assert "gh missing" in result.message
    assert "install with" not in result.message  # no hint -> no clause


def test_provider_label_falls_back_to_github() -> None:
    """When vcs_provider is None, label defaults to 'github'."""
    checks = [
        _warn("tools-vcs", "VCS tool 'gh' not found"),
        _warn("vcs-auth", "auth not verifiable"),
        _warn("detection-current", "no remote"),
    ]
    result = consolidate_vcs_warnings(checks, vcs_provider=None)
    assert result.consolidated is True
    assert "VCS 'github' tooling" in result.message
