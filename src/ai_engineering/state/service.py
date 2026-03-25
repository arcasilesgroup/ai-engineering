"""State service facade for ai-engineering state I/O.

Provides a single entry point for loading and saving state files,
replacing direct imports of ``state.io`` + ``state.models`` in CLI commands.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ai_engineering.state.io import append_ndjson, read_json_model, write_json_model
from ai_engineering.state.models import (
    AuditEntry,
    DecisionStore,
    InstallState,
    OwnershipMap,
)

logger = logging.getLogger(__name__)


class StateService:
    """Facade for reading and writing ai-engineering state files."""

    def __init__(self, project_root: Path) -> None:
        self._root = project_root
        self._state_dir = project_root / ".ai-engineering" / "state"

    @property
    def state_dir(self) -> Path:
        """Return the state directory path."""
        return self._state_dir

    def load_decisions(self) -> DecisionStore:
        """Load the decision store."""
        return read_json_model(self._state_dir / "decision-store.json", DecisionStore)

    def save_decisions(self, store: DecisionStore) -> None:
        """Save the decision store."""
        write_json_model(self._state_dir / "decision-store.json", store)

    def load_ownership(self) -> OwnershipMap:
        """Load the ownership map."""
        return read_json_model(self._state_dir / "ownership-map.json", OwnershipMap)

    def append_audit(self, entry: AuditEntry) -> None:
        """Append an entry to the audit log."""
        append_ndjson(self._state_dir / "audit-log.ndjson", entry)


# ---------------------------------------------------------------------------
# Free functions for InstallState I/O (spec-068)
# ---------------------------------------------------------------------------

_INSTALL_STATE_FILENAME = "install-state.json"


def load_install_state(state_dir: Path) -> InstallState:
    """Load ``install-state.json`` from *state_dir*, returning defaults if absent.

    Follows the same pattern as ``CredentialService.load_tools_state()``:
    file-present -> parse + validate, file-absent -> sensible defaults.

    Args:
        state_dir: The ``.ai-engineering/state/`` directory.

    Returns:
        Parsed ``InstallState``, or a default instance when the file
        does not exist.
    """
    path = state_dir / _INSTALL_STATE_FILENAME
    if path.exists():
        data = json.loads(path.read_text(encoding="utf-8"))
        return InstallState.model_validate(data)
    return InstallState()


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
