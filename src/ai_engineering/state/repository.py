"""Repository boundaries for manifest and durable-state artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ai_engineering.config.loader import load_manifest_config, update_manifest_field
from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.state.io import read_json_model, write_json_model
from ai_engineering.state.models import (
    DecisionStore,
    FrameworkCapabilitiesCatalog,
    FrameworkEvent,
    InstallState,
    OwnershipMap,
)
from ai_engineering.state.service import load_install_state

_MANIFEST_REL = Path(".ai-engineering") / "manifest.yml"
_STATE_REL = Path(".ai-engineering") / "state"
_INSTALL_STATE_FILENAME = "install-state.json"
_DECISION_STORE_FILENAME = "decision-store.json"
_OWNERSHIP_MAP_FILENAME = "ownership-map.json"
_FRAMEWORK_CAPABILITIES_FILENAME = "framework-capabilities.json"
_FRAMEWORK_EVENTS_FILENAME = "framework-events.ndjson"


class ManifestRepository:
    """Public manifest access boundary for typed, raw, partial, and patch reads."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.manifest_path = project_root / _MANIFEST_REL

    def load_typed(self) -> ManifestConfig:
        """Load the manifest through the canonical typed loader."""
        return load_manifest_config(self.project_root)

    def load_raw(self) -> dict[str, Any]:
        """Load a raw manifest snapshot for compatibility readers."""
        if not self.manifest_path.is_file():
            return {}
        try:
            data = yaml.safe_load(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError):
            return {}
        return data if isinstance(data, dict) else {}

    def get_partial(self, field_path: str) -> Any | None:
        """Return a partial raw field by dotted path, or None when absent."""
        value: Any = self.load_raw()
        for key in field_path.split("."):
            if not isinstance(value, dict) or key not in value:
                return None
            value = value[key]
        return value

    def patch_field(self, field_path: str, value: Any) -> None:
        """Patch a manifest field through the comment-preserving writer."""
        update_manifest_field(self.project_root, field_path, value)


class DurableStateRepository:
    """Public durable-state access boundary for stable state families."""

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root
        self.state_dir = project_root / _STATE_REL

    @property
    def install_state_path(self) -> Path:
        """Return the install-state artifact path."""
        return self.state_dir / _INSTALL_STATE_FILENAME

    @property
    def decision_store_path(self) -> Path:
        """Return the decision-store artifact path."""
        return self.state_dir / _DECISION_STORE_FILENAME

    @property
    def ownership_map_path(self) -> Path:
        """Return the ownership-map artifact path."""
        return self.state_dir / _OWNERSHIP_MAP_FILENAME

    @property
    def framework_capabilities_path(self) -> Path:
        """Return the framework-capabilities projection path."""
        return self.state_dir / _FRAMEWORK_CAPABILITIES_FILENAME

    @property
    def framework_events_path(self) -> Path:
        """Return the framework event stream path without owning append semantics."""
        return self.state_dir / _FRAMEWORK_EVENTS_FILENAME

    def load_install_state(self) -> InstallState:
        """Load install-state through the migration-preserving state service."""
        return load_install_state(self.state_dir)

    def load_decisions(self) -> DecisionStore:
        """Load the decision-store family.

        spec-124 D-124-12: After the JSON fallback was deleted in
        wave 5, return an empty default when the file is missing.
        State.db is the canonical source; the JSON projection is
        rewritten on-demand only when explicitly saved.
        """
        if not self.decision_store_path.exists():
            from ai_engineering.state.defaults import default_decision_store

            return default_decision_store()
        return read_json_model(self.decision_store_path, DecisionStore)

    def save_decisions(self, store: DecisionStore) -> None:
        """Save the decision-store family."""
        write_json_model(self.decision_store_path, store)

    def load_ownership(self) -> OwnershipMap:
        """Load the ownership-map family.

        spec-124 D-124-12: After the JSON fallback was deleted in
        wave 5, return an empty default when the file is missing.
        State.db.ownership_map is the canonical source.
        """
        if not self.ownership_map_path.exists():
            from ai_engineering.state.defaults import default_ownership_map

            return default_ownership_map()
        return read_json_model(self.ownership_map_path, OwnershipMap)

    def save_ownership(self, ownership: OwnershipMap) -> None:
        """Save the ownership-map family."""
        write_json_model(self.ownership_map_path, ownership)

    def load_framework_capabilities(self) -> FrameworkCapabilitiesCatalog:
        """Load the framework-capabilities derived projection.

        Spec-125: the catalog moved from
        ``framework-capabilities.json`` to the ``tool_capabilities``
        singleton row in state.db. Reads now go through the state.db
        connection helpers; the JSON path is no longer authoritative.
        """
        from ai_engineering.state.state_db import connect

        conn = connect(self.project_root, read_only=False, apply_migrations=None)
        try:
            row = conn.execute("SELECT catalog_json FROM tool_capabilities WHERE id = 1").fetchone()
        finally:
            conn.close()
        if row is None:
            return FrameworkCapabilitiesCatalog()
        raw = row[0] if not hasattr(row, "keys") else row["catalog_json"]
        if not raw:
            return FrameworkCapabilitiesCatalog()
        return FrameworkCapabilitiesCatalog.model_validate_json(raw)

    def save_framework_capabilities(self, catalog: FrameworkCapabilitiesCatalog) -> None:
        """Save the framework-capabilities derived projection.

        Spec-125: routes through the canonical state.db UPSERT in
        :func:`ai_engineering.state.observability.write_framework_capabilities`
        helper logic. Implemented inline here to avoid circular imports
        between repository <-> observability.
        """
        import json as _json
        from datetime import UTC as _UTC
        from datetime import datetime as _datetime

        from ai_engineering.state.state_db import connect, projection_write

        # Lazy bootstrap so a fresh state.db has the
        # ``tool_capabilities`` table before the UPSERT.
        _bootstrap = connect(self.project_root, read_only=False, apply_migrations=None)
        _bootstrap.close()

        payload = catalog.model_dump(mode="json", by_alias=True)
        schema_version = str(payload.get("schemaVersion", "1.0"))
        generated_at = payload.get("generatedAt", "")
        if not isinstance(generated_at, str):
            generated_at = str(generated_at)
        agents = payload.get("agents") or []
        skills = payload.get("skills") or []
        cards = payload.get("capabilityCards") or []
        catalog_json = _json.dumps(payload, sort_keys=True, separators=(",", ":"))
        updated_at = _datetime.now(_UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        with projection_write(self.project_root) as conn:
            conn.execute(
                """
                INSERT INTO tool_capabilities
                  (id, schema_version, generated_at, agents_count,
                   skills_count, capability_cards_count, catalog_json, updated_at)
                VALUES (1, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                  schema_version          = excluded.schema_version,
                  generated_at            = excluded.generated_at,
                  agents_count            = excluded.agents_count,
                  skills_count            = excluded.skills_count,
                  capability_cards_count  = excluded.capability_cards_count,
                  catalog_json            = excluded.catalog_json,
                  updated_at              = excluded.updated_at
                """,
                (
                    schema_version,
                    generated_at,
                    len(agents),
                    len(skills),
                    len(cards),
                    catalog_json,
                    updated_at,
                ),
            )

    def append_framework_event(self, entry: FrameworkEvent) -> None:
        """Append a framework event through the existing observability writer."""
        # Delayed so repository construction does not pull in observability side effects.
        from ai_engineering.state.observability import append_framework_event

        append_framework_event(self.project_root, entry)
