"""RED skeleton for spec-105 Phase 5 — CI environment escalation override.

Covers G-3 (CI portion): ``resolve_mode`` checks three CI sentinel env vars
in order — any one being truthy forces ``regulated`` regardless of manifest
declaration:

1. ``CI=true`` — POSIX-canonical CI marker (used by every major runner).
2. ``GITHUB_ACTIONS=true`` — GitHub Actions specific (often present without
   the bare ``CI`` variable in matrix strategy steps).
3. ``TF_BUILD=True`` — Azure Pipelines specific (note PascalCase value).

Status: RED — ``policy/mode_dispatch.py`` does not exist yet (lands in
Phase 5 T-5.4 / T-5.6).
Marker: ``@pytest.mark.spec_105_red`` — excluded by default CI run.
Will be unmarked in Phase 5 (T-5.19).

Lesson learned in Phase 1: deferred imports of the target wiring keep
pytest collection green while modules are still missing.
"""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.spec_105_red


def _seed_manifest_prototyping(root: Path) -> None:
    """Write a manifest declaring ``prototyping`` so escalation is observable."""
    state_dir = root / ".ai-engineering"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "manifest.yml").write_text(
        "schemaVersion: 1\ngates:\n  mode: prototyping\n",
        encoding="utf-8",
    )


def test_ci_true_forces_regulated_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``CI=true`` env var forces ``regulated`` even on a feat branch."""
    from unittest.mock import patch

    from ai_engineering.policy import mode_dispatch

    _seed_manifest_prototyping(tmp_path)
    monkeypatch.chdir(tmp_path)

    with patch("subprocess.check_output", return_value="feat/local-work\n"):
        result = mode_dispatch.resolve_mode(tmp_path, env={"CI": "true"})

    assert result == "regulated"


def test_github_actions_forces_regulated_mode(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``GITHUB_ACTIONS=true`` env var forces ``regulated`` mode.

    Some matrix-strategy steps set ``GITHUB_ACTIONS`` without the bare
    ``CI`` variable, so the dispatcher must inspect both.
    """
    from unittest.mock import patch

    from ai_engineering.policy import mode_dispatch

    _seed_manifest_prototyping(tmp_path)
    monkeypatch.chdir(tmp_path)

    with patch("subprocess.check_output", return_value="feat/local-work\n"):
        result = mode_dispatch.resolve_mode(tmp_path, env={"GITHUB_ACTIONS": "true"})

    assert result == "regulated"


def test_tf_build_forces_regulated_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """``TF_BUILD=True`` (Azure Pipelines) forces ``regulated`` mode.

    Note PascalCase ``True`` value is the Azure Pipelines convention; the
    dispatcher must accept any truthy spelling.
    """
    from unittest.mock import patch

    from ai_engineering.policy import mode_dispatch

    _seed_manifest_prototyping(tmp_path)
    monkeypatch.chdir(tmp_path)

    with patch("subprocess.check_output", return_value="feat/local-work\n"):
        result = mode_dispatch.resolve_mode(tmp_path, env={"TF_BUILD": "True"})

    assert result == "regulated"
