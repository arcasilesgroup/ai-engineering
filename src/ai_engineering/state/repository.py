"""Repository boundaries for manifest and durable-state artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ai_engineering.config.loader import load_manifest_config, update_manifest_field
from ai_engineering.config.manifest import ManifestConfig
from ai_engineering.state.io import read_json_model, write_json_model
from ai_engineering.state.service import load_install_state
from skill_domain.state_models import (
    DecisionStore,
    FrameworkCapabilitiesCatalog,
    FrameworkEvent,
    InstallState,
    OwnershipMap,
)

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
        """Load a raw manifest snapshot for compatibility readers.

        spec-147 G1 T-1.9/1.10: a missing manifest is a legitimate empty
        snapshot (``{}``); a manifest that EXISTS but cannot be parsed fails
        loud via :class:`InvalidManifestError` rather than masquerading as
        an empty one.
        """
        if not self.manifest_path.is_file():
            return {}
        try:
            data = yaml.safe_load(self.manifest_path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            from ai_engineering.config.loader import InvalidManifestError

            msg = f"failed to read or parse manifest at {self.manifest_path}: {exc}"
            raise InvalidManifestError(msg) from exc
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
        """Load the decision-store family from ``decision-store.json``.

        spec-148 P2 (files-only): ``decision-store.json`` is the single
        source of truth — it already carries the optional per-entry hash
        chain verified by ``ai-eng audit verify``. Returns the default
        empty store when the file is absent (first install / fresh repo).
        """
        if not self.decision_store_path.exists():
            from ai_engineering.state.defaults import default_decision_store

            return default_decision_store()
        return read_json_model(self.decision_store_path, DecisionStore)

    def save_decisions(self, store: DecisionStore) -> None:
        """Persist the decision-store to ``decision-store.json`` (sole SoT).

        spec-148 P2 (files-only): the SQLite ``decisions`` dual-write is
        gone; this is the only durable write path for decisions and risk
        acceptances.
        """
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
        """Load the framework-capabilities catalog from ``framework-capabilities.json``.

        spec-148 P4 (files-only): the catalog is a rebuildable-on-demand
        file projection (reverses the spec-125 move into the state.db
        ``tool_capabilities`` row). Returns an empty catalog when the file
        is absent.
        """
        if not self.framework_capabilities_path.exists():
            return FrameworkCapabilitiesCatalog()
        return read_json_model(self.framework_capabilities_path, FrameworkCapabilitiesCatalog)

    def save_framework_capabilities(self, catalog: FrameworkCapabilitiesCatalog) -> None:
        """Save the framework-capabilities catalog to ``framework-capabilities.json``.

        spec-148 P4 (files-only): the only durable write path for the
        catalog. Rebuild it with
        :func:`ai_engineering.state.observability.write_framework_capabilities`.
        """
        write_json_model(self.framework_capabilities_path, catalog)

    def append_framework_event(self, entry: FrameworkEvent) -> None:
        """Append a framework event through the existing observability writer."""
        # Delayed so repository construction does not pull in observability side effects.
        from ai_engineering.state.observability import append_framework_event

        append_framework_event(self.project_root, entry)
