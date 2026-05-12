#!/usr/bin/env python3
"""Generate ``<prefix>/<slug>`` branch name from spec.md frontmatter (brief §17).

No LLM. Reads ``.ai-engineering/specs/spec.md`` frontmatter, extracts
``id`` (or ``spec_id``) and ``title`` (or ``slug``) fields, returns a
kebab-case branch slug capped at 50 chars.

Default prefix is ``feat/``; override with ``--prefix fix|chore|docs``
etc. Stdlib + pyyaml only.

Usage:

```
python3 .ai-engineering/scripts/branch_slug.py
# stdout:  feat/spec-127-skill-agent-rubric

python3 .ai-engineering/scripts/branch_slug.py --prefix fix
# stdout:  fix/spec-127-skill-agent-rubric
```
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover
    yaml = None  # type: ignore[assignment]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SPEC_PATH = _REPO_ROOT / ".ai-engineering" / "specs" / "spec.md"
_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_SLUG_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_VALID_PREFIXES = ("feat", "fix", "chore", "docs", "refactor", "perf", "test", "build", "ci")
MAX_SLUG_LEN = 50


def _slugify(text: str) -> str:
    """Convert ``text`` to kebab-case lowercase. Empty when only punctuation."""
    text = text.strip().lower()
    text = _SLUG_NON_ALNUM.sub("-", text)
    text = text.strip("-")
    return text


def _read_frontmatter(spec_path: Path) -> dict | None:
    """Parse the YAML frontmatter from ``spec.md``; None on missing/invalid."""
    if not spec_path.is_file() or yaml is None:
        return None
    try:
        text = spec_path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _FRONTMATTER_RE.search(text)
    if not match:
        return None
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return None
    return fm if isinstance(fm, dict) else None


def compose_branch(prefix: str, frontmatter: dict | None) -> str:
    """Compose ``<prefix>/<slug>`` capped at MAX_SLUG_LEN total length.

    Slug parts (joined with ``-``):
      1. ``spec-<id>`` if ``id`` / ``spec_id`` present.
      2. ``slugify(title)`` if ``title`` / ``slug`` present.

    Falls back to ``<prefix>/work`` when no usable frontmatter.
    """
    if prefix not in _VALID_PREFIXES:
        raise ValueError(f"prefix {prefix!r} not in {_VALID_PREFIXES}")

    if not frontmatter:
        return f"{prefix}/work"

    parts: list[str] = []
    spec_id = frontmatter.get("id") or frontmatter.get("spec_id")
    if spec_id is not None:
        sid = str(spec_id).strip()
        if sid:
            # Accept either ``127`` or ``spec-127`` shaped IDs.
            sid_norm = sid if sid.startswith("spec-") else f"spec-{sid}"
            parts.append(_slugify(sid_norm))

    title = frontmatter.get("slug") or frontmatter.get("title")
    if isinstance(title, str) and title.strip():
        slugged = _slugify(title)
        if slugged:
            parts.append(slugged)

    if not parts:
        return f"{prefix}/work"

    body = "-".join(parts).strip("-")
    # Cap to MAX_SLUG_LEN total (prefix + ``/`` + body).
    overhead = len(prefix) + 1
    if len(body) + overhead > MAX_SLUG_LEN:
        body = body[: MAX_SLUG_LEN - overhead].rstrip("-")
    return f"{prefix}/{body}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="branch_slug",
        description="Compose <prefix>/<slug> branch name from spec.md frontmatter.",
    )
    parser.add_argument(
        "--prefix",
        default="feat",
        choices=_VALID_PREFIXES,
        help="Conventional commit type prefix (default: feat).",
    )
    parser.add_argument(
        "--spec-path",
        type=Path,
        default=_SPEC_PATH,
        help="Path to spec.md (default: .ai-engineering/specs/spec.md).",
    )
    args = parser.parse_args(argv)

    fm = _read_frontmatter(args.spec_path)
    branch = compose_branch(args.prefix, fm)
    sys.stdout.write(branch)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
