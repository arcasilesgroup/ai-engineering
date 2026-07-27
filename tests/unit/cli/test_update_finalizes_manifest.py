"""spec-159 D-159-03 — ``update_cmd`` re-pins hooks-manifest after an apply.

Contract under test:

* After ``ai-eng update --apply`` mutates hook bytes, the apply path calls
  ``_finalize_hooks_manifest(root)`` so ``hooks-manifest.json`` sha256
  entries match the freshly deployed bytes. Without this, every hook is
  killed under ``AIENG_HOOK_INTEGRITY_MODE=enforce`` (a self-inflicted
  outage on every upgrade).
* The finalize MUST NOT fire on preview / dry-run / no-op applies — a
  clean preview never rewrites the manifest.

These tests FAIL before T-6 (no finalize call in ``update_cmd``) and PASS
after. The unit tests spy on ``_finalize_hooks_manifest``; the integration
test drives the real helper end-to-end against deployed hook bytes.

Anchors: spec-159 D-159-03. TDD §10.5. §10.3 SOLID (parity with install_cmd).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from ai_engineering.cli_commands import core as core_mod
from ai_engineering.commands.update_workflow import (
    UpdateWorkflowResult,
    UpdateWorkflowStatus,
)
from ai_engineering.updater.service import FileChange, UpdateResult

REPO_ROOT = Path(__file__).resolve().parents[3]
REGEN_SCRIPT_SRC = REPO_ROOT / ".ai-engineering" / "scripts" / "regenerate-hooks-manifest.py"


def _make_result(*, dry_run: bool, applied: int = 0, orphan: int = 0) -> UpdateResult:
    """Build an UpdateResult with the requested applied/orphan change counts."""
    changes: list[FileChange] = []
    for i in range(applied):
        changes.append(FileChange(path=Path(f"applied-{i}.sh"), action="update"))
    for i in range(orphan):
        changes.append(FileChange(path=Path(f"orphan-{i}.sh"), action="orphan"))
    return UpdateResult(dry_run=dry_run, changes=changes)


def _patch_workflow(
    monkeypatch: pytest.MonkeyPatch, workflow_result: UpdateWorkflowResult
) -> list[Path]:
    """Patch update_cmd's collaborators; return the list finalize was called with."""
    finalize_calls: list[Path] = []

    monkeypatch.setattr(core_mod, "run_update_workflow", lambda *a, **k: workflow_result)
    monkeypatch.setattr(
        core_mod, "_finalize_hooks_manifest", lambda root: finalize_calls.append(root)
    )
    # Force the non-interactive JSON path so update_cmd does not block on a TTY.
    monkeypatch.setattr(core_mod, "is_json_mode", lambda: True)
    monkeypatch.setattr(core_mod, "resolve_project_root", lambda target: target or Path.cwd())
    return finalize_calls


# ---------------------------------------------------------------------------
# Unit — apply that mutated files finalizes; preview/no-op does not.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_apply_with_changes_finalizes_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An APPLIED update that mutated hook bytes re-pins the manifest."""
    wfr = UpdateWorkflowResult(
        status=UpdateWorkflowStatus.APPLIED,
        result=_make_result(dry_run=False, applied=2),
    )
    finalize_calls = _patch_workflow(monkeypatch, wfr)

    core_mod.update_cmd(target=tmp_path, apply=True)

    assert finalize_calls == [tmp_path], (
        "apply that mutated hook bytes must call _finalize_hooks_manifest(root)"
    )


@pytest.mark.unit
def test_apply_orphan_only_finalizes_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An apply that only removed orphan hook files still re-pins the manifest."""
    wfr = UpdateWorkflowResult(
        status=UpdateWorkflowStatus.APPLIED,
        result=_make_result(dry_run=False, orphan=1),
    )
    finalize_calls = _patch_workflow(monkeypatch, wfr)

    core_mod.update_cmd(target=tmp_path, apply=True)

    assert finalize_calls == [tmp_path]


@pytest.mark.unit
def test_preview_does_not_finalize_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """A dry-run preview must NEVER rewrite the manifest."""
    wfr = UpdateWorkflowResult(
        status=UpdateWorkflowStatus.PREVIEW,
        result=_make_result(dry_run=True, applied=3),
    )
    finalize_calls = _patch_workflow(monkeypatch, wfr)

    core_mod.update_cmd(target=tmp_path, apply=False)

    assert finalize_calls == [], "preview must not finalize the hooks manifest"


@pytest.mark.unit
def test_noop_apply_does_not_finalize_manifest(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An apply that mutated nothing must not rewrite the manifest."""
    wfr = UpdateWorkflowResult(
        status=UpdateWorkflowStatus.APPLIED,
        result=_make_result(dry_run=False),
    )
    finalize_calls = _patch_workflow(monkeypatch, wfr)

    core_mod.update_cmd(target=tmp_path, apply=True)

    assert finalize_calls == [], "no-op apply must not finalize the hooks manifest"


# ---------------------------------------------------------------------------
# Integration — real helper writes a manifest matching deployed hook bytes.
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_update_apply_repins_manifest_to_deployed_bytes(tmp_path: Path) -> None:
    """End-to-end: the apply gate runs the real regen and matches hook bytes.

    Builds a tmp project with the real regen script + a deployed hook, drives
    ``_finalize_update_hooks_manifest`` with an APPLIED result, and asserts the
    written sha256 matches the on-disk hook bytes (enforce-mode would pass).
    """
    import hashlib

    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REGEN_SCRIPT_SRC, scripts_dir / "regenerate-hooks-manifest.py")

    hooks_dir = scripts_dir / "hooks"
    hooks_dir.mkdir(parents=True, exist_ok=True)
    hook = hooks_dir / "run-hook.sh"
    hook_bytes = b"#!/usr/bin/env bash\necho updated\n"
    hook.write_bytes(hook_bytes)

    manifest_path = tmp_path / ".ai-engineering" / "state" / "hooks-manifest.json"
    assert not manifest_path.exists()

    wfr = UpdateWorkflowResult(
        status=UpdateWorkflowStatus.APPLIED,
        result=_make_result(dry_run=False, applied=1),
    )
    core_mod._finalize_update_hooks_manifest(wfr, tmp_path)

    assert manifest_path.exists(), "apply must (re)write hooks-manifest.json"
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_sha = hashlib.sha256(hook_bytes).hexdigest()
    key = ".ai-engineering/scripts/hooks/run-hook.sh"
    recorded = data["hooks"].get(key)
    assert recorded is not None, "deployed hook must be pinned in the manifest"
    assert recorded == expected_sha, "manifest sha256 must match deployed hook bytes"


@pytest.mark.integration
def test_preview_helper_is_noop_on_disk(tmp_path: Path) -> None:
    """The real helper writes nothing for a dry-run preview result."""
    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REGEN_SCRIPT_SRC, scripts_dir / "regenerate-hooks-manifest.py")

    manifest_path = tmp_path / ".ai-engineering" / "state" / "hooks-manifest.json"

    wfr = UpdateWorkflowResult(
        status=UpdateWorkflowStatus.PREVIEW,
        result=_make_result(dry_run=True, applied=2),
    )
    core_mod._finalize_update_hooks_manifest(wfr, tmp_path)

    assert not manifest_path.exists(), "preview must not write a manifest"


# ---------------------------------------------------------------------------
# spec-200 D-200-05 — the update path must reach the VERSION stamp
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_update_apply_stamps_version_at_canonical_path(tmp_path: Path) -> None:
    """An apply that mutates files re-stamps ``.ai-engineering/runtime/VERSION``.

    This is the load-bearing test for spec-200 D-200-05, which argues that no
    migration is needed when the runtime path moves. The argument: hook scripts
    are project-deployed, so a consumer receives new-path hooks only via
    ``ai-eng install``/``update``, and both funnel through
    ``_finalize_hooks_manifest`` — which stamps ``VERSION`` in the same run,
    before any new-path hook can execute. Old scripts read the old file, new
    scripts read the new one, and no intermediate state exists.

    That guarantee holds only while the stamp lives inside
    ``_finalize_hooks_manifest``. A future refactor that narrows the stamp to a
    single install-only call site reopens the window silently — every consumer
    would fall back to the importlib-metadata version with no failure anywhere.
    This test is what makes that refactor fail loudly instead (spec-200 Risk 3).
    """
    from ai_engineering import __version__

    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REGEN_SCRIPT_SRC, scripts_dir / "regenerate-hooks-manifest.py")

    wfr = UpdateWorkflowResult(
        status=UpdateWorkflowStatus.APPLIED,
        result=_make_result(dry_run=False, applied=1),
    )
    core_mod._finalize_update_hooks_manifest(wfr, tmp_path)

    version_file = tmp_path / ".ai-engineering" / "runtime" / "VERSION"
    assert version_file.is_file(), (
        "an apply that deploys new hook bytes must re-stamp VERSION in the same "
        "run — spec-200 D-200-05 zero-window guarantee"
    )
    assert version_file.read_text(encoding="utf-8").strip() == __version__
    assert not (tmp_path / ".ai-engineering" / "state" / "runtime").exists()


@pytest.mark.integration
def test_noop_apply_does_not_stamp_version(tmp_path: Path) -> None:
    """A no-op apply writes no VERSION — the early return is deliberate.

    ``_finalize_update_hooks_manifest`` returns before finalizing when an apply
    mutated nothing, so a clean preview or no-op never rewrites state. Pinned
    here so the D-200-05 test above is not "fixed" by removing that guard.
    """
    scripts_dir = tmp_path / ".ai-engineering" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy(REGEN_SCRIPT_SRC, scripts_dir / "regenerate-hooks-manifest.py")

    wfr = UpdateWorkflowResult(
        status=UpdateWorkflowStatus.APPLIED,
        result=_make_result(dry_run=False),
    )
    core_mod._finalize_update_hooks_manifest(wfr, tmp_path)

    assert not (tmp_path / ".ai-engineering" / "runtime" / "VERSION").exists()
