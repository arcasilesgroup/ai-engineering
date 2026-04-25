"""RED tests for spec-101 T-0.15 / T-0.16 (R-10).

Covers the legacy ``install-state.json`` migration owned by
``state/service.py::load_install_state``:

- Loading a legacy state file (missing ``required_tools_state`` key, OR with
  any tool record missing the ``os_release`` field) MUST:
  1. Rename the file to ``install-state.json.legacy-<ISO-ts>``.
  2. Write a fresh modern state at the original path.
  3. Emit a ``state_migration`` event via the existing observability surface.
  4. Return the fresh ``InstallState`` to the caller.
- The legacy file is preserved read-only as the rollback path.
- Modern state files pass through unchanged (no migration, no rename).
- Migration is idempotent: running the loader twice does not migrate twice.

These tests intentionally fail until T-0.16 lands the migration logic.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from ai_engineering.state.io import read_ndjson_entries
from ai_engineering.state.models import FrameworkEvent, InstallState
from ai_engineering.state.observability import framework_events_path
from ai_engineering.state.service import load_install_state

# Windows-safe timestamp -- ``:`` is illegal in NTFS filenames, so the
# legacy backup uses ``-`` separators between H/M/S. Both expressions
# remain ISO-like (``YYYY-MM-DDTHH-MM-SS``).
_LEGACY_TS_RE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}")
_LEGACY_FILENAME_RE = re.compile(
    r"^install-state\.json\.legacy-\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2}$"
)


def _write_manifest(project_root: Path) -> None:
    """Drop a minimal manifest.yml so observability emitters can resolve the project name."""
    manifest_path = project_root / ".ai-engineering" / "manifest.yml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("name: spec-101-migration-test\n", encoding="utf-8")


def _state_dir(project_root: Path) -> Path:
    state_dir = project_root / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)
    return state_dir


def _legacy_pre_spec101_payload() -> dict[str, object]:
    """Return a JSON payload representing pre-spec-101 install state.

    Notably absent: the ``required_tools_state`` key (added in T-0.14).
    """
    return {
        "schema_version": "2.0",
        "installed_at": "2026-03-25T10:00:00Z",
        "vcs_provider": "github",
        "tooling": {"gh": {"installed": True, "authenticated": True}},
        "platforms": {},
        "branch_policy": {"applied": False, "mode": "api"},
        "operational_readiness": {"status": "pending", "pending_steps": []},
        "release": {"last_version": "", "last_released_at": None},
    }


def _legacy_with_tool_record_missing_os_release() -> dict[str, object]:
    """Return a JSON payload with ``required_tools_state`` but a record missing ``os_release``."""
    return {
        "schema_version": "2.0",
        "installed_at": "2026-03-25T10:00:00Z",
        "vcs_provider": "github",
        "tooling": {},
        "platforms": {},
        "branch_policy": {"applied": False, "mode": "api"},
        "operational_readiness": {"status": "pending", "pending_steps": []},
        "release": {"last_version": "", "last_released_at": None},
        "required_tools_state": {
            "gh": {
                "state": "installed",
                "mechanism": "brew",
                "version": "2.62.0",
                "verified_at": "2026-03-25T10:00:00Z",
                # NOTE: os_release intentionally missing.
            }
        },
    }


def _modern_payload() -> dict[str, object]:
    """Return a JSON payload that already conforms to the spec-101 schema."""
    return {
        "schema_version": "2.0",
        "installed_at": "2026-04-24T10:00:00Z",
        "vcs_provider": "github",
        "tooling": {},
        "platforms": {},
        "branch_policy": {"applied": False, "mode": "api"},
        "operational_readiness": {"status": "pending", "pending_steps": []},
        "release": {"last_version": "", "last_released_at": None},
        "required_tools_state": {
            "gh": {
                "state": "installed",
                "mechanism": "brew",
                "version": "2.62.0",
                "verified_at": "2026-03-25T10:00:00Z",
                "os_release": "14.4",
            }
        },
        "python_env_mode_recorded": "uv-tool",
    }


# -- Tests ---------------------------------------------------------------


class TestLegacyMissingRequiredToolsState:
    """Legacy file lacking the new ``required_tools_state`` key triggers migration."""

    def test_legacy_missing_required_tools_state_migrates(self, tmp_path: Path) -> None:
        # Arrange
        _write_manifest(tmp_path)
        state_dir = _state_dir(tmp_path)
        original = state_dir / "install-state.json"
        legacy_payload = _legacy_pre_spec101_payload()
        original.write_text(json.dumps(legacy_payload), encoding="utf-8")

        # Act
        result = load_install_state(state_dir)

        # Assert: original path now contains a fresh modern state
        assert isinstance(result, InstallState)
        assert result.required_tools_state == {}
        assert result.python_env_mode_recorded is None

        # Assert: a sibling renamed file exists with the canonical legacy suffix
        legacy_files = [
            p for p in state_dir.iterdir() if p.name.startswith("install-state.json.legacy-")
        ]
        assert len(legacy_files) == 1
        legacy_file = legacy_files[0]
        assert _LEGACY_FILENAME_RE.match(legacy_file.name) is not None
        match = _LEGACY_TS_RE.search(legacy_file.name)
        assert match is not None, f"timestamp not found in {legacy_file.name}"

        # Assert: original install-state.json now holds the freshly-written state
        assert original.exists()
        rewritten = json.loads(original.read_text(encoding="utf-8"))
        assert "required_tools_state" in rewritten or rewritten == {}


class TestLegacyToolRecordMissingOsRelease:
    """A tool record missing ``os_release`` triggers the same migration."""

    def test_missing_os_release_on_tool_record_migrates(self, tmp_path: Path) -> None:
        # Arrange
        _write_manifest(tmp_path)
        state_dir = _state_dir(tmp_path)
        original = state_dir / "install-state.json"
        original.write_text(
            json.dumps(_legacy_with_tool_record_missing_os_release()),
            encoding="utf-8",
        )

        # Act
        result = load_install_state(state_dir)

        # Assert
        assert isinstance(result, InstallState)
        assert result.required_tools_state == {}

        legacy_files = [
            p for p in state_dir.iterdir() if p.name.startswith("install-state.json.legacy-")
        ]
        assert len(legacy_files) == 1
        assert _LEGACY_FILENAME_RE.match(legacy_files[0].name) is not None


class TestModernStatePassesThrough:
    """A file already conforming to the modern schema is loaded as-is."""

    def test_modern_state_no_migration(self, tmp_path: Path) -> None:
        # Arrange
        _write_manifest(tmp_path)
        state_dir = _state_dir(tmp_path)
        original = state_dir / "install-state.json"
        modern_payload = _modern_payload()
        original.write_text(json.dumps(modern_payload), encoding="utf-8")

        # Act
        result = load_install_state(state_dir)

        # Assert: file is NOT renamed; no .legacy-* sibling is created
        legacy_files = [
            p for p in state_dir.iterdir() if p.name.startswith("install-state.json.legacy-")
        ]
        assert legacy_files == []

        # Assert: returned state matches the written content
        assert result.vcs_provider == "github"
        assert "gh" in result.required_tools_state
        assert result.required_tools_state["gh"].mechanism == "brew"
        assert result.required_tools_state["gh"].os_release == "14.4"


class TestLegacyContentPreservedReadOnly:
    """The renamed ``.legacy-<ts>`` file preserves the original JSON byte-for-byte."""

    def test_legacy_file_content_is_preserved(self, tmp_path: Path) -> None:
        # Arrange
        _write_manifest(tmp_path)
        state_dir = _state_dir(tmp_path)
        original = state_dir / "install-state.json"
        legacy_payload = _legacy_pre_spec101_payload()
        original_text = json.dumps(legacy_payload, sort_keys=True)
        original.write_text(original_text, encoding="utf-8")

        # Act
        load_install_state(state_dir)

        # Assert
        legacy_files = [
            p for p in state_dir.iterdir() if p.name.startswith("install-state.json.legacy-")
        ]
        assert len(legacy_files) == 1
        preserved = legacy_files[0].read_text(encoding="utf-8")
        assert preserved == original_text


class TestMigrationLogged:
    """The migration emits a ``state_migration`` framework event."""

    def test_migration_emits_state_migration_event(self, tmp_path: Path) -> None:
        # Arrange
        _write_manifest(tmp_path)
        state_dir = _state_dir(tmp_path)
        original = state_dir / "install-state.json"
        original.write_text(
            json.dumps(_legacy_pre_spec101_payload()),
            encoding="utf-8",
        )

        # Act
        load_install_state(state_dir)

        # Assert: framework-events.ndjson contains the migration event
        events = read_ndjson_entries(framework_events_path(tmp_path), FrameworkEvent)
        migration_events = [
            event
            for event in events
            if event.detail.get("operation") == "state_migration" or event.kind == "state_migration"
        ]
        assert len(migration_events) == 1, (
            f"expected exactly one state_migration event, got {len(migration_events)} "
            f"in {[e.kind for e in events]}"
        )
        evt = migration_events[0]
        legacy_files = [
            p for p in state_dir.iterdir() if p.name.startswith("install-state.json.legacy-")
        ]
        assert len(legacy_files) == 1
        legacy_filename = legacy_files[0].name
        # The event detail must reference the renamed legacy filename and an ISO timestamp.
        detail_str = json.dumps(evt.detail)
        assert legacy_filename in detail_str
        assert _LEGACY_TS_RE.search(detail_str) is not None


class TestMigrationIsIdempotent:
    """A second load on already-migrated state does not migrate again."""

    def test_second_load_is_noop(self, tmp_path: Path) -> None:
        # Arrange
        _write_manifest(tmp_path)
        state_dir = _state_dir(tmp_path)
        original = state_dir / "install-state.json"
        original.write_text(
            json.dumps(_legacy_pre_spec101_payload()),
            encoding="utf-8",
        )

        # Act -- first load triggers migration
        load_install_state(state_dir)
        legacy_after_first = sorted(
            p.name for p in state_dir.iterdir() if p.name.startswith("install-state.json.legacy-")
        )
        assert len(legacy_after_first) == 1

        # Act -- second load should be a no-op rename-wise
        result_second = load_install_state(state_dir)

        # Assert: still exactly one .legacy-* file, fresh state returned
        legacy_after_second = sorted(
            p.name for p in state_dir.iterdir() if p.name.startswith("install-state.json.legacy-")
        )
        assert legacy_after_second == legacy_after_first
        assert isinstance(result_second, InstallState)
        assert result_second.required_tools_state == {}
