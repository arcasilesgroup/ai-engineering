"""Unit tests for hook helper runtime classification."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.hooks.asset_runtime import (
    HookAssetRuntimeClass,
    classify_hook_runtime_asset,
    list_hook_runtime_assets,
    validate_hook_runtime_asset_registry,
)


def test_all_packaged_hook_helpers_are_classified() -> None:
    validation = validate_hook_runtime_asset_registry()

    assert validation.passed
    assert validation.missing_classifications == ()
    assert validation.stale_classifications == ()


def test_stdlib_mirrors_have_packaged_counterparts_and_are_not_reducible() -> None:
    mirrors = [
        asset
        for asset in list_hook_runtime_assets()
        if asset.runtime_class == HookAssetRuntimeClass.STDLIB_MIRROR
    ]

    assert {asset.relative_path.name for asset in mirrors} == {
        "audit.py",
        "hook-common.py",
        "instincts.py",
        "observability.py",
    }
    assert all(asset.packaged_counterpart for asset in mirrors)
    assert all(asset.import_policy == "stdlib-only" for asset in mirrors)
    assert not any(asset.is_reducible_duplicate for asset in mirrors)


def test_classify_hook_runtime_asset_normalizes_paths() -> None:
    asset = classify_hook_runtime_asset(Path("scripts/hooks/_lib/hook_context.py"))

    assert asset is not None
    assert asset.runtime_class == HookAssetRuntimeClass.RUNTIME_NATIVE
    assert asset.import_policy == "stdlib-only"


def test_unknown_hook_runtime_asset_is_unclassified() -> None:
    assert classify_hook_runtime_asset(Path("scripts/hooks/_lib/unknown.py")) is None
