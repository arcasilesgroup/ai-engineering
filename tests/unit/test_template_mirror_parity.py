"""Ensure canonical governance and template mirror stay in sync."""

from __future__ import annotations

import hashlib

from ai_engineering.paths import repo_root, template_root


def test_template_mirror_matches_canonical_non_state_files() -> None:
    root = repo_root()
    canonical_root = root / ".ai-engineering"
    mirror_root = template_root() / ".ai-engineering"

    canonical = {
        path.relative_to(canonical_root).as_posix(): path
        for path in canonical_root.rglob("*")
        if path.is_file() and not path.relative_to(canonical_root).as_posix().startswith("state/")
    }
    mirror = {
        path.relative_to(mirror_root).as_posix(): path
        for path in mirror_root.rglob("*")
        if path.is_file() and not path.relative_to(mirror_root).as_posix().startswith("state/")
    }

    assert set(canonical) == set(mirror)

    for rel_path in sorted(canonical):
        canonical_hash = hashlib.sha256(canonical[rel_path].read_bytes()).hexdigest()
        mirror_hash = hashlib.sha256(mirror[rel_path].read_bytes()).hexdigest()
        assert canonical_hash == mirror_hash, f"mirror mismatch: {rel_path}"
