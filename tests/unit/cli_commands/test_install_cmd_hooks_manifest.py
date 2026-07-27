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
import subprocess
from pathlib import Path

import pytest

from ai_engineering.cli_commands import core as core_mod
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


# ---------------------------------------------------------------------------
# Test 4 — clean write but --check reports drift: stale-after-regen warning
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_finalize_warns_when_manifest_stale_after_regen(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    """spec-168 post-condition: a regen that exits 0 but still fails ``--check``.

    This is the exact silent dead-hooks state — a clean write whose manifest
    does not match the bytes. The helper must emit the loud recovery block
    naming the stale manifest, and must NOT raise.
    """
    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    regen_stub = scripts_dir / "regenerate-hooks-manifest.py"
    # Plain run: succeed (exit 0). With --check: report drift (exit 1).
    regen_stub.write_text(
        "import sys\nsys.exit(1 if '--check' in sys.argv else 0)\n",
        encoding="utf-8",
    )

    _finalize_hooks_manifest(tmp_path)

    captured = capsys.readouterr()
    assert "still stale after regeneration" in captured.err, (
        f"expected stale-after-regen warning in stderr; got: {captured.err!r}"
    )


# ---------------------------------------------------------------------------
# Test 5 — regen subprocess raises OSError: fail-open with recovery block
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_finalize_warns_when_subprocess_raises(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """spec-168: an OSError launching the regen must fail-open with a warning.

    Covers the ``except (TimeoutExpired, OSError)`` guard around the regen
    invocation — the install must never abort on a launch failure.
    """
    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "regenerate-hooks-manifest.py").write_text(
        "import sys\nsys.exit(0)\n", encoding="utf-8"
    )

    def _boom(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess:
        raise OSError("simulated exec failure")

    monkeypatch.setattr(core_mod.subprocess, "run", _boom)

    _finalize_hooks_manifest(tmp_path)

    captured = capsys.readouterr()
    assert "failed to run" in captured.err, (
        f"expected fail-open warning in stderr; got: {captured.err!r}"
    )


# ---------------------------------------------------------------------------
# Test 6 — --check subprocess raises: verification fail-open warning
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_finalize_warns_when_check_subprocess_raises(
    tmp_path: Path, capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """spec-168: a clean regen then an OSError on the ``--check`` verification.

    Covers the second ``except (TimeoutExpired, OSError)`` guard — the
    post-write verification must also fail-open with a recovery block.
    """
    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "regenerate-hooks-manifest.py").write_text(
        "import sys\nsys.exit(0)\n", encoding="utf-8"
    )

    def _run(cmd: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
        if "--check" in cmd:
            raise OSError("simulated verification failure")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(core_mod.subprocess, "run", _run)

    _finalize_hooks_manifest(tmp_path)

    captured = capsys.readouterr()
    assert "verification failed to run" in captured.err, (
        f"expected verification fail-open warning in stderr; got: {captured.err!r}"
    )


# ---------------------------------------------------------------------------
# Test 7 — spec-190: VERSION pin write raises OSError -> swallowed, no abort
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_finalize_swallows_version_write_oserror(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """spec-190 D-190-01: an unwritable ``runtime/VERSION`` must fail-open.

    The framework-version pin is best-effort; an OSError writing it must be
    swallowed (``except OSError: pass``) so the install/update never aborts.
    Only the ``VERSION`` write is forced to fail — the regen path is untouched.
    """
    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "regenerate-hooks-manifest.py").write_text(
        "import sys\nsys.exit(0)\n", encoding="utf-8"
    )

    version_file = tmp_path / ".ai-engineering" / "runtime" / "VERSION"
    real_write_text = Path.write_text

    def _guarded_write_text(self: Path, *args: object, **kwargs: object) -> int:
        if self.name == "VERSION":
            raise OSError("simulated version write failure")
        return real_write_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "write_text", _guarded_write_text)

    # Must not raise even though the VERSION write fails.
    _finalize_hooks_manifest(tmp_path)

    assert not version_file.exists(), "VERSION must not exist after a swallowed write failure"


# ---------------------------------------------------------------------------
# Test 8 — spec-200 D-200-03: the VERSION pin lands at the canonical path
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_finalize_pins_version_at_canonical_runtime_path(tmp_path: Path) -> None:
    """``_finalize_hooks_manifest`` writes ``.ai-engineering/runtime/VERSION``.

    spec-200 D-200-03. The hook observability library reads this file to stamp
    ``frameworkVersion`` on every telemetry event (spec-190 D-190-01). Reader
    and writer are one datum: if the reader moves to the canonical runtime dir
    and this write does not, telemetry silently degrades to the
    importlib-metadata fallback with no failure anywhere — spec-200 Risk 2.

    The legacy ``state/runtime/`` location must not be created at all; nothing
    reads it after this spec, and a resurrected directory fails
    ``test_forbidden_dirs_absent``.
    """
    from ai_engineering import __version__

    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "regenerate-hooks-manifest.py").write_text(
        "import sys\nsys.exit(0)\n", encoding="utf-8"
    )

    _finalize_hooks_manifest(tmp_path)

    version_file = tmp_path / ".ai-engineering" / "runtime" / "VERSION"
    assert version_file.is_file(), (
        f"VERSION must be pinned at {version_file}; hook event stamping reads it"
    )
    assert version_file.read_text(encoding="utf-8").strip() == __version__

    legacy = tmp_path / ".ai-engineering" / "state" / "runtime"
    assert not legacy.exists(), f"the retired {legacy} must not be created"
