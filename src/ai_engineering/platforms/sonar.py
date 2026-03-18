"""SonarCloud / SonarQube platform setup — token validation and storage.

Guides the user through:
1. Entering the Sonar server URL (SonarCloud or self-hosted).
2. Generating a token via the browser.
3. Validating the token via ``GET /api/authentication/validate``.
4. Storing the token in the OS secret store via ``keyring``.

Security contract: tokens are **never** written to files or logs.
Only non-secret metadata (URL, project key) is persisted.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

if TYPE_CHECKING:
    from ai_engineering.credentials.service import CredentialService

logger = logging.getLogger(__name__)

# Default SonarCloud URL.
SONARCLOUD_URL: str = "https://sonarcloud.io"

# Keyring identifiers for the Sonar credential.
_PLATFORM_NAME: str = "sonar"
_KEYRING_USERNAME: str = "token"


@dataclass
class SonarValidationResult:
    """Result of Sonar token validation."""

    valid: bool = False
    url: str = ""
    error: str = ""


@dataclass
class SonarSetupResult:
    """Result of the full Sonar setup flow."""

    success: bool = False
    url: str = ""
    project_key: str = ""
    error: str = ""


class SonarSetup:
    """SonarCloud / SonarQube credential setup and validation.

    Parameters
    ----------
    credential_service:
        The credential service for storing/retrieving tokens.
    """

    def __init__(self, credential_service: CredentialService) -> None:
        self._creds = credential_service

    @staticmethod
    def get_token_url(base_url: str) -> str:
        """Return the browser URL for generating a Sonar token.

        For SonarCloud: ``https://sonarcloud.io/account/security``
        For self-hosted: ``{base_url}/account/security``
        """
        return urljoin(base_url.rstrip("/") + "/", "account/security")

    def validate_token(self, url: str, token: str) -> SonarValidationResult:
        """Validate a Sonar token via the authentication API.

        Makes a ``GET`` request to ``/api/authentication/validate``
        with the token as HTTP basic auth (token as username, empty password).

        Parameters
        ----------
        url:
            Sonar server URL (e.g. ``https://sonarcloud.io``).
        token:
            The Sonar authentication token.

        Returns
        -------
        SonarValidationResult:
            Validation result with ``valid=True`` if the token is accepted.
        """
        result = SonarValidationResult(url=url)
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        api_url = urljoin(base.rstrip("/") + "/", "api/authentication/validate")

        try:
            import httpx as _httpx

            response = _httpx.get(
                api_url,
                auth=(token, ""),
                timeout=10.0,
            )
            if response.status_code == 200:
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    result.error = (
                        "Could not parse Sonar API response — "
                        "verify the URL is a base URL like https://sonarcloud.io"
                    )
                    return result
                result.valid = data.get("valid", False)
                if not result.valid:
                    result.error = "Token rejected by Sonar server"
            else:
                result.error = f"HTTP {response.status_code} from Sonar API"
        except ImportError:
            # Fallback to urllib if httpx is not available.
            result = self._validate_token_urllib(url, token)
        except Exception as exc:
            result.error = f"Connection error: {exc}"

        return result

    @staticmethod
    def _validate_token_urllib(url: str, token: str) -> SonarValidationResult:
        """Fallback validation using stdlib ``urllib``.

        Used when ``httpx`` is not installed. Uses HTTP basic auth
        with the token as username and empty password.
        """
        import base64
        import http.client
        import json

        result = SonarValidationResult(url=url)
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        api_url = urljoin(base.rstrip("/") + "/", "api/authentication/validate")
        parsed = urlparse(api_url)
        if parsed.scheme not in {"https", "http"}:
            result.error = "Invalid Sonar API URL scheme"
            return result

        credentials = base64.b64encode(f"{token}:".encode()).decode()
        path = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        conn_cls = (
            http.client.HTTPSConnection if parsed.scheme == "https" else http.client.HTTPConnection
        )
        conn: http.client.HTTPConnection | http.client.HTTPSConnection | None = None

        try:
            conn = conn_cls(parsed.netloc, timeout=10)
            conn.request(
                "GET",
                path,
                headers={"Authorization": f"Basic {credentials}"},
            )
            resp = conn.getresponse()
            data = json.loads(resp.read().decode())
            result.valid = data.get("valid", False)
            if not result.valid:
                result.error = "Token rejected by Sonar server"
        except (http.client.HTTPException, OSError) as exc:
            result.error = f"Connection error: {exc}"
        except Exception as exc:
            result.error = f"Unexpected error: {exc}"
        finally:
            if conn is not None:
                conn.close()

        return result

    def store_token(self, token: str) -> None:
        """Store the Sonar token in the OS secret store."""
        self._creds.store(_PLATFORM_NAME, _KEYRING_USERNAME, token)
        logger.debug("Sonar token stored in keyring")

    def retrieve_token(self) -> str | None:
        """Retrieve the stored Sonar token, or ``None`` if absent."""
        return self._creds.retrieve(_PLATFORM_NAME, _KEYRING_USERNAME)

    def is_configured(self) -> bool:
        """Return ``True`` if a Sonar token is stored."""
        return self._creds.exists(_PLATFORM_NAME, _KEYRING_USERNAME)

    def delete_token(self) -> None:
        """Delete the stored Sonar token."""
        self._creds.delete(_PLATFORM_NAME, _KEYRING_USERNAME)

    @staticmethod
    def get_setup_instructions(url: str = SONARCLOUD_URL) -> str:
        """Return user-facing instructions for Sonar setup."""
        token_url = SonarSetup.get_token_url(url)
        return (
            "SonarCloud / SonarQube credential setup:\n"
            f"\n  1. Open: {token_url}\n"
            "  2. Generate a new token (type: User Token).\n"
            "  3. Copy the token and paste it when prompted.\n"
            "\nThe token will be stored in your OS secret store (keyring).\n"
            "It will never be written to files or displayed in logs."
        )
