"""OS-native credential storage service.

Wraps the ``keyring`` library to provide a clean interface for
storing, retrieving, and validating platform credentials.

Security invariants
-------------------
* Tokens are stored exclusively in the OS secret store
  (Windows Credential Manager / macOS Keychain / Linux libsecret).
* Tokens are **never** written to files, environment variables, or logs.
* Terminal output masks secrets with ``***``.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from ai_engineering.credentials.models import ToolsState

if TYPE_CHECKING:
    import keyring.backend

logger = logging.getLogger(__name__)

# Keyring service name prefix — all ai-engineering credentials share this.
_SERVICE_PREFIX = "ai-engineering"


class CredentialService:
    """Manage platform credentials via OS-native secret store.

    Parameters
    ----------
    backend:
        Optional keyring backend override (useful for testing).
        When ``None``, uses the system default backend.
    """

    def __init__(self, backend: keyring.backend.KeyringBackend | None = None) -> None:
        self._backend = backend

    # ------------------------------------------------------------------
    # Low-level keyring operations
    # ------------------------------------------------------------------

    def _get_keyring(self) -> keyring.backend.KeyringBackend:
        """Return the active keyring backend."""
        if self._backend is not None:
            return self._backend

        import keyring as kr

        return kr.get_keyring()

    @staticmethod
    def service_name(platform: str) -> str:
        """Build keyring service name for *platform*."""
        return f"{_SERVICE_PREFIX}/{platform}"

    def store(self, platform: str, username: str, secret: str) -> None:
        """Store *secret* for *platform*/*username* in the OS secret store."""
        backend = self._get_keyring()
        backend.set_password(self.service_name(platform), username, secret)
        logger.debug("Credential stored for %s/%s", platform, username)

    def retrieve(self, platform: str, username: str) -> str | None:
        """Retrieve the secret for *platform*/*username*.

        Returns ``None`` if no credential is stored.
        """
        backend = self._get_keyring()
        return backend.get_password(self.service_name(platform), username)

    def delete(self, platform: str, username: str) -> None:
        """Delete the credential for *platform*/*username*.

        Silently ignores missing entries.
        """
        backend = self._get_keyring()
        try:
            backend.delete_password(self.service_name(platform), username)
            logger.debug("Credential deleted for %s/%s", platform, username)
        except Exception:  # noqa: BLE001 — keyring backends raise various types
            logger.debug("No credential to delete for %s/%s", platform, username)

    def exists(self, platform: str, username: str) -> bool:
        """Return ``True`` if a credential exists for *platform*/*username*."""
        return self.retrieve(platform, username) is not None

    # ------------------------------------------------------------------
    # tools.json state management
    # ------------------------------------------------------------------

    @staticmethod
    def load_tools_state(state_dir: Path) -> ToolsState:
        """Load ``tools.json`` from *state_dir*, returning defaults if absent."""
        path = state_dir / "tools.json"
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return ToolsState.model_validate(data)
        return ToolsState()

    @staticmethod
    def save_tools_state(state_dir: Path, state: ToolsState) -> None:
        """Persist *state* to ``tools.json`` in *state_dir*."""
        path = state_dir / "tools.json"
        state_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(
            state.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        logger.debug("tools.json written to %s", path)

    @staticmethod
    def mask_secret(value: str, visible_chars: int = 4) -> str:
        """Return a masked version of *value* for safe terminal display.

        Shows the first *visible_chars* characters followed by ``***``.
        Returns ``***`` when the value is too short to partially reveal.
        """
        if len(value) <= visible_chars:
            return "***"
        return value[:visible_chars] + "***"
