"""Banner + escalation-reason coverage for ``policy/mode_dispatch.py``.

Exercises the surface that the gate CLI relies on for user-facing output
(see ``cli_commands/gate.py:_emit_mode_banner``):

* :func:`banner_for_mode` -- string composition for every (manifest_mode,
  resolved) combination.
* :func:`explain_escalation_reason` -- which trigger label gets shown.
* The ``release/*`` glob path of :func:`_branch_is_protected` reached via
  :func:`resolve_mode`.

These are real branches behind real CLI output -- not coverage padding.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ai_engineering.policy import mode_dispatch


def test_banner_returns_empty_for_regulated_default() -> None:
    """No banner is emitted when both manifest and resolved are regulated."""
    text = mode_dispatch.banner_for_mode("regulated", manifest_mode="regulated")
    assert text == ""


def test_banner_announces_escalation_with_reason() -> None:
    """Escalated banner includes the structured reason snippet."""
    text = mode_dispatch.banner_for_mode(
        "regulated",
        manifest_mode="prototyping",
        reason="protected branch 'main'",
    )
    assert "REGULATED MODE" in text
    assert "escalated from prototyping" in text
    assert "protected branch 'main'" in text


def test_banner_uses_default_reason_when_not_provided() -> None:
    """Escalated banner falls back to a generic reason on missing label."""
    text = mode_dispatch.banner_for_mode("regulated", manifest_mode="prototyping")
    assert "branch / CI escalation" in text


def test_banner_warns_when_prototyping_honored() -> None:
    """Honored prototyping mode prints the Tier 2 warning banner."""
    text = mode_dispatch.banner_for_mode("prototyping", manifest_mode="prototyping")
    assert "PROTOTYPING MODE" in text
    assert "Tier 2 governance checks skipped" in text


def test_explain_reason_prefers_ci_sentinel(tmp_path: Path) -> None:
    """``CI=true`` is reported as the escalation reason."""
    reason = mode_dispatch.explain_escalation_reason(tmp_path, env={"CI": "true"})
    assert reason is not None
    assert "CI environment" in reason


def test_explain_reason_reports_push_target(tmp_path: Path) -> None:
    """``AIENG_PUSH_TARGET_REF`` pointing at main is surfaced verbatim."""
    reason = mode_dispatch.explain_escalation_reason(
        tmp_path, env={"AIENG_PUSH_TARGET_REF": "refs/heads/main"}
    )
    assert reason is not None
    assert "push target" in reason
    assert "refs/heads/main" in reason


def test_explain_reason_reports_detached_head(tmp_path: Path) -> None:
    """When git symbolic-ref returns ``None``, reason is ``detached HEAD``."""
    with patch.object(mode_dispatch, "_current_branch_or_none", return_value=None):
        reason = mode_dispatch.explain_escalation_reason(tmp_path, env={})
    assert reason == "detached HEAD"


def test_explain_reason_reports_protected_branch(tmp_path: Path) -> None:
    """A protected branch name is wrapped in single quotes for display."""
    with patch.object(mode_dispatch, "_current_branch_or_none", return_value="main"):
        reason = mode_dispatch.explain_escalation_reason(tmp_path, env={})
    assert reason == "protected branch 'main'"


def test_explain_reason_returns_none_for_feature_branch(tmp_path: Path) -> None:
    """Non-protected branches mean no escalation reason."""
    with patch.object(mode_dispatch, "_current_branch_or_none", return_value="feat/x"):
        reason = mode_dispatch.explain_escalation_reason(tmp_path, env={})
    assert reason is None


def test_release_glob_branch_escalates_to_regulated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``release/2026-Q3`` matches the ``release/*`` glob and escalates.

    Validates that the ``fnmatch`` path inside :func:`_branch_is_protected`
    triggers the conservative escalation even when the manifest opts into
    prototyping mode.
    """
    state_dir = tmp_path / ".ai-engineering"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "manifest.yml").write_text(
        "schemaVersion: 1\ngates:\n  mode: prototyping\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    with patch.object(mode_dispatch, "_current_branch_or_none", return_value="release/2026-Q3"):
        result = mode_dispatch.resolve_mode(tmp_path, env={})
    assert result == "regulated"


def test_resolve_mode_honors_manifest_when_no_escalation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """With no escalation triggers, the manifest declaration wins."""
    state_dir = tmp_path / ".ai-engineering"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "manifest.yml").write_text(
        "schemaVersion: 1\ngates:\n  mode: prototyping\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    with patch.object(mode_dispatch, "_current_branch_or_none", return_value="feat/free-of-glob"):
        result = mode_dispatch.resolve_mode(tmp_path, env={})
    assert result == "prototyping"


def test_resolve_mode_falls_back_to_regulated_on_manifest_load_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If ``load_manifest_config`` raises, ``_read_manifest_mode`` returns regulated."""
    monkeypatch.chdir(tmp_path)
    with (
        patch.object(mode_dispatch, "_current_branch_or_none", return_value="feat/safe"),
        patch.object(mode_dispatch, "load_manifest_config", side_effect=RuntimeError("broken")),
    ):
        result = mode_dispatch.resolve_mode(tmp_path, env={})
    assert result == "regulated"
