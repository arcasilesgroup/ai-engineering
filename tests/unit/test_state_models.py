"""Unit tests for system-managed state schemas."""

from __future__ import annotations

from ai_engineering.state.defaults import (
    decision_store_default,
    install_manifest_default,
    ownership_map_default,
    sources_lock_default,
)
from ai_engineering.state.models import (
    DecisionStore,
    InstallManifest,
    OwnershipMap,
    SourcesLock,
)


def test_install_manifest_default_validates() -> None:
    payload = install_manifest_default("0.1.0")
    model = InstallManifest.model_validate(payload)
    assert model.schemaVersion == "1.1"


def test_ownership_map_default_validates() -> None:
    payload = ownership_map_default()
    model = OwnershipMap.model_validate(payload)
    assert len(model.paths) >= 5


def test_sources_lock_default_validates() -> None:
    payload = sources_lock_default()
    model = SourcesLock.model_validate(payload)
    assert len(model.sources) == 2


def test_decision_store_default_validates() -> None:
    payload = decision_store_default()
    model = DecisionStore.model_validate(payload)
    assert model.decisions == []


def test_invalid_ownership_rule_fails_validation() -> None:
    payload = ownership_map_default()
    payload["paths"][0]["frameworkUpdate"] = "bad-value"
    try:
        OwnershipMap.model_validate(payload)
    except Exception:
        return
    raise AssertionError("Expected validation failure for invalid frameworkUpdate value")
