"""Project identity initialisation for consumer installs.

The framework template ships neutral defaults, but an installed consumer
project must identify as the repository it lives in -- never as the
framework repository that produced the template.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from ai_engineering.config.loader import update_manifest_field

logger = logging.getLogger(__name__)

_TEMPLATE_PROJECT_NAME = "ai-engineering"
_EMPTY_PROJECT_NAME = ""


def project_name_from_root(target: Path) -> str:
    """Return the default consumer project name for an install target."""
    name = target.name or target.resolve().name
    return name or "project"


def _read_manifest_name(manifest_path: Path) -> str:
    """Read the raw manifest ``name`` value without applying defaults."""
    try:
        data: Any = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        logger.debug("cannot read manifest name from %s: %s", manifest_path, exc)
        return _EMPTY_PROJECT_NAME
    if not isinstance(data, dict):
        return _EMPTY_PROJECT_NAME
    raw = data.get("name")
    return raw.strip() if isinstance(raw, str) else _EMPTY_PROJECT_NAME


def initialize_manifest_project_name(target: Path, *, force: bool = False) -> bool:
    """Initialise ``manifest.yml`` name from the target root directory.

    Returns ``True`` when the file was updated. Existing non-template names
    are preserved unless ``force`` is true.
    """
    manifest_path = target / ".ai-engineering" / "manifest.yml"
    if not manifest_path.is_file():
        return False

    current = _read_manifest_name(manifest_path)
    if not force and current not in {_EMPTY_PROJECT_NAME, _TEMPLATE_PROJECT_NAME}:
        return False

    try:
        update_manifest_field(target, "name", project_name_from_root(target))
    except (FileNotFoundError, KeyError, OSError, yaml.YAMLError) as exc:
        logger.debug("cannot initialise manifest project name at %s: %s", manifest_path, exc)
        return False
    return True
