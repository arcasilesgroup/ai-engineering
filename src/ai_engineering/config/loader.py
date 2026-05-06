"""YAML loader and writer for the project manifest.

Provides ``load_manifest_config`` which reads
``.ai-engineering/manifest.yml``, parses it with ``yaml.safe_load``,
and validates the result through :class:`ManifestConfig`.

Provides ``update_manifest_field`` which updates a specific field
in ``manifest.yml`` using ``ruamel.yaml`` round-trip mode to
preserve comments and formatting.

If the file is missing or empty, a default ``ManifestConfig`` is
returned so callers never need to guard against ``None``.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml
from ruamel.yaml import YAML

from ai_engineering.config.manifest import ManifestConfig, RootEntryPointConfig

logger = logging.getLogger(__name__)

_MANIFEST_REL = Path(".ai-engineering") / "manifest.yml"


def load_manifest_config(root: Path) -> ManifestConfig:
    """Read and validate the project manifest.

    Parameters
    ----------
    root:
        Repository root directory containing ``.ai-engineering/``.

    Returns
    -------
    ManifestConfig
        Validated config. Returns all-defaults if the file is missing
        or empty.
    """
    manifest_path = root / _MANIFEST_REL

    if not manifest_path.is_file():
        logger.debug("Manifest not found at %s, returning defaults", manifest_path)
        return ManifestConfig()

    try:
        raw = manifest_path.read_text(encoding="utf-8")
        data = yaml.safe_load(raw)
    except (OSError, yaml.YAMLError) as exc:
        logger.debug("Failed to read manifest at %s (%s), returning defaults", manifest_path, exc)
        return ManifestConfig()

    if not isinstance(data, dict):
        logger.debug("Manifest at %s is empty or non-mapping, returning defaults", manifest_path)
        return ManifestConfig()

    # Migration: derive ai_providers from providers.ides when absent
    if "ai_providers" not in data:
        _migrate_ai_providers(data)

    # Spec-124 D-124-01: translate legacy underscore IDE keys to hyphenated form.
    _migrate_legacy_ide_keys(data)

    return ManifestConfig.model_validate(data)


def load_manifest_root_entry_points(root: Path) -> dict[str, RootEntryPointConfig] | None:
    """Load governed root-entry metadata when a manifest file is present.

    Returns ``None`` when the manifest file does not exist so callers can
    preserve backward-compatible fallback behavior that distinguishes
    "manifest absent" from "manifest present but empty/defaulted".
    """
    manifest_path = root / _MANIFEST_REL
    if not manifest_path.is_file():
        logger.debug("Manifest not found at %s, root entry points unavailable", manifest_path)
        return None

    return load_manifest_config(root).ownership.root_entry_points


# Known AI provider identifiers (mirrored from operations.py).
_AI_PROVIDER_IDS: frozenset[str] = frozenset(
    {"claude-code", "github-copilot", "gemini-cli", "codex"}
)

# Spec-124 D-124-01: backwards-compat read shim translating old underscore
# IDE keys to the new hyphenated vendor-product form.  Removal tracked in
# spec-125.
_LEGACY_IDE_KEY_MAP: dict[str, str] = {
    "claude_code": "claude-code",
    "github_copilot": "github-copilot",
    "copilot": "github-copilot",
    "gemini": "gemini-cli",
}


def _translate_ide_keys(values: list[Any]) -> tuple[list[Any], bool]:
    """Translate legacy underscore IDE keys to hyphenated form.

    Returns the (possibly rewritten) list plus a flag indicating
    whether at least one key was migrated, so callers can emit a
    one-shot WARN.
    """
    translated: list[Any] = []
    migrated = False
    for value in values:
        if isinstance(value, str) and value in _LEGACY_IDE_KEY_MAP:
            translated.append(_LEGACY_IDE_KEY_MAP[value])
            migrated = True
        else:
            translated.append(value)
    return translated, migrated


def _migrate_legacy_ide_keys(data: dict[str, Any]) -> None:
    """Rewrite legacy IDE-key string literals in-place.

    Touches ``providers.ides``, ``ai_providers.enabled``, and
    ``ai_providers.primary``.  Emits a single WARN log when any value
    was translated so operators know to update ``manifest.yml``.
    Removal tracked in spec-125.
    """
    migrated = False

    providers = data.get("providers")
    if isinstance(providers, dict):
        ides = providers.get("ides")
        if isinstance(ides, list):
            new_ides, did_migrate = _translate_ide_keys(ides)
            if did_migrate:
                providers["ides"] = new_ides
                migrated = True

    ai_providers = data.get("ai_providers")
    if isinstance(ai_providers, dict):
        enabled = ai_providers.get("enabled")
        if isinstance(enabled, list):
            new_enabled, did_migrate = _translate_ide_keys(enabled)
            if did_migrate:
                ai_providers["enabled"] = new_enabled
                migrated = True
        primary = ai_providers.get("primary")
        if isinstance(primary, str) and primary in _LEGACY_IDE_KEY_MAP:
            ai_providers["primary"] = _LEGACY_IDE_KEY_MAP[primary]
            migrated = True

    if migrated:
        logger.warning(
            "manifest IDE keys updated to hyphenated form per spec-124; "
            "please update your manifest.yml"
        )


def _migrate_ai_providers(data: dict[str, Any]) -> None:
    """Derive ``ai_providers`` from legacy ``providers.ides`` entries.

    AI provider entries are moved to ``ai_providers.enabled`` and the
    first becomes ``primary``.  Non-AI entries remain in
    ``providers.ides``.  The ``ai_providers`` dict is injected into
    *data* in-place.
    """
    providers = data.get("providers")
    if not isinstance(providers, dict):
        return

    ides = providers.get("ides")
    if not isinstance(ides, list):
        return

    ai_entries = [i for i in ides if i in _AI_PROVIDER_IDS]
    non_ai_entries = [i for i in ides if i not in _AI_PROVIDER_IDS]

    if ai_entries:
        data["ai_providers"] = {
            "enabled": ai_entries,
            "primary": ai_entries[0],
        }
        providers["ides"] = non_ai_entries


def update_manifest_field(root: Path, field_path: str, value: Any) -> None:
    """Update a specific field in manifest.yml preserving comments.

    Uses ``ruamel.yaml`` round-trip mode so existing comments, blank
    lines, and key ordering are retained after the write.

    Parameters
    ----------
    root:
        Repository root directory containing ``.ai-engineering/``.
    field_path:
        Dot-separated path to the target field, e.g.
        ``"providers.stacks"`` or ``"work_items.provider"``.
    value:
        The new value to assign.  Must be a type that ruamel.yaml
        can serialize (scalars, lists, dicts).

    Raises
    ------
    FileNotFoundError
        If ``manifest.yml`` does not exist.
    KeyError
        If an intermediate key in *field_path* is missing from the
        YAML document.
    """
    manifest_path = root / _MANIFEST_REL

    if not manifest_path.is_file():
        msg = f"Manifest not found at {manifest_path}"
        raise FileNotFoundError(msg)

    rt_yaml = YAML(typ="rt")
    rt_yaml.preserve_quotes = True

    with manifest_path.open(encoding="utf-8") as fh:
        data = rt_yaml.load(fh)

    keys = field_path.split(".")
    target = data
    for key in keys[:-1]:
        if key not in target:
            msg = f"Key '{key}' not found while navigating '{field_path}'"
            raise KeyError(msg)
        target = target[key]

    final_key = keys[-1]
    if final_key not in target:
        msg = f"Key '{final_key}' not found while navigating '{field_path}'"
        raise KeyError(msg)

    target[final_key] = value

    with manifest_path.open("w", encoding="utf-8") as fh:
        rt_yaml.dump(data, fh)
