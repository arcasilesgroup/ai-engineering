"""RED-phase tests for ``_finalize_hooks_manifest`` in cli_commands/core.py (spec-142 T-12).

Contract under test (T-13 will implement):

* ``_finalize_hooks_manifest(root: Path) -> None`` — invokes
  ``regenerate-hooks-manifest.py`` (no ``--check`` flag) so a fresh
  install writes ``hooks-manifest.json`` immediately, ensuring
  ``/ai-start`` reports ``hooks: ok`` instead of ``hooks: unverified``.

Anchors: spec-142 D-142-05 (installer auto-regenerate).
TDD §10.5 RED phase.  §10.1 KISS (single responsibility: locate and invoke).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ai_engineering.cli_commands.core import _finalize_hooks_manifest

REPO_ROOT = Path(__file__).resolve().parents[3]
REGEN_SCRIPT_SRC = REPO_ROOT / ".ai-engineering" / "scripts" / "regenerate-hooks-manifest.py"


# ---------------------------------------------------------------------------
# Test 1 — happy path: script present, hooks dir populated, manifest written
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_finalize_hooks_manifest_happy_path(tmp_path: Path) -> None:
    """Manifest is created when the regen script and a hooks dir are present.

    The test copies the REAL regen script into ``tmp/.ai-engineering/scripts/``
    so the script's self-resolving ``REPO_ROOT`` points at ``tmp`` and the
    manifest lands at ``tmp/.ai-engineering/state/hooks-manifest.json``.
    """
    # Arrange: build tmp tree matching the script's expected layout.
    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)

    # Copy the real regen script — its __file__-derived REPO_ROOT resolves to tmp.
    regen_dst = scripts_dir / "regenerate-hooks-manifest.py"
    shutil.copy(REGEN_SCRIPT_SRC, regen_dst)

    # Provide at least one hook file so hookCount > 0 (proves HOOKS_DIR was scanned).
    hooks_dir = scripts_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    stub_hook = hooks_dir / "dummy.sh"
    stub_hook.write_text("echo hi\n", encoding="utf-8")

    # State dir does NOT exist yet — script must create it.
    manifest_path = tmp_path / ".ai-engineering" / "state" / "hooks-manifest.json"
    assert not manifest_path.exists(), "pre-condition: manifest must be absent"

    # Act
    _finalize_hooks_manifest(tmp_path)

    # Assert: manifest was written and is valid JSON with a ``hooks`` key.
    assert manifest_path.exists(), "manifest must be created by _finalize_hooks_manifest"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "hooks" in data, "manifest JSON must contain a 'hooks' key"
    assert isinstance(data["hooks"], dict), "'hooks' value must be a dict"
    assert len(data["hooks"]) >= 1, "at least one hook entry expected (dummy.sh)"


# ---------------------------------------------------------------------------
# Test 2 — regen script missing: no exception, no manifest
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_finalize_hooks_manifest_script_missing(tmp_path: Path) -> None:
    """When the regen script is absent, the helper returns silently without error.

    No manifest file should be created and no exception should propagate.
    """
    # Arrange: tmp root WITHOUT the regen script.
    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    # Deliberately omit ``regenerate-hooks-manifest.py``.

    manifest_path = tmp_path / ".ai-engineering" / "state" / "hooks-manifest.json"

    # Act + Assert: must not raise.
    _finalize_hooks_manifest(tmp_path)

    assert not manifest_path.exists(), "no manifest should be created when script is absent"


# ---------------------------------------------------------------------------
# Test 3 — regen script exits 1: warning emitted, no exception raised
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_finalize_hooks_manifest_script_fails(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """When the regen script exits non-zero, a warning is written to stderr.

    The helper must NOT raise and must emit a line containing
    ``"regenerate-hooks-manifest"`` (or similar) to stderr so the operator
    knows why the manifest was not refreshed.
    """
    # Arrange: create a stub script that always exits 1 and writes nothing.
    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    regen_stub = scripts_dir / "regenerate-hooks-manifest.py"
    regen_stub.write_text(
        "import sys\nsys.exit(1)\n",
        encoding="utf-8",
    )

    manifest_path = tmp_path / ".ai-engineering" / "state" / "hooks-manifest.json"

    # Act + Assert: must not raise.
    _finalize_hooks_manifest(tmp_path)

    # The manifest must not exist (script failed, wrote nothing).
    assert not manifest_path.exists(), "failed script must not produce a manifest"

    # A warning containing the script name must appear on stderr.
    captured = capsys.readouterr()
    assert "regenerate-hooks-manifest" in captured.err, (
        f"expected warning about 'regenerate-hooks-manifest' in stderr; got: {captured.err!r}"
    )
