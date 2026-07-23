"""Integration pack YAML schema (spec-198 T-1).

Defines the structure for governed CLI/MCP integration packs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Provenance:
    """Provenance lock for a pack."""

    vendor_source: str
    version: str
    license: str
    asset_digest: str  # SHA256 of binary/asset
    launcher_digest: str  # SHA256 of launcher script
    supported_platforms: list[str] = field(default_factory=lambda: ["darwin-arm64", "linux-x64"])


@dataclass(frozen=True)
class CommandSpec:
    """Specification for a single command."""

    name: str
    description: str
    command_type: str  # "read-only", "mutation", "production", "destructive"
    timeout_seconds: int = 30
    output_cap_bytes: int = 8192
    requires_confirmation: bool = False
    confirmation_phrase: str | None = None


@dataclass(frozen=True)
class CredentialSpec:
    """Credential requirements for a pack."""

    source: str  # "keychain", "env", "process-local"
    service_name: str
    required: bool = True
    acl_description: str = ""


@dataclass(frozen=True)
class IntegrationPack:
    """Complete integration pack definition."""

    name: str
    description: str
    provenance: Provenance
    commands: list[CommandSpec]
    credentials: list[CredentialSpec]
    mcp_fallback: str = "forbidden"  # must be "forbidden"
    entry_budget_tokens: int = 200  # max tokens for SKILL.md entry

    def to_json(self) -> str:
        return json.dumps(
            {
                "name": self.name,
                "description": self.description,
                "provenance": {
                    "vendor_source": self.provenance.vendor_source,
                    "version": self.provenance.version,
                    "license": self.provenance.license,
                    "asset_digest": self.provenance.asset_digest,
                    "launcher_digest": self.provenance.launcher_digest,
                    "supported_platforms": self.provenance.supported_platforms,
                },
                "commands": [
                    {
                        "name": c.name,
                        "description": c.description,
                        "command_type": c.command_type,
                        "timeout_seconds": c.timeout_seconds,
                        "output_cap_bytes": c.output_cap_bytes,
                        "requires_confirmation": c.requires_confirmation,
                        "confirmation_phrase": c.confirmation_phrase,
                    }
                    for c in self.commands
                ],
                "credentials": [
                    {
                        "source": cr.source,
                        "service_name": cr.service_name,
                        "required": cr.required,
                        "acl_description": cr.acl_description,
                    }
                    for cr in self.credentials
                ],
                "mcp_fallback": self.mcp_fallback,
                "entry_budget_tokens": self.entry_budget_tokens,
            },
            indent=2,
            sort_keys=True,
        )

    @classmethod
    def from_json(cls, data: str | dict[str, Any]) -> IntegrationPack:
        if isinstance(data, str):
            data = json.loads(data)
        return cls(
            name=data["name"],
            description=data["description"],
            provenance=Provenance(**data["provenance"]),
            commands=[CommandSpec(**c) for c in data["commands"]],
            credentials=[CredentialSpec(**c) for c in data["credentials"]],
            mcp_fallback=data.get("mcp_fallback", "forbidden"),
            entry_budget_tokens=data.get("entry_budget_tokens", 200),
        )
