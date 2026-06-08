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
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent.parent
HOOKS_DIR = SCRIPT_DIR / "hooks"
MANIFEST_PATH = REPO_ROOT / ".ai-engineering" / "state" / "hooks-manifest.json"
SCHEMA_VERSION = "1.0"
INCLUDE_SUFFIXES = {".py", ".sh", ".ps1"}

# spec-131 sub-004 T-4.D: trusted-script lane.
#
# ``TRUSTED_SCRIPTS`` — repo-relative paths to scripts that legitimately
# bypass RTK rewriting and IOC re-evaluation of their inner subprocesses.
# Bytes are hash-pinned in the manifest so any drift produces an integrity
# failure (R-131-07 mitigation).
#
# ``TRUSTED_ARGVS`` — literal Bash argv forms the prompt-injection-guard
# matches against to short-circuit the IOC + injection scans. Dual-key
# enforcement (sha256 + literal form) closes the bypass via
# ``bash -c "..."`` or via byte modification.
#
# ``session_bootstrap.py`` enrolment (spec-132 T-2 / operator-pain #18b):
# the trusted-script lane was wired in spec-131 sub-004 but the
# bootstrap script was left out — sub-agents dispatched from /ai-start
# kept tripping the IOC scan instead of bypassing it. Pinning both the
# bytes (sha256) and the literal argv form closes pain #16/#18b.
TRUSTED_SCRIPTS: list[Path] = [
    Path(".ai-engineering/scripts/hooks/no-verify-guard.py"),
    Path(".ai-engineering/scripts/session_bootstrap.py"),
]
TRUSTED_ARGVS: list[str] = [
    "uv run python .ai-engineering/scripts/session_bootstrap.py",
    "uv run python .ai-engineering/scripts/session_bootstrap.py --format=markdown",
    "uv run python .ai-engineering/scripts/session_bootstrap.py --format=json",
]


def _sha256_file(path: Path) -> str:
    # Normalise CRLF -> LF before hashing so the manifest stays portable
    # across Windows / Linux / macOS checkouts regardless of whether the
    # runner honoured `.gitattributes` eol=lf. Hash is byte-identical for
    # LF-only files; only Windows-CRLF checkouts get normalised.
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


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


def _build_trusted_scripts() -> dict[str, str]:
    """Hash every entry in :data:`TRUSTED_SCRIPTS` (sorted for stability).

    Missing files are silently skipped — the regenerator should never fail
    just because a trusted script has not yet landed (sub-003 follow-up
    lands ``session_bootstrap.py`` independently). Operators who add a
    typo to ``TRUSTED_SCRIPTS`` will notice the gap immediately via the
    test fixture ``test_trusted_script_lane_manifest.py``.
    """
    out: dict[str, str] = {}
    for rel in sorted(p.as_posix() for p in TRUSTED_SCRIPTS):
        abs_path = REPO_ROOT / rel
        if not abs_path.is_file():
            continue
        out[rel] = _sha256_file(abs_path)
    return out


def _build_manifest() -> dict:
    hooks: dict[str, str] = {}
    for path in _enumerate_hooks():
        # POSIX-style key so the manifest is cross-platform identical
        # regardless of which OS regenerated it.
        rel = path.relative_to(REPO_ROOT).as_posix()
        hooks[rel] = _sha256_file(path)
    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": datetime.now(tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hookCount": len(hooks),
        "hooks": hooks,
        # spec-131 sub-004 T-4.D additive keys (backwards-compatible).
        "trustedScripts": _build_trusted_scripts(),
        "trustedArgvs": list(TRUSTED_ARGVS),
    }


def _read_existing() -> dict | None:
    if not MANIFEST_PATH.exists():
        return None
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return None


def _manifests_equal(current: dict, existing: dict | None) -> bool:
    """Compare ``hooks`` AND the spec-131 trusted-script keys.

    Returns False on any drift across the three load-bearing keys; the
    ``generatedAt`` and ``hookCount`` fields are ignored so a no-op
    regenerate produces no commit diff.
    """
    if not isinstance(existing, dict):
        return False
    if current.get("hooks") != existing.get("hooks"):
        return False
    if current.get("trustedScripts", {}) != existing.get("trustedScripts", {}):
        return False
    return list(current.get("trustedArgvs", [])) == list(existing.get("trustedArgvs", []))


# Back-compat alias for callers that imported the previous helper name.
_hooks_equal = _manifests_equal


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
    if _manifests_equal(new_manifest, existing) and isinstance(existing, dict):
        prior_ts = existing.get("generatedAt")
        if isinstance(prior_ts, str):
            new_manifest["generatedAt"] = prior_ts

    if args.check:
        if _manifests_equal(new_manifest, existing):
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
