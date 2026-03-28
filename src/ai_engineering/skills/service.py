"""Local skill eligibility diagnostics.

Evaluates which skills in `.claude/skills/`, `.codex/skills/`, `.gemini/skills/`, or
legacy `.ai-engineering/skills/` meet their runtime requirements
(binaries, environment variables, config paths, OS).
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

import yaml

from ai_engineering.config.loader import load_manifest_config

_logger = logging.getLogger(__name__)


@dataclass
class SkillStatus:
    """Eligibility status for a local governance skill."""

    name: str
    file_path: str
    eligible: bool
    missing_bins: list[str] = field(default_factory=list)
    missing_any_bins: list[str] = field(default_factory=list)
    missing_env: list[str] = field(default_factory=list)
    missing_config: list[str] = field(default_factory=list)
    missing_os: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _collect_skill_files(skills_root: Path, *, include_flat_files: bool = False) -> list[Path]:
    """Collect skill definition files from a single skills directory."""
    if not skills_root.is_dir():
        return []
    # Directory-based: skills/<name>/SKILL.md
    # Legacy file-based: skills/<category>/<name>.md
    skill_files: list[Path] = []
    skill_files.extend(sorted(skills_root.rglob("SKILL.md")))
    if include_flat_files:
        for category_dir in sorted(skills_root.iterdir()):
            if category_dir.is_dir():
                for md in sorted(category_dir.glob("*.md")):
                    if md.is_file() and md.name != "SKILL.md":
                        skill_files.append(md)
    return skill_files


# Skill directories to scan, in priority order.
_SKILL_DIRS: list[str] = [
    ".claude/skills",
    ".codex/skills",
    ".gemini/skills",
    ".ai-engineering/skills",  # legacy, backwards compat
]


def list_local_skill_status(target: Path) -> list[SkillStatus]:
    """Evaluate local skill requirement eligibility.

    Scans ``.claude/skills/``, ``.codex/skills/``, ``.gemini/skills/``,
    and legacy ``.ai-engineering/skills/`` for SKILL.md files.
    """
    manifest = load_manifest_config(target).model_dump()
    install_state = _safe_json_load(target / ".ai-engineering" / "state" / "install-state.json")
    config_roots = [manifest, install_state]

    # Collect skill files from all known directories.
    seen_paths: set[Path] = set()
    skill_files: list[Path] = []
    for rel_dir in _SKILL_DIRS:
        include_flat_files = rel_dir == ".ai-engineering/skills"
        for sf in _collect_skill_files(target / rel_dir, include_flat_files=include_flat_files):
            resolved = sf.resolve()
            if resolved not in seen_paths:
                seen_paths.add(resolved)
                skill_files.append(sf)

    statuses: list[SkillStatus] = []
    for skill_file in skill_files:
        rel = skill_file.relative_to(target).as_posix()
        frontmatter, errors = _load_skill_frontmatter(skill_file)

        name = str(frontmatter.get("name") or skill_file.stem)
        requires_raw = frontmatter.get("requires") if isinstance(frontmatter, dict) else {}
        requires: dict[str, object] = (
            cast(dict[str, object], requires_raw) if isinstance(requires_raw, dict) else {}
        )

        bins = _ensure_str_list(requires.get("bins"))
        any_bins = _ensure_str_list(requires.get("anyBins"))
        env_vars = _ensure_str_list(requires.get("env"))
        config_paths = _ensure_str_list(requires.get("config"))
        os_required = _ensure_str_list(frontmatter.get("os"))

        missing_bins = [bin_name for bin_name in bins if not shutil.which(bin_name)]
        missing_any_bins = []
        if any_bins and not any(shutil.which(bin_name) for bin_name in any_bins):
            missing_any_bins = any_bins
        missing_env = [env_name for env_name in env_vars if not os.environ.get(env_name)]
        missing_config = [
            path
            for path in config_paths
            if not any(_config_path_truthy(root, path) for root in config_roots)
        ]
        missing_os = []
        if os_required and not _platform_matches(os_required):
            missing_os = os_required

        eligible = not (
            errors
            or missing_bins
            or missing_any_bins
            or missing_env
            or missing_config
            or missing_os
        )

        statuses.append(
            SkillStatus(
                name=name,
                file_path=rel,
                eligible=eligible,
                missing_bins=missing_bins,
                missing_any_bins=missing_any_bins,
                missing_env=missing_env,
                missing_config=missing_config,
                missing_os=missing_os,
                errors=errors,
            )
        )

    return statuses


def _safe_yaml_load(path: Path) -> dict[str, object]:
    """Read YAML file into dict; return empty dict on failure."""
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def _safe_json_load(path: Path) -> dict[str, object]:
    """Read JSON file into dict; return empty dict on failure."""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _ensure_str_list(value: object) -> list[str]:
    """Normalize potentially-invalid list values to list[str]."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _load_skill_frontmatter(path: Path) -> tuple[dict[str, object], list[str]]:
    """Parse SKILL markdown frontmatter and return errors if invalid."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return {}, [f"read-failed: {exc}"]

    if not text.startswith("---\n"):
        return {}, ["missing-frontmatter"]

    end = text.find("\n---\n", 4)
    if end == -1:
        return {}, ["unterminated-frontmatter"]

    block = text[4:end]
    try:
        parsed = yaml.safe_load(block) or {}
    except yaml.YAMLError as exc:
        return {}, [f"invalid-frontmatter-yaml: {exc}"]

    if not isinstance(parsed, dict):
        return {}, ["frontmatter-not-mapping"]
    return parsed, []


def _config_path_truthy(root: dict[str, object], dotted_path: str) -> bool:
    """Evaluate dotted config path against mapping-like config data."""
    if not dotted_path:
        return False

    current: object = root
    for part in dotted_path.split("."):
        if not isinstance(current, dict):
            return False
        current = current.get(part)
    return bool(current)


def _platform_matches(required: list[str]) -> bool:
    """Check if current platform identifier matches required list."""
    platform = sys.platform.lower()
    if platform.startswith("darwin"):
        platform = "darwin"
    elif platform.startswith("win"):
        platform = "win32"
    elif platform.startswith("linux"):
        platform = "linux"
    return platform in required
