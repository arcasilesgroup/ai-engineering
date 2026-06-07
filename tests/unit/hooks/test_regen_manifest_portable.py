"""spec-168: the hook-manifest regenerator must self-heal on stock interpreters.

Two defects fixed here, both proven on a fresh install whose hooks were
silently disabled:

1. ``regenerate-hooks-manifest.py`` used ``from datetime import UTC`` — a
   3.11-only idiom. The integrity-failure remedy text tells operators to run
   it via bare ``python3``, which on stock macOS is 3.9 → ``ImportError`` →
   the documented self-heal crashed and the operator stayed stuck. The script
   is a recovery tool and must run on any Python it is handed, so it may not
   use idioms newer than the oldest interpreter an operator is likely to have.

2. ``_finalize_hooks_manifest`` swallowed failures with a one-line warning and
   never verified its own output, so a clean write that still mismatched the
   bytes (a stale manifest) slid by silently. It now runs a post-write
   ``--check`` and fails LOUD when the manifest is still stale.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ai_engineering.cli_commands.core import _finalize_hooks_manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_REGEN = REPO_ROOT / ".ai-engineering" / "scripts" / "regenerate-hooks-manifest.py"
TEMPLATE_REGEN = (
    REPO_ROOT
    / "src"
    / "ai_engineering"
    / "templates"
    / ".ai-engineering"
    / "scripts"
    / "regenerate-hooks-manifest.py"
)


def _uses_datetime_utc(source: str) -> bool:
    """True if the source references the 3.11-only ``datetime.UTC`` symbol."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        # `from datetime import UTC`
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "datetime"
            and any(alias.name == "UTC" for alias in node.names)
        ):
            return True
        # `datetime.UTC`
        if isinstance(node, ast.Attribute) and node.attr == "UTC":
            return True
    return False


@pytest.mark.unit
@pytest.mark.parametrize("path", [CANONICAL_REGEN, TEMPLATE_REGEN], ids=["canonical", "template"])
def test_regen_avoids_311_only_datetime_utc(path: Path) -> None:
    """The recovery tool must not use Python 3.11-only ``datetime.UTC``."""
    assert path.is_file(), f"missing regen script: {path}"
    assert not _uses_datetime_utc(path.read_text(encoding="utf-8")), (
        f"{path} uses the 3.11-only `datetime.UTC`; use `timezone.utc` so the "
        "self-heal command runs on stock python3 (3.9 on macOS) — spec-168"
    )


@pytest.mark.unit
def test_regen_canonical_and_template_are_byte_identical() -> None:
    """The shipped twin must match the canonical regen byte-for-byte.

    No CI guard covers script-template parity; this anchors at least the
    recovery tool so a one-sided edit cannot ship a stale twin (spec-168).
    """
    assert CANONICAL_REGEN.read_bytes() == TEMPLATE_REGEN.read_bytes()


@pytest.mark.unit
def test_finalize_fails_loud_when_manifest_stays_stale(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """A clean write whose --check still reports drift must warn LOUD.

    Simulates the exact silent dead-hooks state: the regen write succeeds
    (exit 0) but the manifest does not match the bytes, so the post-write
    ``--check`` exits non-zero. ``_finalize_hooks_manifest`` must surface the
    recovery command on stderr rather than returning silently.
    """
    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    # Stub: plain run (no --check) exits 0; a --check run exits 1 (stale).
    (scripts_dir / "regenerate-hooks-manifest.py").write_text(
        "import sys\nsys.exit(1 if '--check' in sys.argv else 0)\n",
        encoding="utf-8",
    )

    _finalize_hooks_manifest(tmp_path)

    err = capsys.readouterr().err
    assert "stale" in err.lower(), f"expected a loud stale-manifest warning; got: {err!r}"
    assert "regenerate-hooks-manifest.py" in err, "warning must name the recovery command"
