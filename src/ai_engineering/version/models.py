"""Pydantic models for version lifecycle management.

Defines schemas for:
- VersionStatus: lifecycle state of a version (current, supported, deprecated, eol).
- VersionEntry: a single version record in the registry.
- VersionRegistry: the full embedded version registry.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class VersionStatus(StrEnum):
    """Lifecycle status of a framework version."""

    CURRENT = "current"
    SUPPORTED = "supported"
    DEPRECATED = "deprecated"
    EOL = "eol"


class VersionEntry(BaseModel):
    """A single version record in the registry."""

    version: str
    status: VersionStatus
    released: str
    deprecated_reason: str | None = Field(default=None, alias="deprecatedReason")
    eol_date: str | None = Field(default=None, alias="eolDate")

    model_config = {"populate_by_name": True}


class VersionRegistry(BaseModel):
    """Embedded version registry shipped with the package.

    Declares all known versions and their lifecycle status.
    Loaded from ``version/registry.json`` at runtime.
    """

    schema_version: str = Field(default="1.0", alias="schemaVersion")
    versions: list[VersionEntry] = Field(default_factory=list)

    model_config = {"populate_by_name": True}
