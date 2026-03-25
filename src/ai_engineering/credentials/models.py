"""Pydantic models for credential metadata.

Platform state is now tracked in ``InstallState.platforms``
(see ``state.models``). This module retains only the
``PlatformKind`` enum used by the setup wizard and detector.

Security contract: models **never** contain actual secret values.
"""

from __future__ import annotations

from enum import StrEnum


class PlatformKind(StrEnum):
    """Supported platform types."""

    GITHUB = "github"
    SONAR = "sonar"
    AZURE_DEVOPS = "azure_devops"
