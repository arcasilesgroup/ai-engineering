"""spec-184 Phase B: update() wiring to advance_framework_version (ordering)."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from ai_engineering.updater.service import update


def _minimal_manifest(root: Path) -> None:
    d = root / ".ai-engineering"
    d.mkdir(parents=True, exist_ok=True)
    (d / "manifest.yml").write_text('framework_version: "0.0.1"\nname: p\n', encoding="utf-8")


def test_no_advance_on_rollback(tmp_path: Path) -> None:
    """A rolled-back apply must NOT bump framework_version (else drift is falsely
    silenced while the files stayed old)."""
    _minimal_manifest(tmp_path)
    failed_run = SimpleNamespace(
        plan=SimpleNamespace(payload=object()),
        apply_result=object(),
        verification=SimpleNamespace(passed=False, errors=["boom"]),
        rolled_back=True,
    )
    with (
        patch("ai_engineering.updater.service.ResourceReconciler") as rf,
        patch("ai_engineering.updater.framework_version_advance.advance_framework_version") as adv,
        pytest.raises(RuntimeError, match="rolled back changes"),
    ):
        rf.return_value.run.return_value = failed_run
        update(tmp_path, dry_run=False)
    adv.assert_not_called()


def test_advances_on_verified_apply(tmp_path: Path) -> None:
    _minimal_manifest(tmp_path)
    ok_run = SimpleNamespace(
        plan=SimpleNamespace(payload=object()),
        apply_result=SimpleNamespace(payload=object()),
        verification=SimpleNamespace(passed=True, errors=[]),
        rolled_back=False,
    )
    fake_payload = SimpleNamespace(result=SimpleNamespace(hook_migration=None))
    with (
        patch("ai_engineering.updater.service.ResourceReconciler") as rf,
        patch(
            "ai_engineering.updater.service._UpdateAdapter._coerce_apply_payload",
            return_value=fake_payload,
        ),
        patch("ai_engineering.updater.framework_version_advance.advance_framework_version") as adv,
    ):
        rf.return_value.run.return_value = ok_run
        update(tmp_path, dry_run=False)
    adv.assert_called_once()
    assert adv.call_args.kwargs.get("dry_run") is False


def test_dry_run_computes_advance_plan(tmp_path: Path) -> None:
    _minimal_manifest(tmp_path)
    dry_run_obj = SimpleNamespace(plan=SimpleNamespace(payload=object()))
    fake_payload = SimpleNamespace(result=SimpleNamespace(hook_migration=None))
    with (
        patch("ai_engineering.updater.service.ResourceReconciler") as rf,
        patch(
            "ai_engineering.updater.service._UpdateAdapter._coerce_plan_payload",
            return_value=fake_payload,
        ),
        patch("ai_engineering.updater.framework_version_advance.advance_framework_version") as adv,
    ):
        rf.return_value.run.return_value = dry_run_obj
        update(tmp_path, dry_run=True)
    adv.assert_called_once()
    assert adv.call_args.kwargs.get("dry_run") is True


def test_atomic_write_leaves_no_temp_files(tmp_path: Path) -> None:
    """spec-184 remediation: update_manifest_field writes atomically — no
    leftover .manifest-*.tmp after a successful advance."""
    from ai_engineering import __version__
    from ai_engineering.updater.framework_version_advance import advance_framework_version

    _minimal_manifest(tmp_path)
    advance_framework_version(tmp_path, dry_run=False)
    leftovers = list((tmp_path / ".ai-engineering").glob(".manifest-*.tmp"))
    assert leftovers == []
    assert f'"{__version__}"' in (tmp_path / ".ai-engineering" / "manifest.yml").read_text()
