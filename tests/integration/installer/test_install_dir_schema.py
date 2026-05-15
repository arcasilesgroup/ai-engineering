"""Golden-file snapshot for ``ai-eng install`` directory layout.

spec-132 D-132-24: drift in the canonical shape of ``.ai-engineering/``
after a fresh install must surface as a failing test, not as silent
breakage to consumers who follow `docs/architecture/dir-schemas.md`.

The snapshot is intentionally scoped to the structurally stable parts
of the install:

* every top-level entry directly under ``.ai-engineering/`` (one level
  deep — directories appear with a trailing ``/`` so the snapshot is
  stable when contexts / runbooks add new files);
* every file and directory under ``.ai-engineering/specs/`` (the spec
  lifecycle workspace documented in D-132-24);
* every file and directory under ``.ai-engineering/state/`` (the
  audit / state.db layout documented in D-132-24).

This deliberately excludes the deep tree under ``contexts/``,
``runbooks/``, ``scripts/``, ``policies/``, etc. so adding a new
context file does NOT churn the golden snapshot. Those parts live
behind their own validators (`validator/categories/file_existence.py`)
and have their own drift signals.

Regeneration
------------
When the spec authorises a directory-shape change, regenerate the
snapshot with::

    AIENG_UPDATE_INSTALL_SCHEMA=1 uv run pytest \\
        tests/integration/installer/test_install_dir_schema.py

The test will rewrite ``fixtures/install-dir-schema.txt`` with the
current install layout and exit green. Commit the diff alongside the
spec decision that authorised it.
"""

from __future__ import annotations

import os
from pathlib import Path

from ai_engineering.installer.service import install
from ai_engineering.state.state_db import _reset_fallback_warnings

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "install-dir-schema.txt"


def _ensure_project_marker(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "schema-smoke"\nversion = "0.0.1"\n', encoding="utf-8"
    )


def _snapshot_install_layout(tmp_path: Path) -> list[str]:
    """Build the scoped snapshot lines, sorted, with trailing '/' on dirs."""
    ai_eng = tmp_path / ".ai-engineering"
    if not ai_eng.exists():
        return []

    entries: set[str] = set()

    # Top-level entries directly under .ai-engineering/, one level deep.
    for child in ai_eng.iterdir():
        rel = child.relative_to(tmp_path).as_posix()
        if child.is_dir():
            entries.add(f"{rel}/")
        else:
            entries.add(rel)

    # Full tree under specs/ and state/ (where D-132-24 schema is documented).
    for scope in ("specs", "state"):
        root = ai_eng / scope
        if not root.exists():
            continue
        for descendant in root.rglob("*"):
            rel = descendant.relative_to(tmp_path).as_posix()
            if descendant.is_dir():
                entries.add(f"{rel}/")
            else:
                entries.add(rel)

    return sorted(entries)


def test_install_directory_layout_matches_snapshot(tmp_path: Path) -> None:
    """spec-132 D-132-24: fresh install layout matches the golden snapshot."""
    _reset_fallback_warnings()
    _ensure_project_marker(tmp_path)

    install(tmp_path, stacks=["python"])

    actual_lines = _snapshot_install_layout(tmp_path)
    actual_text = "\n".join(actual_lines) + "\n"

    if os.environ.get("AIENG_UPDATE_INSTALL_SCHEMA") == "1":
        FIXTURE_PATH.parent.mkdir(parents=True, exist_ok=True)
        FIXTURE_PATH.write_text(actual_text, encoding="utf-8")
        return

    assert FIXTURE_PATH.exists(), (
        f"Snapshot missing at {FIXTURE_PATH.relative_to(Path(__file__).parents[3])}. "
        "Regenerate with AIENG_UPDATE_INSTALL_SCHEMA=1 (see module docstring)."
    )

    expected_text = FIXTURE_PATH.read_text(encoding="utf-8")
    assert actual_text == expected_text, (
        "Install directory layout drifted from the spec-132 D-132-24 snapshot. "
        "Either restore the layout or, if the change is spec-authorised, "
        "regenerate the snapshot with AIENG_UPDATE_INSTALL_SCHEMA=1 and commit "
        "the diff alongside the spec decision.\n"
        f"Expected:\n{expected_text}\nActual:\n{actual_text}"
    )
