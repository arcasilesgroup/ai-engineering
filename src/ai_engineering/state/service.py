"""State service facade for ai-engineering state I/O.

Provides a single entry point for loading and saving state files,
replacing direct imports of ``state.io`` + ``state.models`` in CLI commands.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.state.io import append_ndjson, read_json_model, write_json_model
from ai_engineering.state.models import (
    AuditEntry,
    DecisionStore,
    InstallManifest,
    OwnershipMap,
)


class StateService:
    """Facade for reading and writing ai-engineering state files."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._state_dir = project_root / ".ai-engineering" / "state"

    @property
    def state_dir(self) -> Path:
        """Return the state directory path."""
        return self._state_dir

    def load_manifest(self) -> InstallManifest:
        """Load the install manifest."""
        return read_json_model(self._state_dir / "install-manifest.json", InstallManifest)

    def save_manifest(self, manifest: InstallManifest) -> None:
        """Save the install manifest."""
        write_json_model(self._state_dir / "install-manifest.json", manifest)

    def load_decisions(self) -> DecisionStore:
        """Load the decision store."""
        return read_json_model(self._state_dir / "decision-store.json", DecisionStore)

    def load_ownership(self) -> OwnershipMap:
        """Load the ownership map."""
        return read_json_model(self._state_dir / "ownership-map.json", OwnershipMap)

    def append_audit(self, entry: AuditEntry) -> None:
        """Append an entry to the audit log."""
        append_ndjson(self._state_dir / "audit-log.ndjson", entry)
