"""Tests for version/models.py and version/checker.py.

Covers:
- Model parsing (VersionStatus, VersionEntry, VersionRegistry).
- check_version for all lifecycle states (current, outdated, deprecated, eol, unknown).
- find_latest_version and find_version_entry helpers.
- Semver comparison via tuple parsing.
- load_registry from file and bundled package data.
- Graceful error handling (missing/corrupt registry).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.version.checker import (
    _parse_semver,
    check_version,
    find_latest_version,
    find_version_entry,
    load_registry,
)
from ai_engineering.version.models import VersionEntry, VersionRegistry, VersionStatus

# ---------------------------------------------------------------------------
# Model parsing
# ---------------------------------------------------------------------------


class TestVersionModels:
    """Tests for Pydantic model parsing."""

    def test_version_status_values(self) -> None:
        assert VersionStatus.CURRENT == "current"
        assert VersionStatus.SUPPORTED == "supported"
        assert VersionStatus.DEPRECATED == "deprecated"
        assert VersionStatus.EOL == "eol"

    def test_version_entry_minimal(self) -> None:
        entry = VersionEntry(version="1.0.0", status=VersionStatus.CURRENT, released="2026-01-01")
        assert entry.version == "1.0.0"
        assert entry.status == VersionStatus.CURRENT
        assert entry.deprecated_reason is None

    def test_version_entry_with_deprecation(self) -> None:
        entry = VersionEntry.model_validate(
            {
                "version": "0.9.0",
                "status": "deprecated",
                "released": "2025-06-01",
                "deprecatedReason": "CVE-2025-1234",
            }
        )
        assert entry.deprecated_reason == "CVE-2025-1234"

    def test_version_registry_parsing(self) -> None:
        data = {
            "schemaVersion": "1.0",
            "versions": [
                {"version": "1.0.0", "status": "current", "released": "2026-01-01"},
                {"version": "0.9.0", "status": "supported", "released": "2025-06-01"},
            ],
        }
        registry = VersionRegistry.model_validate(data)
        assert len(registry.versions) == 2
        assert registry.schema_version == "1.0"

    def test_empty_registry(self) -> None:
        registry = VersionRegistry.model_validate({"schemaVersion": "1.0", "versions": []})
        assert len(registry.versions) == 0


# ---------------------------------------------------------------------------
# Semver parsing
# ---------------------------------------------------------------------------


class TestSemverParsing:
    """Tests for _parse_semver helper."""

    def test_basic_parse(self) -> None:
        assert _parse_semver("1.2.3") == (1, 2, 3)

    def test_comparison(self) -> None:
        assert _parse_semver("1.0.0") > _parse_semver("0.9.0")
        assert _parse_semver("0.2.0") > _parse_semver("0.1.0")
        assert _parse_semver("0.1.1") > _parse_semver("0.1.0")

    def test_equality(self) -> None:
        assert _parse_semver("1.0.0") == _parse_semver("1.0.0")

    def test_invalid_raises(self) -> None:
        with pytest.raises(ValueError):
            _parse_semver("not.a.version")


# ---------------------------------------------------------------------------
# load_registry
# ---------------------------------------------------------------------------


class TestLoadRegistry:
    """Tests for load_registry function."""

    def test_loads_bundled_registry(self) -> None:
        registry = load_registry()
        assert registry is not None
        assert len(registry.versions) >= 1

    def test_loads_from_custom_path(self, tmp_path: Path) -> None:
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(
            json.dumps(
                {
                    "schemaVersion": "1.0",
                    "versions": [
                        {"version": "2.0.0", "status": "current", "released": "2026-06-01"}
                    ],
                }
            )
        )
        registry = load_registry(reg_file)
        assert registry is not None
        assert registry.versions[0].version == "2.0.0"

    def test_returns_none_on_missing_file(self, tmp_path: Path) -> None:
        result = load_registry(tmp_path / "nonexistent.json")
        assert result is None

    def test_returns_none_on_corrupt_json(self, tmp_path: Path) -> None:
        reg_file = tmp_path / "registry.json"
        reg_file.write_text("{invalid json")
        result = load_registry(reg_file)
        assert result is None

    def test_returns_none_on_invalid_schema(self, tmp_path: Path) -> None:
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(json.dumps({"schemaVersion": "1.0", "versions": "not-a-list"}))
        result = load_registry(reg_file)
        assert result is None


# ---------------------------------------------------------------------------
# find_version_entry
# ---------------------------------------------------------------------------


class TestFindVersionEntry:
    """Tests for find_version_entry helper."""

    def test_finds_existing_version(self) -> None:
        registry = _make_registry(
            ("1.0.0", "current"), ("0.9.0", "supported"), ("0.8.0", "deprecated")
        )
        entry = find_version_entry(registry, "0.9.0")
        assert entry is not None
        assert entry.version == "0.9.0"
        assert entry.status == VersionStatus.SUPPORTED

    def test_returns_none_for_missing_version(self) -> None:
        registry = _make_registry(("1.0.0", "current"))
        assert find_version_entry(registry, "0.0.1") is None


# ---------------------------------------------------------------------------
# find_latest_version
# ---------------------------------------------------------------------------


class TestFindLatestVersion:
    """Tests for find_latest_version helper."""

    def test_finds_highest_version(self) -> None:
        registry = _make_registry(
            ("0.8.0", "deprecated"), ("1.0.0", "current"), ("0.9.0", "supported")
        )
        assert find_latest_version(registry) == "1.0.0"

    def test_returns_none_for_empty_registry(self) -> None:
        registry = VersionRegistry(versions=[])
        assert find_latest_version(registry) is None

    def test_single_version(self) -> None:
        registry = _make_registry(("0.1.0", "current"))
        assert find_latest_version(registry) == "0.1.0"


# ---------------------------------------------------------------------------
# check_version
# ---------------------------------------------------------------------------


class TestCheckVersion:
    """Tests for check_version — the main checker function."""

    def test_current_version(self) -> None:
        registry = _make_registry(("1.0.0", "current"))
        result = check_version("1.0.0", registry)
        assert result.is_current is True
        assert result.is_outdated is False
        assert result.is_deprecated is False
        assert result.is_eol is False
        assert result.status == VersionStatus.CURRENT
        assert "current" in result.message

    def test_outdated_version(self) -> None:
        registry = _make_registry(("1.0.0", "current"), ("0.9.0", "supported"))
        result = check_version("0.9.0", registry)
        assert result.is_outdated is True
        assert result.is_current is False
        assert result.latest == "1.0.0"
        assert "outdated" in result.message

    def test_deprecated_version(self) -> None:
        registry = _make_registry_with_deprecation(
            ("1.0.0", "current"),
            ("0.8.0", "deprecated", "CVE-2025-9999"),
        )
        result = check_version("0.8.0", registry)
        assert result.is_deprecated is True
        assert result.is_current is False
        assert "deprecated" in result.message
        assert "CVE-2025-9999" in result.message

    def test_eol_version(self) -> None:
        registry = _make_registry(("1.0.0", "current"), ("0.7.0", "eol"))
        result = check_version("0.7.0", registry)
        assert result.is_eol is True
        assert "end-of-life" in result.message

    def test_unknown_version(self) -> None:
        registry = _make_registry(("1.0.0", "current"))
        result = check_version("99.99.99", registry)
        assert result.status is None
        assert result.is_current is False
        assert "not found" in result.message

    def test_no_registry(self, tmp_path: Path) -> None:
        result = check_version("0.1.0", registry_path=tmp_path / "nonexistent.json")
        assert result.status is None
        assert "unavailable" in result.message

    def test_deprecated_without_reason(self) -> None:
        registry = _make_registry(("1.0.0", "current"), ("0.8.0", "deprecated"))
        result = check_version("0.8.0", registry)
        assert result.is_deprecated is True
        assert "security vulnerability" in result.message

    def test_loads_registry_from_path(self, tmp_path: Path) -> None:
        reg_file = tmp_path / "registry.json"
        reg_file.write_text(
            json.dumps(
                {
                    "schemaVersion": "1.0",
                    "versions": [
                        {"version": "0.1.0", "status": "current", "released": "2026-01-01"}
                    ],
                }
            )
        )
        result = check_version("0.1.0", registry_path=reg_file)
        assert result.is_current is True

    def test_check_result_is_frozen(self) -> None:
        registry = _make_registry(("1.0.0", "current"))
        result = check_version("1.0.0", registry)
        with pytest.raises(AttributeError):
            result.installed = "2.0.0"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_registry(*entries: tuple[str, str]) -> VersionRegistry:
    """Build a registry from (version, status) tuples."""
    return VersionRegistry(
        versions=[
            VersionEntry(version=v, status=VersionStatus(s), released="2026-01-01")
            for v, s in entries
        ]
    )


def _make_registry_with_deprecation(
    *entries: tuple[str, str] | tuple[str, str, str],
) -> VersionRegistry:
    """Build a registry from (version, status[, reason]) tuples."""
    versions = []
    for entry in entries:
        v, s = entry[0], entry[1]
        reason = entry[2] if len(entry) > 2 else None
        versions.append(
            VersionEntry(
                version=v,
                status=VersionStatus(s),
                released="2026-01-01",
                deprecated_reason=reason,
            )
        )
    return VersionRegistry(versions=versions)
