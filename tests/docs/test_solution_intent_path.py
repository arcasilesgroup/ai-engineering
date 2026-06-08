"""Guard: no tracked file may reference the pre-move solution-intent path.

spec-168 D-168-02: the solution-intent document was moved out of ``docs/`` into
``.ai-engineering/`` (recorded in CHANGELOG). A handful of stale references were
left behind — notably the weekly architecture-drift runbook, which ``cat``/greps
the now-nonexistent path and silently no-ops. This guard prevents reintroduction.

Allowed to mention the old path:
  * ``CHANGELOG.md`` — records the historical move
  * ``.ai-engineering/specs/`` — spec/plan narrative describing the reconcile
  * this test file itself
"""

from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SELF_REL = str(Path(__file__).resolve().relative_to(REPO_ROOT))

ALLOWED_PREFIXES = (
    "CHANGELOG.md",
    ".ai-engineering/specs/",
)
STALE = "docs/" + "solution-intent.md"


def _tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout.splitlines()


def test_no_stale_solution_intent_path() -> None:
    offenders: list[str] = []
    for rel in _tracked_files():
        if rel == SELF_REL or rel.startswith(ALLOWED_PREFIXES):
            continue
        path = REPO_ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, FileNotFoundError, OSError):
            continue
        if STALE in text:
            offenders.append(rel)
    assert not offenders, (
        f"Stale {STALE!r} references found "
        "(canonical path is .ai-engineering/solution-intent.md): " + ", ".join(sorted(offenders))
    )
