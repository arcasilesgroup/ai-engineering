"""Tests for orphan detection in the update service.

When a provider is disabled in ``manifest.yml`` but its files remain on
disk, ``update()`` should detect them as orphans and report them with
``action="orphan"``.  Orphans are deleted on apply but preserved on
dry-run.

Shared files (e.g., ``AGENTS.md`` used by copilot, gemini, codex)
should only be orphaned when ALL providers that use them are disabled.

RED-phase tests -- expected to FAIL until orphan detection is
implemented in the update service.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from ai_engineering.config.loader import update_manifest_field
from ai_engineering.installer.service import install
from ai_engineering.updater.service import update


def _ensure_git_repo(path: Path) -> None:
    """Init a git repo so installer hook discovery does not fail."""
    if not (path / ".git").is_dir():
        subprocess.run(["git", "init", "-q"], cwd=path, check=True)


# ---------------------------------------------------------------------------
# Provider-specific path prefixes (mirrors test_update_provider_filtering.py).
# ---------------------------------------------------------------------------

_CODEX_PREFIXES = (".codex/",)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _orphan_relative_paths(result: object, root: Path) -> set[str]:
    """Extract relative POSIX paths of orphan changes."""
    paths: set[str] = set()
    for change in result.changes:  # type: ignore[attr-defined]
        if change.action != "orphan":
            continue
        try:
            rel = change.path.relative_to(root).as_posix()
        except ValueError:
            rel = str(change.path)
        paths.add(rel)
    return paths


def _all_relative_paths(result: object, root: Path) -> set[str]:
    """Extract all relative POSIX paths from changes."""
    paths: set[str] = set()
    for change in result.changes:  # type: ignore[attr-defined]
        try:
            rel = change.path.relative_to(root).as_posix()
        except ValueError:
            rel = str(change.path)
        paths.add(rel)
    return paths


def _has_prefix_match(paths: set[str], prefixes: tuple[str, ...]) -> bool:
    """Return True if any path starts with one of the given prefixes."""
    return any(any(p.startswith(prefix) or p == prefix for prefix in prefixes) for p in paths)


def _place_codex_files(root: Path) -> list[Path]:
    """Create representative .codex/ files on disk.

    Returns the list of created file paths for assertion use.
    """
    codex_dir = root / ".codex"
    codex_dir.mkdir(parents=True, exist_ok=True)
    files = [
        codex_dir / "instructions.md",
        codex_dir / "config.yaml",
    ]
    for f in files:
        f.write_text(f"# stub content for {f.name}\n", encoding="utf-8")
    return files


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def claude_codex_project(tmp_path: Path) -> Path:
    """Install a project with ``claude_code`` and ``codex``, then
    reconfigure to ``claude_code`` only -- leaving .codex/ files as orphans.
    """
    _ensure_git_repo(tmp_path)
    install(tmp_path, ai_providers=["claude_code", "codex"])
    # Shrink enabled providers in the manifest to only claude_code.
    update_manifest_field(tmp_path, "ai_providers.enabled", ["claude_code"])
    update_manifest_field(tmp_path, "ai_providers.primary", "claude_code")
    # Ensure .codex/ files exist on disk (some may have been installed,
    # but place extras to guarantee orphan detection has files to find).
    _place_codex_files(tmp_path)
    return tmp_path


@pytest.fixture()
def claude_gemini_project(tmp_path: Path) -> Path:
    """Install a project with ``claude_code`` and ``gemini``."""
    _ensure_git_repo(tmp_path)
    install(tmp_path, ai_providers=["claude_code", "gemini"])
    return tmp_path


@pytest.fixture()
def claude_only_project(tmp_path: Path) -> Path:
    """Install a project with only ``claude_code``."""
    _ensure_git_repo(tmp_path)
    install(tmp_path, ai_providers=["claude_code"])
    return tmp_path


# ---------------------------------------------------------------------------
# T4: Orphan detection for disabled provider files
# ---------------------------------------------------------------------------


class TestOrphanDetection:
    """Verify that ``update()`` detects orphan files from disabled providers."""

    def test_orphan_detection_disabled_provider_files(
        self,
        claude_codex_project: Path,
    ) -> None:
        """T4: When codex is disabled but .codex/ files remain on disk,
        update(dry_run=True) must report them with action='orphan'.
        """
        result = update(claude_codex_project, dry_run=True)
        orphans = _orphan_relative_paths(result, claude_codex_project)

        assert _has_prefix_match(orphans, _CODEX_PREFIXES), (
            f"Expected .codex/ orphan entries but got none. "
            f"All actions: {[c.action for c in result.changes]}"
        )

    # -----------------------------------------------------------------------
    # T5: Orphan files deleted on apply
    # -----------------------------------------------------------------------

    def test_orphan_files_deleted_on_apply(
        self,
        claude_codex_project: Path,
    ) -> None:
        """T5: When update runs with dry_run=False, orphan .codex/ files
        must be deleted from disk.
        """
        codex_dir = claude_codex_project / ".codex"
        assert codex_dir.exists(), "Precondition: .codex/ must exist before update"

        result = update(claude_codex_project, dry_run=False)

        # After apply, every .codex/ file should be gone.
        remaining = list(codex_dir.rglob("*")) if codex_dir.exists() else []
        remaining_files = [f for f in remaining if f.is_file()]
        assert not remaining_files, (
            f"Expected .codex/ files to be deleted after apply, "
            f"but found: {[str(f) for f in remaining_files]}"
        )

        # Confirm orphan entries appeared in the result.
        orphans = _orphan_relative_paths(result, claude_codex_project)
        assert _has_prefix_match(orphans, _CODEX_PREFIXES), (
            "Expected orphan entries in result for deleted .codex/ files"
        )

    # -----------------------------------------------------------------------
    # T6: Orphan count in result
    # -----------------------------------------------------------------------

    def test_orphan_count_in_result(
        self,
        claude_codex_project: Path,
    ) -> None:
        """T6: UpdateResult must expose an orphan_count property > 0 when
        orphan files are detected.  This property does not exist yet.
        """
        result = update(claude_codex_project, dry_run=True)

        # This will raise AttributeError until orphan_count is implemented.
        assert result.orphan_count > 0, f"Expected orphan_count > 0 but got {result.orphan_count}"

    # -----------------------------------------------------------------------
    # T7: Dry-run does not delete orphans
    # -----------------------------------------------------------------------

    def test_dry_run_does_not_delete_orphans(
        self,
        claude_codex_project: Path,
    ) -> None:
        """T7: When update runs with dry_run=True, orphan .codex/ files
        must remain on disk (preview only).
        """
        codex_files = _place_codex_files(claude_codex_project)

        update(claude_codex_project, dry_run=True)

        for f in codex_files:
            assert f.exists(), f"Dry-run should not delete orphan files, but {f.name} was removed"


# ---------------------------------------------------------------------------
# T8 / T9: Shared file (AGENTS.md) orphan rules
# ---------------------------------------------------------------------------


class TestSharedFileOrphanRules:
    """AGENTS.md is shared by copilot, gemini, and codex.  It should
    only be orphaned when ALL providers that use it are disabled.
    """

    def test_shared_file_not_orphaned_when_other_provider_active(
        self,
        claude_gemini_project: Path,
    ) -> None:
        """T8: With [claude_code, gemini] active and codex disabled,
        AGENTS.md must NOT appear as an orphan because gemini still uses it.
        """
        # Ensure AGENTS.md exists on disk (gemini install should create it).
        agents_md = claude_gemini_project / "AGENTS.md"
        if not agents_md.exists():
            agents_md.write_text("# AGENTS\n", encoding="utf-8")

        result = update(claude_gemini_project, dry_run=True)
        orphans = _orphan_relative_paths(result, claude_gemini_project)

        assert "AGENTS.md" not in orphans, (
            "AGENTS.md should NOT be orphaned when gemini (which uses it) is active"
        )

    def test_shared_file_orphaned_when_all_providers_disabled(
        self,
        claude_only_project: Path,
    ) -> None:
        """T9: With only [claude_code] active (no copilot, gemini, codex),
        AGENTS.md must appear as an orphan because no active provider uses it.
        """
        # Place AGENTS.md on disk manually (it should not have been installed
        # since none of the providers that use it are active).
        agents_md = claude_only_project / "AGENTS.md"
        agents_md.write_text("# AGENTS\n", encoding="utf-8")

        result = update(claude_only_project, dry_run=True)
        orphans = _orphan_relative_paths(result, claude_only_project)

        assert "AGENTS.md" in orphans, (
            f"AGENTS.md should be orphaned when no provider that uses it is active. "
            f"Orphans found: {orphans}"
        )


# ---------------------------------------------------------------------------
# T-label: Orphan state label in tree
# ---------------------------------------------------------------------------


class TestOrphanStateLabel:
    """Verify that the CLI tree renderer has an 'orphan' state label."""

    def test_orphan_state_label_in_tree(self) -> None:
        """T-label: _STATE_LABELS must contain an 'orphan' entry with
        the expected (label, style) tuple.
        """
        from ai_engineering.cli_ui import _STATE_LABELS

        assert "orphan" in _STATE_LABELS, (
            f"Expected 'orphan' in _STATE_LABELS but found only: {list(_STATE_LABELS.keys())}"
        )

        label, style = _STATE_LABELS["orphan"]
        assert label == "orphan", f"Expected label 'orphan' but got '{label}'"
        assert "magenta" in style, f"Expected style to contain 'magenta' but got '{style}'"
