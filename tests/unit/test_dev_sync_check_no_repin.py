"""``dev sync --check`` verifies the hook manifest; it must never re-sign it.

spec-201 H8: the ``--check`` path called ``_finalize_hooks_manifest`` — the
WRITE-mode regenerator — so a verify-only command silently re-pinned the
integrity manifest from whatever bytes were on disk. A corrupted pin, an
edited hook, or an injected hook was freshly signed and the command reported
"Mirrors in sync", exit 0. It stayed invisible on a clean tree (``generatedAt``
is preserved on a no-op) and only bit on the drifted tree the check exists for.

The regenerator is replaced by a stand-in that records whether it was asked to
write, so the assertion is on observed process behaviour rather than on a
mocked call.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import ai_engineering.cli_commands.dev_sync as dev_sync_module

# Stand-in regenerator: `--check` fails until a repair has happened, and a
# write leaves the `REPAIRED` sentinel behind. Mirrors the real script's
# contract (`--check` writes nothing, exits 1 when stale).
_FAKE_REGEN = """\
import pathlib
import sys

root = pathlib.Path(__file__).resolve().parents[2]
sentinel = root / "REPAIRED"
if "--check" in sys.argv:
    if sentinel.exists():
        sys.exit(0)
    sys.stderr.write("hooks-manifest STALE\\n")
    sys.exit(1)
sentinel.write_text("re-pinned\\n", encoding="utf-8")
sys.exit(0)
"""


@pytest.fixture
def drifted_project(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A project whose hook manifest does not match its hook bytes."""
    mirrors = tmp_path / "scripts" / "sync_command_mirrors.py"
    mirrors.parent.mkdir(parents=True, exist_ok=True)
    mirrors.write_text("print('mirrors ok')\n", encoding="utf-8")

    regen = tmp_path / ".ai-engineering" / "scripts" / "regenerate-hooks-manifest.py"
    regen.parent.mkdir(parents=True, exist_ok=True)
    regen.write_text(_FAKE_REGEN, encoding="utf-8")

    monkeypatch.setattr(dev_sync_module, "resolve_project_root", lambda _target: tmp_path)
    return tmp_path


def test_check_reports_manifest_drift_instead_of_healing_it(drifted_project: Path) -> None:
    """--check surfaces the drift and leaves the manifest untouched."""
    # Act
    with pytest.raises(SystemExit) as exit_info:
        dev_sync_module.dev_sync_cmd(check=True)

    # Assert -- non-zero exit, and the regenerator was never run in write mode.
    assert exit_info.value.code == 1
    assert not (drifted_project / "REPAIRED").exists(), (
        "`dev sync --check` re-signed the hook integrity manifest — a verify-only "
        "command must never launder tampered hook bytes into a signed clean state"
    )


def test_write_mode_still_repins_the_manifest(drifted_project: Path) -> None:
    """The write path keeps its D-192-05 re-pin: only --check is verify-only."""
    # Act
    dev_sync_module.dev_sync_cmd(check=False)

    # Assert
    assert (drifted_project / "REPAIRED").exists()
