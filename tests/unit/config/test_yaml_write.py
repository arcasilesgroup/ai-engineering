"""Tests for update_manifest_field (comment-preserving YAML writes).

Covers:
- Write providers.stacks to a manifest with comments -> comments preserved
- Write providers.ides -> value updated, rest unchanged
- Nested field work_items.provider -> updated correctly
- Error cases: missing file, missing intermediate key, missing final key
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.config.loader import load_manifest_config, update_manifest_field

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_MANIFEST = """\
# ai-engineering manifest

# === USER CONFIGURATION ===
# Edit this section to match your project.

schema_version: "2.0"
framework_version: "0.4.0"
name: test-project
version: "1.0.0"

# Providers
providers:
  vcs: github
  ides: [claude_code, github_copilot]
  stacks: [python]

# Work items
work_items:
  provider: github # 'github' or 'azure_devops'
  azure_devops:
    area_path: "Project\\\\TeamName"
  github:
    team_label: "team:core"
  hierarchy:
    feature: never_close # features are never closed by AI
    user_story: close_on_pr
    task: close_on_pr
    bug: close_on_pr

# Quality gates
quality:
  coverage: 80
  duplication: 3
  cyclomatic: 10
  cognitive: 15
"""


@pytest.fixture()
def manifest_project(tmp_path: Path) -> Path:
    """Create a temp project with a manifest.yml containing comments."""
    ai_dir = tmp_path / ".ai-engineering"
    ai_dir.mkdir()
    (ai_dir / "manifest.yml").write_text(SAMPLE_MANIFEST, encoding="utf-8")
    return tmp_path


# ---------------------------------------------------------------------------
# Comment preservation
# ---------------------------------------------------------------------------


class TestCommentPreservation:
    """Verify YAML comments survive a roundtrip write."""

    def test_update_stacks_preserves_comments(self, manifest_project: Path) -> None:
        update_manifest_field(manifest_project, "providers.stacks", ["python", "rust"])

        raw = (manifest_project / ".ai-engineering" / "manifest.yml").read_text(encoding="utf-8")

        # Comments must still be present
        assert "# ai-engineering manifest" in raw
        assert "# === USER CONFIGURATION ===" in raw
        assert "# Providers" in raw
        assert "# Quality gates" in raw

    def test_update_ides_preserves_comments(self, manifest_project: Path) -> None:
        update_manifest_field(manifest_project, "providers.ides", ["claude_code"])

        raw = (manifest_project / ".ai-engineering" / "manifest.yml").read_text(encoding="utf-8")

        assert "# Work items" in raw
        assert "# features are never closed by AI" in raw

    def test_inline_comment_preserved(self, manifest_project: Path) -> None:
        update_manifest_field(manifest_project, "providers.stacks", ["python", "dotnet"])

        raw = (manifest_project / ".ai-engineering" / "manifest.yml").read_text(encoding="utf-8")

        # The inline comment on work_items.provider should survive
        assert "'github' or 'azure_devops'" in raw


# ---------------------------------------------------------------------------
# Value updates
# ---------------------------------------------------------------------------


class TestValueUpdates:
    """Verify the target field is correctly updated."""

    def test_update_stacks_value(self, manifest_project: Path) -> None:
        update_manifest_field(manifest_project, "providers.stacks", ["python", "rust"])

        config = load_manifest_config(manifest_project)
        assert config.providers.stacks == ["python", "rust"]

    def test_update_ides_value(self, manifest_project: Path) -> None:
        update_manifest_field(
            manifest_project,
            "providers.ides",
            ["claude_code", "github_copilot", "codex"],
        )

        config = load_manifest_config(manifest_project)
        assert config.providers.ides == ["claude_code", "github_copilot", "codex"]

    def test_update_work_items_provider(self, manifest_project: Path) -> None:
        update_manifest_field(manifest_project, "work_items.provider", "azure_devops")

        config = load_manifest_config(manifest_project)
        assert config.work_items.provider == "azure_devops"

    def test_update_quality_coverage(self, manifest_project: Path) -> None:
        update_manifest_field(manifest_project, "quality.coverage", 90)

        config = load_manifest_config(manifest_project)
        assert config.quality.coverage == 90

    def test_update_top_level_field(self, manifest_project: Path) -> None:
        update_manifest_field(manifest_project, "name", "new-project-name")

        config = load_manifest_config(manifest_project)
        assert config.name == "new-project-name"

    def test_rest_of_manifest_unchanged(self, manifest_project: Path) -> None:
        update_manifest_field(manifest_project, "providers.stacks", ["rust"])

        config = load_manifest_config(manifest_project)
        # Other fields remain as set in the fixture
        assert config.providers.vcs == "github"
        assert config.providers.ides == ["claude_code", "github_copilot"]
        assert config.work_items.provider == "github"
        assert config.quality.coverage == 80
        assert config.name == "test-project"


# ---------------------------------------------------------------------------
# Error cases
# ---------------------------------------------------------------------------


class TestErrors:
    """Verify proper errors for invalid inputs."""

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError):
            update_manifest_field(tmp_path, "providers.stacks", ["python"])

    def test_missing_intermediate_key_raises(self, manifest_project: Path) -> None:
        with pytest.raises(KeyError, match="nonexistent"):
            update_manifest_field(manifest_project, "nonexistent.stacks", ["python"])

    def test_missing_final_key_raises(self, manifest_project: Path) -> None:
        with pytest.raises(KeyError, match="missing_field"):
            update_manifest_field(manifest_project, "providers.missing_field", "value")
