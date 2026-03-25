"""YAML loader for the project manifest.

Provides ``load_manifest_config`` which reads
``.ai-engineering/manifest.yml``, parses it with ``yaml.safe_load``,
and validates the result through :class:`ManifestConfig`.

If the file is missing or empty, a default ``ManifestConfig`` is
returned so callers never need to guard against ``None``.
"""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

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

    raw = manifest_path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)

    if not isinstance(data, dict):
        logger.debug("Manifest at %s is empty or non-mapping, returning defaults", manifest_path)
        return ManifestConfig()

    return ManifestConfig.model_validate(data)
