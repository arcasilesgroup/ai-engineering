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

from ai_engineering.config.manifest import ManifestConfig

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

    return ManifestConfig.model_validate(data)


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
