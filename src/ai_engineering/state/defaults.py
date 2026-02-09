"""Default system-managed state payloads for installer bootstrap."""

from __future__ import annotations

from datetime import datetime, timezone


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def install_manifest_default(framework_version: str) -> dict:
    """Return default install-manifest.json payload."""
    return {
        "schemaVersion": "1.1",
        "updateMetadata": {
            "rationale": "initialize system-managed installation contract",
            "expectedGain": "consistent readiness tracking",
            "potentialImpact": "installer and doctor must maintain this file",
        },
        "frameworkVersion": framework_version,
        "installedAt": _now_iso(),
        "installedStacks": ["python"],
        "installedIdes": ["terminal", "vscode", "claude", "codex", "copilot"],
        "providers": {
            "vcs": {
                "primary": "github",
                "enabled": ["github"],
                "extensions": {
                    "azure_devops": {
                        "enabled": False,
                        "organization": None,
                        "project": None,
                        "repository": None,
                    }
                },
            }
        },
        "toolingReadiness": {
            "gh": {"installed": False, "configured": False, "authenticated": False},
            "az": {
                "installed": False,
                "configured": False,
                "authenticated": False,
                "requiredNow": False,
            },
            "gitHooks": {"installed": False, "integrityVerified": False},
            "python": {
                "uv": {"ready": False},
                "ruff": {"ready": False},
                "ty": {"ready": False},
                "pipAudit": {"ready": False},
            },
        },
    }


def ownership_map_default() -> dict:
    """Return default ownership-map.json payload."""
    return {
        "schemaVersion": "1.0",
        "updateMetadata": {
            "rationale": "enforce path-level ownership for safe updates",
            "expectedGain": "no accidental overwrite of team or project content",
            "potentialImpact": "updater must validate every path write",
        },
        "paths": [
            {
                "pattern": ".ai-engineering/standards/framework/**",
                "owner": "framework-managed",
                "frameworkUpdate": "allow",
            },
            {
                "pattern": ".ai-engineering/standards/team/**",
                "owner": "team-managed",
                "frameworkUpdate": "deny",
            },
            {
                "pattern": ".ai-engineering/context/**",
                "owner": "project-managed",
                "frameworkUpdate": "deny",
            },
            {
                "pattern": ".ai-engineering/skills/**",
                "owner": "framework-managed",
                "frameworkUpdate": "allow",
            },
            {
                "pattern": "CLAUDE.md",
                "owner": "framework-managed",
                "frameworkUpdate": "allow",
            },
            {
                "pattern": "codex.md",
                "owner": "framework-managed",
                "frameworkUpdate": "allow",
            },
            {
                "pattern": ".github/copilot-instructions.md",
                "owner": "framework-managed",
                "frameworkUpdate": "allow",
            },
            {
                "pattern": ".github/copilot/**",
                "owner": "framework-managed",
                "frameworkUpdate": "allow",
            },
            {
                "pattern": ".ai-engineering/state/install-manifest.json",
                "owner": "system-managed",
                "frameworkUpdate": "allow",
            },
            {
                "pattern": ".ai-engineering/state/ownership-map.json",
                "owner": "system-managed",
                "frameworkUpdate": "allow",
            },
            {
                "pattern": ".ai-engineering/state/sources.lock.json",
                "owner": "system-managed",
                "frameworkUpdate": "allow",
            },
            {
                "pattern": ".ai-engineering/state/decision-store.json",
                "owner": "system-managed",
                "frameworkUpdate": "allow",
            },
            {
                "pattern": ".ai-engineering/state/audit-log.ndjson",
                "owner": "system-managed",
                "frameworkUpdate": "append-only",
            },
        ],
    }


def sources_lock_default() -> dict:
    """Return default sources.lock.json payload."""
    source_template = {
        "trusted": True,
        "checksum": None,
        "signatureMetadata": {
            "algorithm": None,
            "keyId": None,
            "signature": None,
            "verified": False,
        },
        "cache": {"ttlHours": 24, "lastFetchedAt": None},
    }
    return {
        "schemaVersion": "1.0",
        "updateMetadata": {
            "rationale": "lock trusted remote skill sources and integrity metadata",
            "expectedGain": "deterministic and safer skill resolution",
            "potentialImpact": "source updates require lock refresh",
        },
        "generatedAt": _now_iso(),
        "defaultRemoteEnabled": True,
        "sources": [
            {"url": "https://skills.sh/", **source_template},
            {"url": "https://www.aitmpl.com/skills", **source_template},
        ],
    }


def decision_store_default() -> dict:
    """Return default decision-store.json payload."""
    return {
        "schemaVersion": "1.0",
        "updateMetadata": {
            "rationale": "persist risk and flow decisions for prompt reuse",
            "expectedGain": "lower prompt fatigue and stronger auditability",
            "potentialImpact": "decision expiry and context-hash logic becomes mandatory",
        },
        "decisions": [],
    }
