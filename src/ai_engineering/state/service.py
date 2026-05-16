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

    def load_framework_capabilities(self) -> FrameworkCapabilitiesCatalog:
        """Load the canonical framework capability catalog (spec-125).

        Reads from the ``tool_capabilities`` singleton row in state.db
        instead of the legacy ``framework-capabilities.json`` file.
        """
        return self._repository().load_framework_capabilities()


# ---------------------------------------------------------------------------
# Free functions for InstallState I/O (spec-068)
# ---------------------------------------------------------------------------

_INSTALL_STATE_FILENAME = "install-state.json"
_LEGACY_AUDIT_LOG_FILENAME = "audit-log.ndjson"


def load_install_state(state_dir: Path) -> InstallState:
    """Load the install state from the state.db ``install_state`` table.

    Spec-125 cutover: state.db is now canonical; the JSON file is gone.
    This function preserves its public signature (``state_dir`` parameter
    accepted for back-compat) but reads from the singleton row at
    ``install_state.id = 1``. Callers receive defaults when the table is
    empty so first-install flows still work.

    The legacy migration path (renaming ``install-state.json`` to a
    timestamped backup when a structurally-legacy payload is found) is
    retained as a one-time fallback: if the JSON file is still on disk
    (pre-spec-125 install), we ingest it once into the table, then leave
    the JSON alone so spec-125 T-1.21 can remove it as part of the same
    wave.

    Args:
        state_dir: The ``.ai-engineering/state/`` directory. Used to
            recover the project root for the state.db connection.

    Returns:
        Parsed ``InstallState``, or a default instance when the table
        is empty AND no fallback JSON is present.
    """
    project_root = state_dir.parent.parent
    payload = _load_state_json_from_db(project_root)
    if payload is not None:
        if isinstance(payload, dict) and _is_legacy_install_state(payload):
            # Legacy payload migration: renames the on-disk JSON if it
            # still exists, refreshes the dict, and persists the merged
            # form back into the table.
            payload = _migrate_legacy_install_state(state_dir / _INSTALL_STATE_FILENAME, payload)
            _save_state_to_db(project_root, InstallState.model_validate(payload))
        return InstallState.model_validate(payload)

    # state.db row missing -- check the legacy JSON one last time so a
    # pre-spec-125 install does not lose data on first connect. The
    # singleton row is then written so subsequent loads stay on the DB
    # path.
    legacy_path = state_dir / _INSTALL_STATE_FILENAME
    if legacy_path.exists():
        data = json.loads(legacy_path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and _is_legacy_install_state(data):
            data = _migrate_legacy_install_state(legacy_path, data)
        state = InstallState.model_validate(data)
        _save_state_to_db(project_root, state)
        return state

    return InstallState()


def _load_state_json_from_db(project_root: Path) -> dict[str, Any] | None:
    """Return the install_state.state_json payload as a dict, or None when absent.

    Lazy import keeps ``state.service`` free of an eager dependency on
    ``state.state_db`` (which itself imports the migration runner).
    """
    from ai_engineering.state.state_db import connect

    conn = connect(project_root, read_only=False, apply_migrations=None)
    try:
        row = conn.execute("SELECT state_json FROM install_state WHERE id = 1").fetchone()
    finally:
        conn.close()
    if row is None:
        return None
    raw = row[0] if not hasattr(row, "keys") else row["state_json"]
    if not raw:
        return None
    return json.loads(raw)


def _save_state_to_db(project_root: Path, state: InstallState) -> None:
    """UPSERT the singleton ``install_state`` row from *state*.

    Spec-125: when called against a fresh ``state.db`` (test or first
    install), perform a one-shot lazy bootstrap so the ``install_state``
    table exists before the INSERT. ``projection_write`` itself uses
    ``apply_migrations=False`` to avoid double work in normal flows.
    """
    from ai_engineering.state.state_db import connect, projection_write

    # Lazy bootstrap: cheaply ensure the schema is in place. ``connect``
    # with ``apply_migrations=None`` runs the migration ladder iff the
    # ``_migrations`` ledger is missing, so this is a no-op on fully
    # bootstrapped DBs.
    bootstrap_conn = connect(project_root, read_only=False, apply_migrations=None)
    bootstrap_conn.close()

    payload = state.model_dump(mode="json")
    schema_version = str(payload.get("schema_version", "2.0"))
    vcs_provider = payload.get("vcs_provider")
    installed_at = payload.get("installed_at")
    operational = payload.get("operational_readiness") or {}
    operational_status = (
        operational.get("status") if isinstance(operational, dict) else None
    ) or "pending"
    state_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    updated_at = datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")

    with projection_write(project_root) as conn:
        conn.execute(
            """
            INSERT INTO install_state
              (id, schema_version, vcs_provider, installed_at,
               operational_status, state_json, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
              schema_version    = excluded.schema_version,
              vcs_provider      = excluded.vcs_provider,
              installed_at      = excluded.installed_at,
              operational_status = excluded.operational_status,
              state_json        = excluded.state_json,
              updated_at        = excluded.updated_at
            """,
            (
                schema_version,
                vcs_provider,
                installed_at,
                operational_status,
                state_json,
                updated_at,
            ),
        )


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
    """Persist *state* into the ``install_state`` state.db table.

    Spec-125 cutover: the JSON file is no longer the source of truth.
    The function still accepts ``state_dir`` for back-compat with
    callers; it derives the project root and writes the singleton row.
    Creates the state directory only when needed (older tests assume
    the directory exists post-call).

    Args:
        state_dir: The ``.ai-engineering/state/`` directory. Used to
            recover the project root for the state.db connection.
        state: The ``InstallState`` model to write.
    """
    state_dir.mkdir(parents=True, exist_ok=True)
    project_root = state_dir.parent.parent
    _save_state_to_db(project_root, state)
    logger.debug("install_state row written for project root %s", project_root)


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
