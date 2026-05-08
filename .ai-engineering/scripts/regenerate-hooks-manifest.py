#!/usr/bin/env python3
"""Regenerate the committed hook integrity manifest (spec-115 G-1).

Walks ``.ai-engineering/scripts/hooks/`` recursively, hashes every
``*.py`` / ``*.sh`` / ``*.ps1`` file (excluding the ``_lib/__init__.py``
stub which is dev-managed), and writes the canonical sha256 mapping to
``.ai-engineering/state/hooks-manifest.json``.

Run after any intentional edit to a hook script. The CI pipeline should
reject commits that change a hook script without bumping the manifest;
``ai-eng doctor --check hooks-manifest`` (added in the same spec) reads
this file to flag drift.

Usage:
    python3 .ai-engineering/scripts/regenerate-hooks-manifest.py [--check]

``--check`` exits non-zero if the on-disk manifest is stale (writes
nothing). Suitable for pre-commit / CI use.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
HOOKS_DIR = SCRIPT_DIR / "hooks"
MANIFEST_PATH = REPO_ROOT / ".ai-engineering" / "state" / "hooks-manifest.json"
SCHEMA_VERSION = "1.0"
INCLUDE_SUFFIXES = {".py", ".sh", ".ps1"}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _enumerate_hooks() -> list[Path]:
    if not HOOKS_DIR.is_dir():
        return []
    files: list[Path] = []
    for path in sorted(HOOKS_DIR.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in INCLUDE_SUFFIXES:
            continue
        # Skip dev-managed stubs that legitimately mutate (lazy import shim).
        rel = path.relative_to(REPO_ROOT)
        if rel.name == "__init__.py" and rel.parent.name == "_lib":
            continue
        files.append(path)
    return files


def _build_manifest() -> dict:
    hooks: dict[str, str] = {}
    for path in _enumerate_hooks():
        rel = str(path.relative_to(REPO_ROOT))
        hooks[rel] = _sha256_file(path)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hookCount": len(hooks),
        "hooks": hooks,
    }


def _read_existing() -> dict | None:
    if not MANIFEST_PATH.exists():
        return None
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _hooks_equal(current: dict, existing: dict | None) -> bool:
    if not isinstance(existing, dict):
        return False
    return current.get("hooks") == existing.get("hooks")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if the on-disk manifest is stale; write nothing.",
    )
    args = parser.parse_args(argv)

    existing = _read_existing()
    new_manifest = _build_manifest()

    # Preserve `generatedAt` when content is unchanged. Otherwise every
    # regenerate run produces a 1-line diff (timestamp only) and pre-commit
    # auto-regeneration creates no-op commits.
    if _hooks_equal(new_manifest, existing) and isinstance(existing, dict):
        prior_ts = existing.get("generatedAt")
        if isinstance(prior_ts, str):
            new_manifest["generatedAt"] = prior_ts

    if args.check:
        if _hooks_equal(new_manifest, existing):
            print(f"hooks-manifest OK ({new_manifest['hookCount']} hooks)")
            return 0
        print(
            "hooks-manifest STALE -- run "
            "`python3 .ai-engineering/scripts/regenerate-hooks-manifest.py`",
            file=sys.stderr,
        )
        return 1

    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(new_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {MANIFEST_PATH.relative_to(REPO_ROOT)} ({new_manifest['hookCount']} hooks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
