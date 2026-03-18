"""Azure DevOps platform setup — PAT validation and storage.

Guides the user through:
1. Entering the Azure DevOps organisation URL.
2. Generating a Personal Access Token (PAT) via the browser.
3. Validating the PAT via ``GET /_apis/projects?api-version=7.0``.
4. Storing the PAT in the OS secret store via ``keyring``.

Security contract: PATs are **never** written to files or logs.
Only non-secret metadata (org URL) is persisted.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

if TYPE_CHECKING:
    from ai_engineering.credentials.service import CredentialService

logger = logging.getLogger(__name__)

# Keyring identifiers for the Azure DevOps credential.
_PLATFORM_NAME: str = "azure_devops"
_KEYRING_USERNAME: str = "pat"


@dataclass
class AzureDevOpsValidationResult:
    """Result of Azure DevOps PAT validation."""

    valid: bool = False
    org_url: str = ""
    error: str = ""


@dataclass
class AzureDevOpsSetupResult:
    """Result of the full Azure DevOps setup flow."""

    success: bool = False
    org_url: str = ""
    error: str = ""


class AzureDevOpsSetup:
    """Azure DevOps PAT credential setup and validation.

    Parameters
    ----------
    credential_service:
        The credential service for storing/retrieving PATs.
    """

    def __init__(self, credential_service: CredentialService) -> None:
        self._creds = credential_service

    @staticmethod
    def get_token_url(org_url: str) -> str:
        """Return the browser URL for generating an Azure DevOps PAT.

        Format: ``{org_url}/_usersSettings/tokens``
        """
        return urljoin(org_url.rstrip("/") + "/", "_usersSettings/tokens")

    def validate_pat(self, org_url: str, pat: str) -> AzureDevOpsValidationResult:
        """Validate an Azure DevOps PAT via the REST API.

        Makes a ``GET`` request to
        ``{org_url}/_apis/projects?api-version=7.0``
        with the PAT as HTTP basic auth (empty username, PAT as password).

        Parameters
        ----------
        org_url:
            Azure DevOps organisation URL (e.g. ``https://dev.azure.com/myorg``).
        pat:
            The Personal Access Token.

        Returns
        -------
        AzureDevOpsValidationResult:
            Validation result with ``valid=True`` if the PAT is accepted.
        """
        result = AzureDevOpsValidationResult(org_url=org_url)
        api_url = urljoin(
            org_url.rstrip("/") + "/",
            "_apis/projects?api-version=7.0",
        )

        try:
            import httpx as _httpx

            response = _httpx.get(
                api_url,
                auth=("", pat),
                timeout=10.0,
            )
            if response.status_code == 200:
                result.valid = True
            elif response.status_code in (401, 403):
                result.error = "PAT rejected — invalid or insufficient permissions"
            else:
                result.error = f"HTTP {response.status_code} from Azure DevOps API"
        except ImportError:
            # Fallback to urllib if httpx is not available.
            result = self._validate_pat_urllib(org_url, pat)
        except Exception as exc:
            result.error = f"Connection error: {exc}"

        return result

    @staticmethod
    def _validate_pat_urllib(org_url: str, pat: str) -> AzureDevOpsValidationResult:
        """Fallback validation using stdlib ``urllib``.

        Used when ``httpx`` is not installed. Uses HTTP basic auth
        with empty username and PAT as password.
        """
        import base64
        import http.client

        result = AzureDevOpsValidationResult(org_url=org_url)
        api_url = urljoin(
            org_url.rstrip("/") + "/",
            "_apis/projects?api-version=7.0",
        )
        parsed = urlparse(api_url)
        if parsed.scheme not in {"https", "http"}:
            result.error = "Invalid Azure DevOps API URL scheme"
            return result

        credentials = base64.b64encode(f":{pat}".encode()).decode()
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
            if resp.status == 200:
                result.valid = True
            else:
                result.error = f"HTTP {resp.status} from Azure DevOps API"
        except (http.client.HTTPException, OSError) as exc:
            result.error = f"Connection error: {exc}"
        except Exception as exc:
            result.error = f"Unexpected error: {exc}"
        finally:
            if conn is not None:
                conn.close()

        return result

    def store_pat(self, pat: str) -> None:
        """Store the Azure DevOps PAT in the OS secret store."""
        self._creds.store(_PLATFORM_NAME, _KEYRING_USERNAME, pat)
        logger.debug("Azure DevOps PAT stored in keyring")

    def retrieve_pat(self) -> str | None:
        """Retrieve the stored Azure DevOps PAT, or ``None`` if absent."""
        return self._creds.retrieve(_PLATFORM_NAME, _KEYRING_USERNAME)

    def is_configured(self) -> bool:
        """Return ``True`` if an Azure DevOps PAT is stored."""
        return self._creds.exists(_PLATFORM_NAME, _KEYRING_USERNAME)

    def delete_pat(self) -> None:
        """Delete the stored Azure DevOps PAT."""
        self._creds.delete(_PLATFORM_NAME, _KEYRING_USERNAME)

    @staticmethod
    def get_setup_instructions(org_url: str) -> str:
        """Return user-facing instructions for Azure DevOps setup."""
        token_url = AzureDevOpsSetup.get_token_url(org_url)
        return (
            "Azure DevOps credential setup:\n"
            f"\n  1. Open: {token_url}\n"
            "  2. Click 'New Token'.\n"
            "  3. Select scopes: Code (Read & Write), Build (Read).\n"
            "  4. Copy the token and paste it when prompted.\n"
            "\nThe PAT will be stored in your OS secret store (keyring).\n"
            "It will never be written to files or displayed in logs."
        )
