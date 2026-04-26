"""Gate cache (spec-104 D-104-03, D-104-09)."""

from __future__ import annotations

import hashlib

# D-104-09: per-check whitelist of config files whose hash invalidates the cache.
_CONFIG_FILE_WHITELIST: dict[str, list[str]] = {
    "ruff-format": ["pyproject.toml", ".ruff.toml", "ruff.toml"],
    "ruff-check": ["pyproject.toml", ".ruff.toml", "ruff.toml"],
    "gitleaks": [".gitleaks.toml", "gitleaks.toml"],
    "ty": ["pyproject.toml", ".ai-engineering/manifest.yml"],
    "pytest-smoke": ["pyproject.toml", "pytest.ini", "conftest.py"],
    "validate": [".ai-engineering/manifest.yml"],
    "spec-verify": [".ai-engineering/specs/spec.md", ".ai-engineering/specs/plan.md"],
    "docs-gate": [".ai-engineering/manifest.yml"],
}


def _compute_cache_key(
    check_name: str,
    args: list[str],
    staged_blob_shas: list[str],
    tool_version: str,
    config_file_hashes: dict[str, str],
) -> str:
    """Deterministic 32-char hex cache key for a gate check invocation.

    Inputs are sorted before hashing to make ordering irrelevant.
    """
    parts = [
        check_name,
        tool_version,
        "|".join(sorted(staged_blob_shas)),
        "|".join(f"{k}:{v}" for k, v in sorted(config_file_hashes.items())),
        "|".join(sorted(args)),
    ]
    payload = " ".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:32]
