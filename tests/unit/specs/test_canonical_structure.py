"""CI guard for spec-123 D-123-02/D-123-06: canonical specs/ structure.

`.ai-engineering/specs/` MUST contain exactly three entries:

- `spec.md` — active spec buffer (resolver-canonical)
- `plan.md` — active plan buffer
- `_history.md` — append-only spec lifecycle audit log

Every other entry (numbered archives, progress dirs, work-plane artifacts,
autopilot scaffolding) violates the workflow contract per Article XIII.

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


def test_specs_directory_exists() -> None:
    assert SPECS_DIR.is_dir(), (
        f"Active specs directory missing at {SPECS_DIR}. "
        "Per spec-123 D-123-02 the canonical work-plane surface lives here."
    )


def test_specs_directory_contains_only_canonical_entries() -> None:
    actual = tuple(sorted(os.listdir(SPECS_DIR)))
    assert actual == CANONICAL_ENTRIES, (
        f"specs/ contract violation. Expected exactly {CANONICAL_ENTRIES} "
        f"per spec-123 D-123-02 + Article XIII. Got: {actual}.\n"
        "Numbered archives recoverable via git log. Autopilot scaffolding "
        "must live under .ai-engineering/state/runtime/autopilot/."
    )


def test_canonical_entries_are_files() -> None:
    for name in CANONICAL_ENTRIES:
        path = SPECS_DIR / name
        assert path.is_file(), (
            f"Canonical entry {name} must be a regular file (not a directory or symlink to one)."
        )
