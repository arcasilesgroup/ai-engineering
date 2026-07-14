"""spec-184 Phase A: field-level manifest ownership resolver."""

from __future__ import annotations

from ai_engineering.config.manifest_ownership import (
    FRAMEWORK_WRITABLE_KEYS,
    is_framework_owned_manifest_key,
    is_framework_writable_manifest_key,
)


def test_framework_owned_classification() -> None:
    for key in ("framework_version", "schema_version", "skills", "agents"):
        assert is_framework_owned_manifest_key(key), key
    for key in ("providers", "surfaces", "quality", "gates", "telemetry", "work_items"):
        assert not is_framework_owned_manifest_key(key), key


def test_unknown_key_defaults_to_team_owned() -> None:
    assert not is_framework_owned_manifest_key("totally-unknown-key")


def test_v1_writable_is_framework_version_only() -> None:
    assert frozenset({"framework_version"}) == FRAMEWORK_WRITABLE_KEYS
    assert is_framework_writable_manifest_key("framework_version")
    # name/version are classified framework-owned but are user identity/release
    # and must NEVER be auto-written.
    for key in ("name", "version"):
        assert is_framework_owned_manifest_key(key), key
        assert not is_framework_writable_manifest_key(key), key
    # user config: neither owned nor writable.
    for key in ("providers", "surfaces"):
        assert not is_framework_writable_manifest_key(key), key
