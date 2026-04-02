"""Tests for provider-aware filtering in the update service.

The ``update()`` function should respect ``ai_providers.enabled`` from
``manifest.yml`` and only produce changes for the configured providers.
When no manifest exists, all providers are included as a backward-compatible
fallback.

RED-phase tests -- expected to FAIL until ``_evaluate_project_files``
reads the manifest and passes the enabled providers to
``resolve_template_maps``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.installer.service import install
from ai_engineering.updater.service import update

# ---------------------------------------------------------------------------
# Provider-specific path prefixes used in assertions.
# Derived from ``_PROVIDER_FILE_MAPS`` and ``_PROVIDER_TREE_MAPS`` in
# ``ai_engineering.installer.templates``.
# ---------------------------------------------------------------------------

_CLAUDE_PREFIXES = (".claude/", "CLAUDE.md")
_COPILOT_PREFIXES = (
    ".github/copilot-instructions.md",
    ".github/skills/",
    ".github/agents/",
    "AGENTS.md",
)
_GEMINI_PREFIXES = (".gemini/", "GEMINI.md")
_CODEX_PREFIXES = (".codex/",)


def _changed_relative_paths(result: object, root: Path) -> set[str]:
    """Extract relative POSIX paths from non-skip-unchanged changes.

    Only considers changes that actually create or update files, skipping
    those that are unchanged or denied.
    """
    paths: set[str] = set()
    for change in result.changes:  # type: ignore[attr-defined]
        if change.action == "skip-unchanged":
            continue
        try:
            rel = change.path.relative_to(root).as_posix()
        except ValueError:
            rel = str(change.path)
        paths.add(rel)
    return paths


def _has_provider_paths(paths: set[str], prefixes: tuple[str, ...]) -> bool:
    """Return True if any path starts with one of the given prefixes."""
    return any(any(p.startswith(prefix) or p == prefix for prefix in prefixes) for p in paths)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def claude_only_project(tmp_path: Path) -> Path:
    """Install a project with only ``claude_code`` as AI provider."""
    install(tmp_path, ai_providers=["claude_code"])
    return tmp_path


@pytest.fixture()
def claude_copilot_project(tmp_path: Path) -> Path:
    """Install a project with ``claude_code`` and ``github_copilot``."""
    install(tmp_path, ai_providers=["claude_code", "github_copilot"])
    return tmp_path


@pytest.fixture()
def claude_gemini_project(tmp_path: Path) -> Path:
    """Install a project with ``claude_code`` and ``gemini``."""
    install(tmp_path, ai_providers=["claude_code", "gemini"])
    return tmp_path


@pytest.fixture()
def no_manifest_project(tmp_path: Path) -> Path:
    """Install a project, then remove the manifest to test fallback."""
    install(tmp_path)
    manifest = tmp_path / ".ai-engineering" / "manifest.yml"
    if manifest.exists():
        manifest.unlink()
    return tmp_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestUpdateProviderFiltering:
    """Verify that ``update()`` respects ``ai_providers.enabled`` from manifest."""

    def test_update_claude_only_excludes_other_providers(
        self,
        claude_only_project: Path,
    ) -> None:
        """T1: When only claude_code is enabled, update must not produce
        changes for github_copilot, gemini, or codex paths.
        """
        result = update(claude_only_project, dry_run=True)
        paths = _changed_relative_paths(result, claude_only_project)

        # Claude paths may or may not appear (depending on whether templates
        # differ from what was installed), but other providers MUST be absent.
        assert not _has_provider_paths(paths, _COPILOT_PREFIXES), (
            f"Found github_copilot paths in claude-only update: "
            f"{[p for p in paths if _has_provider_paths({p}, _COPILOT_PREFIXES)]}"
        )
        assert not _has_provider_paths(paths, _GEMINI_PREFIXES), (
            f"Found gemini paths in claude-only update: "
            f"{[p for p in paths if _has_provider_paths({p}, _GEMINI_PREFIXES)]}"
        )
        assert not _has_provider_paths(paths, _CODEX_PREFIXES), (
            f"Found codex paths in claude-only update: "
            f"{[p for p in paths if _has_provider_paths({p}, _CODEX_PREFIXES)]}"
        )

    def test_update_claude_copilot_includes_only_those(
        self,
        claude_copilot_project: Path,
    ) -> None:
        """T2: When claude_code + github_copilot are enabled, update must
        include .claude/ and .github/ paths but NOT .codex/ or .gemini/.
        """
        result = update(claude_copilot_project, dry_run=True)
        paths = _changed_relative_paths(result, claude_copilot_project)

        assert not _has_provider_paths(paths, _GEMINI_PREFIXES), (
            f"Found gemini paths in claude+copilot update: "
            f"{[p for p in paths if _has_provider_paths({p}, _GEMINI_PREFIXES)]}"
        )
        assert not _has_provider_paths(paths, _CODEX_PREFIXES), (
            f"Found codex paths in claude+copilot update: "
            f"{[p for p in paths if _has_provider_paths({p}, _CODEX_PREFIXES)]}"
        )

    def test_update_claude_gemini_excludes_copilot_codex(
        self,
        claude_gemini_project: Path,
    ) -> None:
        """T3: When claude_code + gemini are enabled, update must include
        .claude/ and .gemini/ paths but NOT .github/ or .codex/.
        """
        result = update(claude_gemini_project, dry_run=True)
        paths = _changed_relative_paths(result, claude_gemini_project)

        # Exclude common .github/ paths that come from VCS templates (not copilot).
        # VCS trees are provider-independent and always included.
        provider_copilot_paths = {
            p
            for p in paths
            if any(p.startswith(pfx) or p == pfx for pfx in _COPILOT_PREFIXES)
            and not _is_vcs_template_path(p)
        }
        assert not provider_copilot_paths, (
            f"Found copilot-specific paths in claude+gemini update: {provider_copilot_paths}"
        )
        assert not _has_provider_paths(paths, _CODEX_PREFIXES), (
            f"Found codex paths in claude+gemini update: "
            f"{[p for p in paths if _has_provider_paths({p}, _CODEX_PREFIXES)]}"
        )

    def test_update_no_manifest_falls_back_to_all_providers(
        self,
        no_manifest_project: Path,
    ) -> None:
        """T-R3: Without a manifest, update must fall back to all providers
        (backward compatibility).
        """
        result = update(no_manifest_project, dry_run=True)

        # All provider paths should be present (the project was installed with
        # all defaults, then manifest was removed).
        all_relative = {_safe_relative(c.path, no_manifest_project) for c in result.changes}

        # At minimum, we expect paths from multiple providers to exist.
        has_claude = _has_provider_paths(all_relative, _CLAUDE_PREFIXES)
        has_copilot = _has_provider_paths(all_relative, _COPILOT_PREFIXES)
        has_gemini = _has_provider_paths(all_relative, _GEMINI_PREFIXES)
        has_codex = _has_provider_paths(all_relative, _CODEX_PREFIXES)

        assert has_claude, "Expected claude paths in all-provider fallback"
        assert has_copilot, "Expected copilot paths in all-provider fallback"
        assert has_gemini, "Expected gemini paths in all-provider fallback"
        assert has_codex, "Expected codex paths in all-provider fallback"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# VCS template paths start with .github/ but are NOT copilot-specific.
# They come from ``_VCS_TEMPLATE_TREES["github"]`` which maps
# ``github_templates`` -> ``.github/``.
_VCS_TEMPLATE_SUBDIRS = (
    ".github/ISSUE_TEMPLATE",
    ".github/PULL_REQUEST_TEMPLATE",
    ".github/workflows",
    ".github/CODEOWNERS",
)


def _is_vcs_template_path(path: str) -> bool:
    """Return True if a .github/ path belongs to VCS templates, not copilot."""
    return any(path.startswith(prefix) for prefix in _VCS_TEMPLATE_SUBDIRS)


def _safe_relative(path: Path, root: Path) -> str:
    """Return POSIX relative path, falling back to str if not relative."""
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)
