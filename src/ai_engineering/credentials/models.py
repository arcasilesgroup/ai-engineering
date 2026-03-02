"""Pydantic models for credential metadata and platform state.

These models define the schema for ``.ai-engineering/state/tools.json``
and the in-memory representations used by the credential service.

Security contract: models **never** contain actual secret values.
Only non-secret metadata (URLs, project keys, boolean flags) is
serialised to disk.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class PlatformKind(StrEnum):
    """Supported platform types."""

    GITHUB = "github"
    SONAR = "sonar"
    AZURE_DEVOPS = "azure_devops"


class CredentialRef(BaseModel):
    """Reference to a credential stored in the OS secret store.

    The actual token/secret is **never** part of this model.
    ``service_name`` and ``username`` are the keyring lookup keys.
    """

    service_name: str = Field(description="Keyring service name (e.g. 'ai-engineering/sonar').")
    username: str = Field(description="Keyring username / account identifier.")
    configured: bool = Field(default=False, description="Whether a credential has been stored.")


class GitHubConfig(BaseModel):
    """GitHub platform metadata (non-secret)."""

    configured: bool = Field(default=False)
    cli_authenticated: bool = Field(default=False)
    scopes: list[str] = Field(default_factory=list, description="Verified OAuth scopes.")


class SonarConfig(BaseModel):
    """SonarCloud / SonarQube platform metadata (non-secret)."""

    configured: bool = Field(default=False)
    url: str = Field(default="", description="Sonar server URL (e.g. https://sonarcloud.io).")
    project_key: str = Field(default="", description="Sonar project key.")
    organization: str = Field(
        default="", description="Sonar organization (required for SonarCloud)."
    )
    credential_ref: CredentialRef | None = Field(
        default=None,
        description="Reference to the keyring entry — never the token itself.",
    )


class AzureDevOpsConfig(BaseModel):
    """Azure DevOps platform metadata (non-secret)."""

    configured: bool = Field(default=False)
    org_url: str = Field(
        default="", description="Organisation URL (e.g. https://dev.azure.com/org)."
    )
    credential_ref: CredentialRef | None = Field(
        default=None,
        description="Reference to the keyring entry — never the PAT itself.",
    )


class ToolsState(BaseModel):
    """Root model for ``.ai-engineering/state/tools.json``.

    Serialised as JSON. Contains **only** non-secret metadata.
    """

    github: GitHubConfig = Field(default_factory=GitHubConfig)
    sonar: SonarConfig = Field(default_factory=SonarConfig)
    azure_devops: AzureDevOpsConfig = Field(default_factory=AzureDevOpsConfig)
