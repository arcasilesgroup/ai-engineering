"""CI guard for canonical specs/ structure — recalibrated per spec-131.

`.ai-engineering/specs/` MUST carry the canonical three buffers:

- `spec.md` — active spec buffer (resolver-canonical)
- `plan.md` — active plan buffer
- `_history.md` — append-only spec lifecycle audit log

Two governance subdirectories are also permitted (``archive/`` for
shipped numbered specs and ``drafts/`` for incubated briefs); they
hold curated content rather than autopilot scaffolding.

spec-131 D-131-04 introduces two additional permitted sibling
patterns (closure sweep C1):

* ``_history-constitution-<YYYY-MM-DD>.md`` — append-only rotation
  of the CONSTITUTION.md history when a new identity ADR ships.
  The file pattern is fixed and dated so the rotation is auditable.
* ``spec-<NNN>-<slug>.md`` — temporary holding slot for a shipped
  spec that has not yet been moved to ``archive/`` (e.g. spec-129
  carries the operator-marked-complete predecessor body while
  spec-131 occupies the canonical ``spec.md``).

Anything else (autopilot scaffolds, progress dirs, etc.) still
violates the workflow contract.

Numbered specs are recoverable from git history. Decisions live in
`state.db.decisions`. Autopilot transient state lives under
`.ai-engineering/state/runtime/autopilot/` (gitignored).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SPECS_DIR = PROJECT_ROOT / ".ai-engineering" / "specs"

CANONICAL_ENTRIES = ("_history.md", "plan.md", "spec.md")
# Curated governance subdirectories (kept under specs/ by design).
ALLOWED_DIRS = frozenset({"archive", "drafts"})

# spec-131 closure-sweep C1: permitted sibling-file patterns.
_CONSTITUTION_HISTORY_RE = re.compile(r"^_history-constitution-\d{4}-\d{2}-\d{2}\.md$")
_NUMBERED_SPEC_RE = re.compile(r"^spec-\d{3}(?:-[a-z0-9-]+)?\.md$")


def _entry_is_permitted_sibling(name: str) -> bool:
    """Return ``True`` if *name* matches a spec-131-permitted pattern."""
    return bool(_CONSTITUTION_HISTORY_RE.match(name)) or bool(_NUMBERED_SPEC_RE.match(name))


def test_specs_directory_exists() -> None:
    assert SPECS_DIR.is_dir(), (
        f"Active specs directory missing at {SPECS_DIR}. "
        "Per spec-123 D-123-02 the canonical work-plane surface lives here."
    )


def test_specs_directory_contains_only_canonical_entries() -> None:
    actual = tuple(sorted(os.listdir(SPECS_DIR)))
    canonical_set = set(CANONICAL_ENTRIES)
    extras = [name for name in actual if name not in canonical_set]
    unexpected = [
        name
        for name in extras
        if name not in ALLOWED_DIRS and not _entry_is_permitted_sibling(name)
    ]
    missing = [name for name in CANONICAL_ENTRIES if name not in actual]
    assert not unexpected and not missing, (
        f"specs/ contract violation. Expected canonical {CANONICAL_ENTRIES} "
        f"plus optional dirs {sorted(ALLOWED_DIRS)} plus permitted sibling "
        f"patterns (_history-constitution-YYYY-MM-DD.md, spec-NNN-<slug>.md) "
        f"per spec-131 D-131-04 closure sweep. "
        f"Got: {actual}. Missing canonical: {missing}. "
        f"Unexpected: {unexpected}."
    )


def test_canonical_entries_are_files() -> None:
    for name in CANONICAL_ENTRIES:
        path = SPECS_DIR / name
        assert path.is_file(), (
            f"Canonical entry {name} must be a regular file (not a directory or symlink to one)."
        )
