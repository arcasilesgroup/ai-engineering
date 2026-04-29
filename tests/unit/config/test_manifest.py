"""Tests for ManifestConfig model and load_manifest_config loader.

Covers:
- Parsing the real manifest.yml from this repository
- Partial manifest (only providers section)
- Empty file -> all defaults
- Missing file -> all defaults
- All config fields accessible via typed attributes
- Nested field access (providers.stacks, quality.coverage, etc.)
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from ai_engineering.config.loader import load_manifest_config
from ai_engineering.config.manifest import (
    AgentsConfig,
    CicdConfig,
    DocumentationConfig,
    ManifestConfig,
    OwnershipConfig,
    ProvidersConfig,
    QualityConfig,
    SkillsConfig,
    TelemetryConfig,
    WorkItemsConfig,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / ".ai-engineering" / "manifest.yml"


@pytest.fixture()
def real_manifest_data() -> dict:
    """Load the real manifest.yml as a raw dict."""
    raw = MANIFEST_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    assert isinstance(data, dict)
    return data


@pytest.fixture()
def tmp_project(tmp_path: Path) -> Path:
    """Create a temp directory with .ai-engineering/ structure."""
    ai_dir = tmp_path / ".ai-engineering"
    ai_dir.mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# Real manifest parsing
# ---------------------------------------------------------------------------


class TestRealManifest:
    """Parse the actual manifest.yml from this repository."""

    def test_model_validate_succeeds(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config, ManifestConfig)

    def test_load_from_repo_root(self) -> None:
        config = load_manifest_config(REPO_ROOT)
        assert isinstance(config, ManifestConfig)
        assert config.name == "ai-engineering"

    def test_schema_version(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.schema_version == "2.0"

    def test_framework_version(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.framework_version == "0.4.0"

    def test_name_and_version(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.name == "ai-engineering"
        assert config.version == "1.0.0"


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------


class TestProviders:
    def test_vcs(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.providers.vcs == "github"

    def test_ides(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert "terminal" in config.providers.ides
        assert "claude_code" in config.ai_providers.enabled
        assert "github_copilot" in config.ai_providers.enabled

    def test_stacks(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.providers.stacks == ["python"]


# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------


class TestQuality:
    def test_coverage(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.quality.coverage == 80

    def test_duplication(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.quality.duplication == 3

    def test_cyclomatic(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.quality.cyclomatic == 10

    def test_cognitive(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.quality.cognitive == 15


# ---------------------------------------------------------------------------
# Work items
# ---------------------------------------------------------------------------


class TestWorkItems:
    def test_provider(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.work_items.provider == "github"

    def test_azure_devops_area_path(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.work_items.azure_devops.area_path == "Project\\TeamName"

    def test_github_team_label(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.work_items.github.team_label == "team:core"

    def test_hierarchy(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.work_items.hierarchy.feature == "never_close"
        assert config.work_items.hierarchy.bug == "close_on_pr"


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------


class TestDocumentation:
    def test_auto_update(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.documentation.auto_update.readme is True
        assert config.documentation.auto_update.changelog is True
        assert config.documentation.auto_update.solution_intent is True

    def test_external_portal(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.documentation.external_portal.enabled is False
        assert config.documentation.external_portal.update_method == "pr"


# ---------------------------------------------------------------------------
# CI/CD
# ---------------------------------------------------------------------------


class TestCicd:
    def test_standards_url_null(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.cicd.standards_url is None


# ---------------------------------------------------------------------------
# Skills
# ---------------------------------------------------------------------------


class TestSkills:
    def test_total(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        # spec-107: bumped 47 -> 48 with addition of /ai-mcp-sentinel skill.
        # spec-111: bumped 48 -> 49 with addition of /ai-research skill.
        assert config.skills.total == len(config.skills.registry) == 49

    def test_prefix(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.skills.prefix == "ai-"

    def test_registry_populated(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert len(config.skills.registry) > 0
        assert "ai-brainstorm" in config.skills.registry

    def test_skill_entry_fields(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        brainstorm = config.skills.registry["ai-brainstorm"]
        assert brainstorm.type == "workflow"
        assert "planning" in brainstorm.tags


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class TestAgents:
    def test_total(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.agents.total == 10

    def test_names(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert "build" in config.agents.names
        assert "run-orchestrator" in config.agents.names
        assert "verify" in config.agents.names


# ---------------------------------------------------------------------------
# Ownership
# ---------------------------------------------------------------------------


class TestOwnership:
    def test_framework_paths(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert len(config.ownership.framework) > 0
        assert ".claude/skills/**" in config.ownership.framework

    def test_team_paths(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert ".ai-engineering/contexts/team/**" in config.ownership.team

    def test_system_paths(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert ".ai-engineering/state/**" in config.ownership.system


# ---------------------------------------------------------------------------
# Tooling
# ---------------------------------------------------------------------------


class TestTooling:
    def test_tooling_list(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert "ruff" in config.tooling
        assert "pytest" in config.tooling
        assert "gitleaks" in config.tooling


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------


class TestTelemetry:
    def test_consent(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.telemetry.consent == "strict-opt-in"

    def test_default(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.telemetry.default == "disabled"


# ---------------------------------------------------------------------------
# Partial manifest
# ---------------------------------------------------------------------------


class TestPartialManifest:
    def test_only_providers(self, tmp_project: Path) -> None:
        manifest = tmp_project / ".ai-engineering" / "manifest.yml"
        manifest.write_text("providers:\n  vcs: gitlab\n  stacks: [rust, python]\n")

        config = load_manifest_config(tmp_project)

        assert config.providers.vcs == "gitlab"
        assert config.providers.stacks == ["rust", "python"]
        # Other sections get defaults
        assert config.quality.coverage == 80
        assert config.name == ""
        assert config.tooling == []

    def test_only_quality(self, tmp_project: Path) -> None:
        manifest = tmp_project / ".ai-engineering" / "manifest.yml"
        manifest.write_text("quality:\n  coverage: 90\n  duplication: 5\n")

        config = load_manifest_config(tmp_project)

        assert config.quality.coverage == 90
        assert config.quality.duplication == 5
        # Unset quality fields get defaults
        assert config.quality.cyclomatic == 10
        assert config.quality.cognitive == 15
        # Other sections get defaults
        assert config.providers.vcs == "github"

    def test_only_name(self, tmp_project: Path) -> None:
        manifest = tmp_project / ".ai-engineering" / "manifest.yml"
        manifest.write_text("name: my-project\n")

        config = load_manifest_config(tmp_project)
        assert config.name == "my-project"
        assert config.schema_version == "2.0"


# ---------------------------------------------------------------------------
# Empty and missing file
# ---------------------------------------------------------------------------


class TestEmptyAndMissing:
    def test_empty_file_returns_defaults(self, tmp_project: Path) -> None:
        manifest = tmp_project / ".ai-engineering" / "manifest.yml"
        manifest.write_text("")

        config = load_manifest_config(tmp_project)

        assert isinstance(config, ManifestConfig)
        assert config.schema_version == "2.0"
        assert config.name == ""
        assert config.providers.vcs == "github"
        assert config.quality.coverage == 80

    def test_missing_file_returns_defaults(self, tmp_path: Path) -> None:
        # No .ai-engineering directory at all
        config = load_manifest_config(tmp_path)

        assert isinstance(config, ManifestConfig)
        assert config.schema_version == "2.0"
        assert config.name == ""
        assert config.providers.vcs == "github"
        assert config.quality.coverage == 80

    def test_yaml_only_comment_returns_defaults(self, tmp_project: Path) -> None:
        manifest = tmp_project / ".ai-engineering" / "manifest.yml"
        manifest.write_text("# just a comment\n")

        config = load_manifest_config(tmp_project)

        assert isinstance(config, ManifestConfig)
        assert config.name == ""


# ---------------------------------------------------------------------------
# Typed attribute access
# ---------------------------------------------------------------------------


class TestTypedAccess:
    """Verify all nested configs are properly typed, not raw dicts."""

    def test_providers_type(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config.providers, ProvidersConfig)

    def test_quality_type(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config.quality, QualityConfig)

    def test_work_items_type(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config.work_items, WorkItemsConfig)

    def test_documentation_type(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config.documentation, DocumentationConfig)

    def test_cicd_type(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config.cicd, CicdConfig)

    def test_skills_type(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config.skills, SkillsConfig)

    def test_agents_type(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config.agents, AgentsConfig)

    def test_ownership_type(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config.ownership, OwnershipConfig)

    def test_telemetry_type(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config.telemetry, TelemetryConfig)
