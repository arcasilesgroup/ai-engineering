"""Pack validator (spec-198 T-2).

Validates provenance, credentials, and contract compliance.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .schema import IntegrationPack, Provenance


@dataclass(frozen=True)
class ValidationResult:
    """Result of pack validation."""

    valid: bool
    errors: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


def validate_provenance(provenance: Provenance) -> list[str]:
    """Validate provenance lock. Returns errors."""
    errors = []

    if not provenance.vendor_source:
        errors.append("Missing vendor_source")
    if not provenance.version:
        errors.append("Missing version")
    if not provenance.license:
        errors.append("Missing license")
    if not provenance.asset_digest:
        errors.append("Missing asset_digest")
    if not provenance.launcher_digest:
        errors.append("Missing launcher_digest")
    if not provenance.supported_platforms:
        errors.append("Missing supported_platforms")

    return errors


def validate_mcp_fallback(pack: IntegrationPack) -> list[str]:
    """Validate MCP fallback is forbidden."""
    errors = []
    if pack.mcp_fallback != "forbidden":
        errors.append(f"MCP fallback must be 'forbidden', got '{pack.mcp_fallback}'")
    return errors


def validate_commands(pack: IntegrationPack) -> list[str]:
    """Validate command specifications."""
    errors = []
    valid_types = {"read-only", "mutation", "production", "destructive"}

    for cmd in pack.commands:
        if cmd.command_type not in valid_types:
            errors.append(f"Command {cmd.name}: invalid type '{cmd.command_type}'")
        if cmd.requires_confirmation and not cmd.confirmation_phrase:
            errors.append(f"Command {cmd.name}: requires confirmation but no phrase")
        if cmd.timeout_seconds <= 0:
            errors.append(f"Command {cmd.name}: timeout must be positive")
        if cmd.output_cap_bytes <= 0:
            errors.append(f"Command {cmd.name}: output cap must be positive")

    return errors


def validate_pack(pack: IntegrationPack) -> ValidationResult:
    """Validate a complete integration pack."""
    errors = []
    warnings = []

    # Validate provenance
    errors.extend(validate_provenance(pack.provenance))

    # Validate MCP fallback
    errors.extend(validate_mcp_fallback(pack))

    # Validate commands
    errors.extend(validate_commands(pack))

    # Validate credentials
    valid_sources = {"keychain", "env", "process-local"}
    for cred in pack.credentials:
        if cred.source not in valid_sources:
            errors.append(f"Credential {cred.service_name}: invalid source '{cred.source}'")

    # Warnings
    if pack.entry_budget_tokens > 200:
        warnings.append(f"Entry budget {pack.entry_budget_tokens} exceeds recommended 200 tokens")

    return ValidationResult(
        valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )
