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

import logging
from typing import TYPE_CHECKING

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
        logger.debug("Secret persisted in OS keyring")

    def retrieve(self, platform: str, username: str) -> str | None:
        """Retrieve the secret for *platform*/*username*.

        Returns ``None`` if no credential is stored or if no keyring
        backend is available (e.g. headless CI environments).
        """
        try:
            backend = self._get_keyring()
            return backend.get_password(self.service_name(platform), username)
        except Exception:
            logger.debug("Keyring unavailable when retrieving %s/%s", platform, username)
            return None

    def delete(self, platform: str, username: str) -> None:
        """Delete the credential for *platform*/*username*.

        Silently ignores missing entries.
        """
        backend = self._get_keyring()
        try:
            backend.delete_password(self.service_name(platform), username)
            logger.debug("Secret removed from OS keyring")
        except Exception:
            logger.debug("No matching keyring entry to remove")

    def exists(self, platform: str, username: str) -> bool:
        """Return ``True`` if a credential exists for *platform*/*username*."""
        return self.retrieve(platform, username) is not None

    @staticmethod
    def mask_secret(value: str, visible_chars: int = 4) -> str:
        """Return a masked version of *value* for safe terminal display.

        Shows the first *visible_chars* characters followed by ``***``.
        Returns ``***`` when the value is too short to partially reveal.
        """
        if len(value) <= visible_chars:
            return "***"
        return value[:visible_chars] + "***"
