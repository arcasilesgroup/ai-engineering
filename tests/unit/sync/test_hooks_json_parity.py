"""Single-source parity guard for ``.github/hooks/hooks.json`` (spec-159 T-4).

Before spec-159 the Copilot ``hooks.json`` was hand-maintained in two copies
that drifted (122-line repo root vs 101-line install template -- the template
copy was missing the ``copilot-runtime-stop`` block and other richer entries,
D-159-06 / R2).

This module asserts the two copies are byte-identical *and* that both equal
the deterministic output of ``generate_copilot_hooks_json()`` (the single
source). It FAILS until T-9 lands the generator + dual-write.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_REMEDY = "run: python scripts/sync_mirrors/core.py"


def _root_hooks_json() -> Path:
    from scripts.sync_command_mirrors import ROOT

    return ROOT / ".github" / "hooks" / "hooks.json"


def _template_hooks_json() -> Path:
    from scripts.sync_command_mirrors import TPL_PROJECT

    return TPL_PROJECT / ".github" / "hooks" / "hooks.json"


def test_generator_matches_root_copy() -> None:
    """The generator reproduces the canonical root copy byte-for-byte."""
    from scripts.sync_command_mirrors import generate_copilot_hooks_json

    generated = generate_copilot_hooks_json()
    root_bytes = _root_hooks_json().read_text(encoding="utf-8")
    assert generated == root_bytes, (
        f"generate_copilot_hooks_json() drifted from the root hooks.json ({_REMEDY})"
    )


def test_root_and_template_copies_are_byte_identical() -> None:
    """Repo-root and install-template hooks.json must be byte-identical."""
    root_bytes = _root_hooks_json().read_bytes()
    tpl_bytes = _template_hooks_json().read_bytes()
    assert root_bytes == tpl_bytes, (
        f".github/hooks/hooks.json copies drifted (root vs template) ({_REMEDY})"
    )


def test_both_copies_equal_generator_output() -> None:
    """Both on-disk copies equal the single generated source."""
    from scripts.sync_command_mirrors import generate_copilot_hooks_json

    generated = generate_copilot_hooks_json()
    assert _root_hooks_json().read_text(encoding="utf-8") == generated, (
        f"root hooks.json != generator output ({_REMEDY})"
    )
    assert _template_hooks_json().read_text(encoding="utf-8") == generated, (
        f"template hooks.json != generator output ({_REMEDY})"
    )
