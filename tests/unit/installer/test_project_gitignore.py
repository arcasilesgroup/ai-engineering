"""Tests for the managed ``.ai-engineering/.gitignore`` install output.

The installer writes this file programmatically (not via the template tree):
the wheel build only ships ``templates/**/*.{md,yml,json}``, so a dotfile
named ``.gitignore`` would never reach a pip-installed consumer.

Coverage:
- the file lands at the scoped path ``.ai-engineering/.gitignore``;
- every transient / per-install / derived artifact is ignored;
- the secret-material safety net is present;
- the committed sources of truth (policies, notes, hooks-manifest) stay
  tracked;
- create-only semantics preserve operator edits, FRESH overwrites;
- ``git check-ignore`` actually ignores the bundle + per-install artifacts
  and does NOT ignore the sources of truth.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from ai_engineering.installer.gitignore import (
    MANAGED_GITIGNORE_CONTENT,
    MANAGED_GITIGNORE_REL,
    ensure_project_gitignore,
)


def _active_patterns(content: str) -> set[str]:
    """Return the non-comment, non-blank ignore patterns."""
    return {
        line.strip()
        for line in content.splitlines()
        if line.strip() and not line.strip().startswith("#")
    }


def test_relative_path_is_scoped_to_managed_tree() -> None:
    assert MANAGED_GITIGNORE_REL.parts == (".ai-engineering", ".gitignore")


def test_writes_file_at_scoped_path(tmp_path: Path) -> None:
    result = ensure_project_gitignore(tmp_path)

    dest = tmp_path / ".ai-engineering" / ".gitignore"
    assert dest.is_file()
    assert dest.read_text(encoding="utf-8") == MANAGED_GITIGNORE_CONTENT
    assert result == {
        "written": True,
        "action": "created",
        "path": str(dest),
    }


def test_ignores_transient_and_per_install_artifacts() -> None:
    active = _active_patterns(MANAGED_GITIGNORE_CONTENT)
    must_ignore = {
        "state/runtime/",  # the OPA bundle.tar.gz lives here
        "runtime/",
        "runs/",
        "cache/",
        ".cache/",
        "state/install-state.json",
        "state/ownership-map.json",
        "state/framework-capabilities.json",
        "state/framework-events.ndjson",
        "state/observation-events.ndjson",
        "state/instinct-observations.ndjson",
        "state/state.db",
        "state/state.db-wal",
        "state/state.db-shm",
        "state/gate-findings.json",
        "state/strategic-compact.json",
        "state/locks/",
        "local.yml",
        "policies/.signatures.json",  # per-install signing output
        "policies/.manifest",
    }
    assert must_ignore <= active


def test_ignores_python_bytecode() -> None:
    """spec-168: shipped .ai-engineering/scripts/*.py hooks compile bytecode
    on every run; __pycache__/*.pyc must be ignored or it dirties the tree
    perpetually (and operators end up committing it)."""
    active = _active_patterns(MANAGED_GITIGNORE_CONTENT)
    assert {"__pycache__/", "*.pyc"} <= active


def test_secret_material_safety_net() -> None:
    active = _active_patterns(MANAGED_GITIGNORE_CONTENT)
    assert {"*.pem", "*.key", "*.p12", "*.pfx", "credentials*.json"} <= active


def test_sources_of_truth_are_not_ignored() -> None:
    active = _active_patterns(MANAGED_GITIGNORE_CONTENT)
    # hooks-manifest.json is the hook integrity baseline — must stay tracked.
    assert not any("hooks-manifest" in pattern for pattern in active)
    # notes/ is the /ai-note knowledge base — committed across the team.
    assert "notes/" not in active
    assert "notes" not in active
    # decision-store.json is the committed governance SoT: risk acceptances
    # are born there and are not rebuildable from specs, so it stays tracked.
    assert "state/decision-store.json" not in active
    # manifest.yml is the config source of truth.
    assert "manifest.yml" not in active
    # policy source files are never ignored (only the per-install signature is).
    assert not any(pattern.endswith(".rego") for pattern in active)


def test_create_only_preserves_existing_file(tmp_path: Path) -> None:
    dest = tmp_path / ".ai-engineering" / ".gitignore"
    dest.parent.mkdir(parents=True)
    dest.write_text("# operator edits\ncustom-rule/\n", encoding="utf-8")

    result = ensure_project_gitignore(tmp_path, fresh=False)

    assert result["written"] is False
    assert result["action"] == "skipped"
    assert dest.read_text(encoding="utf-8") == "# operator edits\ncustom-rule/\n"


def test_fresh_overwrites_existing_file(tmp_path: Path) -> None:
    dest = tmp_path / ".ai-engineering" / ".gitignore"
    dest.parent.mkdir(parents=True)
    dest.write_text("# stale managed content\n", encoding="utf-8")

    result = ensure_project_gitignore(tmp_path, fresh=True)

    assert result["written"] is True
    assert result["action"] == "overwritten"
    assert dest.read_text(encoding="utf-8") == MANAGED_GITIGNORE_CONTENT


def test_idempotent_managed_content(tmp_path: Path) -> None:
    ensure_project_gitignore(tmp_path)
    first = (tmp_path / ".ai-engineering" / ".gitignore").read_text(encoding="utf-8")
    ensure_project_gitignore(tmp_path, fresh=True)
    second = (tmp_path / ".ai-engineering" / ".gitignore").read_text(encoding="utf-8")
    assert first == second == MANAGED_GITIGNORE_CONTENT


@pytest.mark.skipif(shutil.which("git") is None, reason="git binary required")
def test_git_check_ignore_matches_intended_paths(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    ensure_project_gitignore(tmp_path)

    def is_ignored(rel: str) -> bool:
        completed = subprocess.run(
            ["git", "check-ignore", rel],
            cwd=tmp_path,
            capture_output=True,
            check=False,
        )
        return completed.returncode == 0

    # Transient / per-install artifacts must be ignored.
    assert is_ignored(".ai-engineering/state/runtime/bundle.tar.gz")
    assert is_ignored(".ai-engineering/state/install-state.json")
    assert is_ignored(".ai-engineering/policies/.signatures.json")
    assert is_ignored(".ai-engineering/policies/.manifest")
    assert is_ignored(".ai-engineering/security/leaked.pem")  # safety net
    assert is_ignored(".ai-engineering/scripts/hooks/_lib/__pycache__/x.pyc")  # spec-168

    # Sources of truth must NOT be ignored.
    assert not is_ignored(".ai-engineering/policies/branch_protection.rego")
    assert not is_ignored(".ai-engineering/state/hooks-manifest.json")
    assert not is_ignored(".ai-engineering/notes/finding.md")
    assert not is_ignored(".ai-engineering/manifest.yml")
