"""State service facade for ai-engineering state I/O.

Provides a single entry point for loading and saving state files,
replacing direct imports of ``state.io`` + ``state.models`` in CLI commands.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from ai_engineering.state.models import (
    DecisionStore,
    FrameworkCapabilitiesCatalog,
    FrameworkEvent,
    InstallState,
    OwnershipMap,
)

logger = logging.getLogger(__name__)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from ai_engineering.state.repository import DurableStateRepository


class StateService:
    """Facade for reading and writing ai-engineering state files."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._state_dir = project_root / ".ai-engineering" / "state"

    @property
    def state_dir(self) -> Path:
        """Return the state directory path."""
        return self._state_dir

    def _repository(self) -> DurableStateRepository:
        """Return the durable-state repository backing this compatibility facade."""
        # Delayed to avoid a module import cycle: repository imports install-state helpers below.
        from ai_engineering.state.repository import DurableStateRepository

        return DurableStateRepository(self._root)

    def load_decisions(self) -> DecisionStore:
        """Load the decision store."""
        return self._repository().load_decisions()

    def save_decisions(self, store: DecisionStore) -> None:
        """Save the decision store."""
        self._repository().save_decisions(store)

    def load_ownership(self) -> OwnershipMap:
        """Load the ownership map."""
        return self._repository().load_ownership()

    def append_framework_event(self, entry: FrameworkEvent) -> None:
        """Append an entry to the canonical framework event stream.

        Spec-110 D-110-03: writes ``prev_event_hash`` at the root of the
        emitted JSON object (sibling of ``kind`` / ``detail``) so the
        tamper-evident chain in ``audit_chain.iter_validate_chain`` finds
        the pointer at the canonical location. Delegates to the
        canonical writer in :mod:`ai_engineering.state.observability` so
        the chain-pointer logic stays single-sourced. Imported lazily to
        avoid a module-level cycle (``observability`` imports from
        ``state.io`` and ``state.models``).
        """
        from ai_engineering.state.observability import append_framework_event

        append_framework_event(self._root, entry)

    def save_framework_capabilities(self, catalog: FrameworkCapabilitiesCatalog) -> None:
        """Persist the canonical framework capability catalog."""
        self._repository().save_framework_capabilities(catalog)


# ---------------------------------------------------------------------------
# Free functions for InstallState I/O (spec-068)
# ---------------------------------------------------------------------------

_INSTALL_STATE_FILENAME = "install-state.json"
_LEGACY_AUDIT_LOG_FILENAME = "audit-log.ndjson"


def load_install_state(state_dir: Path) -> InstallState:
    """Load ``install-state.json`` from *state_dir*, returning defaults if absent.

    Follows the same pattern as ``CredentialService.load_tools_state()``:
    file-present -> parse + validate, file-absent -> sensible defaults.

    When the file is structurally legacy (per spec-101 R-10) -- missing the
    ``required_tools_state`` key OR carrying a tool record without the
    ``os_release`` field -- it is renamed to
    ``install-state.json.legacy-<ISO-ts>``, a fresh modern state is written
    in its place, and a ``state_migration`` framework event is emitted.
    Caller receives the fresh state. The renamed file is preserved
    read-only as the rollback path.

    Wave 23 fix: the fresh state preserves carry-forward keys
    (``tooling``, ``platforms``, ``branch_policy``,
    ``operational_readiness``, ``release``, ``vcs_provider``,
    ``ai_providers``, ``installed_at``) from the legacy payload so
    downstream consumers (VCS factory's ``tooling.gh.mode`` lookup, the
    breaking-banner persistence, etc.) keep operating on the user's
    real configuration. Only the spec-101 fields (``required_tools_state``,
    ``python_env_mode_recorded``) are reset to defaults.

    Args:
        state_dir: The ``.ai-engineering/state/`` directory.

    Returns:
        Parsed ``InstallState``, or a default instance when the file
        does not exist.
    """
    path = state_dir / _INSTALL_STATE_FILENAME
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and _is_legacy_install_state(data):
            data = _migrate_legacy_install_state(path, data)
        return InstallState.model_validate(data)
    return InstallState()


def _is_legacy_install_state(data: dict[str, Any]) -> bool:
    """Return ``True`` when *data* is a pre-spec-101 ``install-state.json`` payload.

    Two structural signals trigger migration (R-10):

    1. The top-level ``required_tools_state`` key is absent entirely. The
       Pydantic field defaults to ``{}``, but the *absence* of the key is the
       legacy marker -- a value of ``{}`` written by a modern installer is
       fine.
    2. ``required_tools_state`` is present but at least one tool record
       lacks the ``os_release`` key (added in T-0.14 alongside the field).
       Records with ``os_release: null`` are valid; only records that
       structurally lack the key are legacy.
    """
    if "required_tools_state" not in data:
        return True

    records = data.get("required_tools_state")
    if not isinstance(records, dict):
        return False

    return any(
        isinstance(record, dict) and "os_release" not in record for record in records.values()
    )


# Top-level keys carried forward from a legacy payload into the fresh state.
# These are stable fields that pre-date spec-101 and remain part of
# :class:`InstallState`; they are preserved so consumers of legacy state
# (e.g. ``vcs.factory.get_provider`` reading ``tooling.gh.mode``) keep
# operating on the user's real configuration after a schema bump.
_LEGACY_CARRY_FORWARD_KEYS: tuple[str, ...] = (
    "schema_version",
    "installed_at",
    "vcs_provider",
    "ai_providers",
    "tooling",
    "platforms",
    "branch_policy",
    "operational_readiness",
    "release",
    "breaking_banner_seen",
)


def _carry_forward_legacy_fields(fresh: dict[str, Any], legacy: dict[str, Any]) -> dict[str, Any]:
    """Overlay legacy values for stable carry-forward keys onto a fresh dict.

    Only keys listed in :data:`_LEGACY_CARRY_FORWARD_KEYS` are copied; the
    spec-101-specific fields (``required_tools_state``,
    ``python_env_mode_recorded``) intentionally retain their defaults. A
    missing or null legacy value falls through to the fresh default.
    """
    merged = dict(fresh)
    for key in _LEGACY_CARRY_FORWARD_KEYS:
        if key in legacy and legacy[key] is not None:
            merged[key] = legacy[key]
    return merged


def _migrate_legacy_install_state(path: Path, data: dict[str, Any]) -> dict[str, Any]:
    """Rename a legacy ``install-state.json`` and return a fresh state dict.

    Steps:

    1. Generate an ISO-formatted UTC timestamp (``YYYY-MM-DDTHH:MM:SS``).
    2. Rename *path* to ``<path>.legacy-<ts>`` -- the legacy bytes are
       preserved verbatim under the new name as the rollback path.
    3. Build a fresh default ``InstallState`` and overlay carry-forward
       fields (``tooling``, ``platforms``, ``vcs_provider``, ...) from the
       legacy payload so downstream consumers keep their configuration.
       Only the spec-101 fields (``required_tools_state``,
       ``python_env_mode_recorded``) are reset to defaults.
    4. Write the merged dict to the original path so subsequent reads see
       a modern, schema-conformant file.
    5. Emit a ``framework_operation`` event with ``operation =
       "state_migration"`` referencing the legacy filename and timestamp.
    6. Return the merged state dict so the caller can complete validation
       without a second filesystem read.

    Args:
        path: The original ``install-state.json`` path being migrated.
        data: The parsed legacy JSON payload (used only for diagnostics).

    Returns:
        Dict shape of a fresh ``InstallState`` ready for ``model_validate``,
        with carry-forward fields populated from *data*.
    """
    # Windows reserves ``:`` in filenames (see WinAPI naming rules), so the
    # legacy backup uses ``-`` between H/M/S rather than the canonical ISO
    # ``T`` + ``:`` form. The bytes still represent a UTC timestamp; only
    # the on-disk filename changes shape.
    timestamp = datetime.now(tz=UTC).strftime("%Y-%m-%dT%H-%M-%S")
    legacy_path = path.with_name(f"{path.name}.legacy-{timestamp}")
    path.rename(legacy_path)

    fresh_state = InstallState()
    fresh_dict = fresh_state.model_dump(mode="json")
    merged_dict = _carry_forward_legacy_fields(fresh_dict, data)

    # Re-validate the merged payload to ensure carry-forward fields parse
    # cleanly under the modern schema; if they don't, fall back to the
    # plain fresh state so the install does not break on bad legacy data.
    try:
        merged_state = InstallState.model_validate(merged_dict)
        merged_dict = merged_state.model_dump(mode="json")
        path.write_text(
            merged_state.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        merged_dict = fresh_dict
        path.write_text(
            fresh_state.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )

    logger.info(
        "Migrated legacy install-state.json: renamed to %s and wrote fresh state",
        legacy_path.name,
    )

    # Emit observability event. Imported lazily to avoid module-level cycles
    # with state.observability (which itself imports from state.io / models).
    try:
        from ai_engineering.state.observability import emit_framework_operation

        # state_dir layout: <project_root>/.ai-engineering/state/
        project_root = path.parent.parent.parent
        emit_framework_operation(
            project_root,
            operation="state_migration",
            component="state.service",
            source="state.service.load_install_state",
            metadata={
                "legacy_filename": legacy_path.name,
                "legacy_timestamp": timestamp,
                "trigger": _legacy_trigger_reason(data),
            },
        )
    except Exception:  # pragma: no cover - observability is fail-open
        logger.debug("Failed to emit state_migration event", exc_info=True)

    return merged_dict


def _legacy_trigger_reason(data: dict[str, Any]) -> str:
    """Classify which structural signal triggered the migration."""
    if "required_tools_state" not in data:
        return "missing_required_tools_state_key"
    return "tool_record_missing_os_release"


def save_install_state(state_dir: Path, state: InstallState) -> None:
    """Persist *state* to ``install-state.json`` in *state_dir*.

    Creates *state_dir* (and parents) when it does not yet exist.

    Args:
        state_dir: The ``.ai-engineering/state/`` directory.
        state: The ``InstallState`` model to write.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / _INSTALL_STATE_FILENAME
    path.write_text(
        state.model_dump_json(indent=2) + "\n",
        encoding="utf-8",
    )
    logger.debug("install-state.json written to %s", path)


def legacy_audit_log_path(project_root: Path) -> Path:
    """Return the legacy audit-log path retained only for cleanup."""
    return project_root / ".ai-engineering" / "state" / _LEGACY_AUDIT_LOG_FILENAME


def remove_legacy_audit_log(project_root: Path) -> bool:
    """Delete the legacy audit-log if present.

    Returns ``True`` when a file was removed and ``False`` otherwise.
    """
    path = legacy_audit_log_path(project_root)
    if not path.exists():
        return False
    path.unlink()
    logger.debug("Removed legacy audit log at %s", path)
    return True
