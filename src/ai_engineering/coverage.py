"""Coverage rules separated from prompts, spec 030 / B-030-2.

What a guard may scan is declared as data — `policy/coverage/<guard>.toml` naming the roots
it may read — and read by the guard at run time. Adjusting coverage is a one-file data
change that never touches the guard's reasoning text. A guard scanning outside its declared
coverage is INCOMPLETE, never silently widened, and a declared root that escapes the
repository is refused on the same rule.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_DIR = ROOT / "policy" / "coverage"

_SCHEMA = "urn:ai-engineering:coverage:1"


def _absolute(repo_relative: str) -> Path | None:
    """Resolve a repo-relative path to its absolute form, or None when it escapes."""
    candidate = (ROOT / repo_relative).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError:
        return None
    return candidate


def declared_roots(policy_dir: Path = DEFAULT_POLICY_DIR) -> list[str]:
    """The roots every coverage file in `policy_dir` declares, or a fresh error.

    A missing directory or a file with an unknown schema is INCOMPLETE, never a guess:
    a guard that cannot name what it may scan cannot be believed to have scanned only that.
    """
    if not policy_dir.is_dir():
        where = policy_dir.relative_to(ROOT) if policy_dir.is_relative_to(ROOT) else policy_dir
        raise ValueError(f"no coverage directory at {where}")
    roots: list[str] = []
    for toml in sorted(policy_dir.glob("*.toml")):
        raw = tomllib.loads(toml.read_text(encoding="utf-8"))
        if raw.get("schema") != _SCHEMA:
            raise ValueError(f"unknown coverage schema in {toml.name}: {raw.get('schema')!r}")
        for root in raw.get("roots", []):
            if not isinstance(root, str):
                raise ValueError(f"coverage root must be a string, got {root!r} in {toml.name}")
            roots.append(root)
    return roots


def may_scan(path: str, policy_dir: Path = DEFAULT_POLICY_DIR) -> bool:
    """Whether `path` (a repo-relative path) falls under any declared coverage root.

    A declared root that escapes the repository is refused (never scanned), and a path that
    exits the repository is refused the same way — scanning outside what is declared is the
    exact false-green this contract exists to stop.
    """
    roots = declared_roots(policy_dir)
    if not roots:
        return False
    target = _absolute(path)
    if target is None:
        return False
    for declared in roots:
        root_decl = _absolute(declared)
        if root_decl is None:
            # A declared root that escapes the repository cannot be a legal scan target.
            continue
        try:
            target.relative_to(root_decl)
        except ValueError:
            continue
        return True
    return False