"""Test the /ai-simplify-sweep skill is present, well-formed, and registered.

(Renamed from ai-entropy-gc per spec-127 D-127-04 / sub-005 M4.)

Three contracts:
  1. ``.claude/skills/ai-simplify-sweep/SKILL.md`` exists at the repo root.
  2. The frontmatter is valid YAML and carries the required keys
     (``name``, ``description``, plus the canonical ``model``,
     ``color``, ``tools``, ``tags``).
  3. The skill is registered in ``.ai-engineering/manifest.yml`` under
     ``skills.registry.ai-simplify-sweep`` and the ``skills.total`` counter
     matches the registry length.
"""

from __future__ import annotations

import re
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[2]
SKILL_PATH = REPO / ".claude" / "skills" / "ai-simplify-sweep" / "SKILL.md"
MANIFEST_PATH = REPO / ".ai-engineering" / "manifest.yml"


def _parse_frontmatter(text: str) -> dict[str, object]:
    """Pull the ``---``-delimited YAML block at the top of the file."""
    match = re.match(r"^---\n(.*?)\n---", text, flags=re.DOTALL)
    assert match is not None, "SKILL.md must start with a ``---`` frontmatter block"
    parsed = yaml.safe_load(match.group(1))
    assert isinstance(parsed, dict), "frontmatter must be a YAML mapping"
    return parsed


def test_skill_file_exists() -> None:
    assert SKILL_PATH.is_file(), (
        f"/ai-simplify-sweep SKILL.md must exist at {SKILL_PATH}. "
        "It is the canonical source for the scheduled simplify wrapper."
    )


def test_skill_frontmatter_is_valid() -> None:
    text = SKILL_PATH.read_text(encoding="utf-8")
    fm = _parse_frontmatter(text)

    assert fm.get("name") == "ai-simplify-sweep"
    description = fm.get("description")
    assert isinstance(description, str) and description.strip()
    # Canonical SKILL.md frontmatter keys (sub-003 / sub-005 baseline).
    # `model`/`color`/`tools` live in the paired agent .md, not the SKILL.md.
    for required_key in ("effort", "tags"):
        assert required_key in fm, f"frontmatter missing required key: {required_key!r}"
    tags = fm.get("tags")
    assert isinstance(tags, list) and tags, "tags must be a non-empty list"


def test_skill_registered_in_manifest() -> None:
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(manifest, dict)
    skills = manifest.get("skills") or {}
    registry = skills.get("registry") or {}
    assert isinstance(registry, dict)
    assert "ai-simplify-sweep" in registry, (
        "ai-simplify-sweep must be registered in manifest.yml under skills.registry."
    )
    entry = registry["ai-simplify-sweep"]
    assert isinstance(entry, dict)
    assert entry.get("type") == "meta"
    assert isinstance(entry.get("tags"), list) and entry["tags"]


def test_manifest_total_matches_registry_size() -> None:
    """``skills.total`` must equal ``len(registry)`` so the registry stays honest."""
    manifest = yaml.safe_load(MANIFEST_PATH.read_text(encoding="utf-8"))
    skills = manifest.get("skills") or {}
    registry = skills.get("registry") or {}
    total = skills.get("total")
    assert isinstance(total, int)
    assert total == len(registry), (
        f"skills.total ({total}) must match registry length ({len(registry)}); "
        "either bump total or add the missing entry."
    )
