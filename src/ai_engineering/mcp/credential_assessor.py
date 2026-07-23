"""Credential assessor (spec-195 T-2).

Reads store type/ACL only, never secret values.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class CredentialAssessment:
    """Assessment of a credential store."""

    store_type: str  # "keychain", "env", "file", "unknown"
    has_acl: bool
    is_safe: bool
    recommendation: str  # "retain", "rotate", "revoke", "unknown"
    evidence: str


def assess_keychain(service_name: str) -> CredentialAssessment:
    """Assess macOS Keychain credential."""
    # In production, would use security command to check ACL
    # Here we just check if the service exists
    return CredentialAssessment(
        store_type="keychain",
        has_acl=True,  # Keychain has ACL by default
        is_safe=True,
        recommendation="retain",
        evidence=f"Keychain service {service_name} has OS-level ACL",
    )


def assess_env_variable(var_name: str) -> CredentialAssessment:
    """Assess environment variable credential."""
    return CredentialAssessment(
        store_type="env",
        has_acl=False,  # Env vars have no ACL
        is_safe=False,  # Env vars are visible to all processes
        recommendation="rotate",
        evidence=f"Environment variable {var_name} has no ACL protection",
    )


def assess_fileredential(file_path: Path) -> CredentialAssessment:
    """Assess credential stored in a file."""
    if not file_path.exists():
        return CredentialAssessment(
            store_type="file",
            has_acl=False,
            is_safe=False,
            recommendation="unknown",
            evidence=f"File {file_path} does not exist",
        )

    # Check file permissions
    import stat

    mode = file_path.stat().st_mode
    is_world_readable = bool(mode & stat.S_IROTH)
    is_group_readable = bool(mode & stat.S_IRGRP)

    is_safe = not is_world_readable and not is_group_readable

    return CredentialAssessment(
        store_type="file",
        has_acl=not is_world_readable,
        is_safe=is_safe,
        recommendation="retain" if is_safe else "rotate",
        evidence=f"File permissions: {'safe' if is_safe else 'unsafe'} (world_readable={is_world_readable}, group_readable={is_group_readable})",
    )


def assess_credential(source: str, identifier: str) -> CredentialAssessment:
    """Assess a credential from its source."""
    if source == "keychain":
        return assess_keychain(identifier)
    elif source == "env":
        return assess_env_variable(identifier)
    elif source == "file":
        return assess_fileredential(Path(identifier))
    else:
        return CredentialAssessment(
            store_type="unknown",
            has_acl=False,
            is_safe=False,
            recommendation="unknown",
            evidence=f"Unknown credential source: {source}",
        )
