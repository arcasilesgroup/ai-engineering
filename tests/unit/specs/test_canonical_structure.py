"""CI guard for spec-123 D-123-02/D-123-06: canonical specs/ structure.

`.ai-engineering/specs/` MUST carry the canonical three buffers:

- `spec.md` — active spec buffer (resolver-canonical)
- `plan.md` — active plan buffer
- `_history.md` — append-only spec lifecycle audit log

Two governance subdirectories are also permitted (``archive/`` for
shipped numbered specs and ``drafts/`` for incubated briefs); they
hold curated content rather than autopilot scaffolding. Anything
else (numbered file siblings, progress dirs, autopilot scaffolds)
violates the workflow contract per Article XIII.

Numbered specs are recoverable from git history. Decisions live in
`state.db.decisions`. Autopilot transient state lives under
`.ai-engineering/state/runtime/autopilot/` (gitignored).
"""

from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPECS_DIR = PROJECT_ROOT / ".ai-engineering" / "specs"

CANONICAL_ENTRIES = ("_history.md", "plan.md", "spec.md")
# Curated governance subdirectories (kept under specs/ by design).
ALLOWED_DIRS = frozenset({"archive", "drafts"})


def test_specs_directory_exists() -> None:
    assert SPECS_DIR.is_dir(), (
        f"Active specs directory missing at {SPECS_DIR}. "
        "Per spec-123 D-123-02 the canonical work-plane surface lives here."
    )


def test_specs_directory_contains_only_canonical_entries() -> None:
    actual = tuple(sorted(os.listdir(SPECS_DIR)))
    canonical_set = set(CANONICAL_ENTRIES)
    extras = [name for name in actual if name not in canonical_set]
    unexpected = [name for name in extras if name not in ALLOWED_DIRS]
    missing = [name for name in CANONICAL_ENTRIES if name not in actual]
    assert not unexpected and not missing, (
        f"specs/ contract violation. Expected canonical {CANONICAL_ENTRIES} "
        f"plus optional {sorted(ALLOWED_DIRS)} per spec-123 D-123-02 + "
        f"Article XIII. Got: {actual}. Missing canonical: {missing}. "
        f"Unexpected: {unexpected}. Numbered archives recoverable via git "
        "log; autopilot scaffolding must live under "
        ".ai-engineering/state/runtime/autopilot/."
    )


def test_canonical_entries_are_files() -> None:
    for name in CANONICAL_ENTRIES:
        path = SPECS_DIR / name
        assert path.is_file(), (
            f"Canonical entry {name} must be a regular file (not a directory or symlink to one)."
        )
