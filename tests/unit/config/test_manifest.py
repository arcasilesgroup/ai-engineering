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

from ai_engineering.config.loader import load_manifest_config, load_manifest_root_entry_points
from ai_engineering.config.manifest import (
    AgentsConfig,
    CicdConfig,
    DocumentationConfig,
    HotPathSlosConfig,
    ManifestConfig,
    OwnershipConfig,
    ProvidersConfig,
    QualityConfig,
    SkillsConfig,
    TelemetryConfig,
    WorkItemsConfig,
)
from ai_engineering.release.version_bump import detect_current_version

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / ".ai-engineering" / "manifest.yml"
TEMPLATE_MANIFEST_PATH = (
    REPO_ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "manifest.yml"
)


@pytest.fixture()
def real_manifest_data() -> dict:
    """Load the real manifest.yml as a raw dict."""
    raw = MANIFEST_PATH.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    assert isinstance(data, dict)
    return data


@pytest.fixture()
def template_manifest_data() -> dict:
    """Load the bundled template manifest.yml as a raw dict."""
    raw = TEMPLATE_MANIFEST_PATH.read_text(encoding="utf-8")
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

    @staticmethod
    def _assert_control_plane_authority_model(manifest_data: dict) -> None:
        control_plane = manifest_data.get("control_plane")
        assert isinstance(control_plane, dict)

        constitutional_authority = control_plane.get("constitutional_authority")
        assert isinstance(constitutional_authority, dict)
        assert constitutional_authority.get("primary") == "CONSTITUTION.md"

        # spec-123 D-123-17: workspace-charter stub deleted; compatibility
        # aliases collapse to empty list. The single canonical source is
        # CONSTITUTION.md at repo root.
        compatibility_aliases = constitutional_authority.get("compatibility_aliases")
        assert isinstance(compatibility_aliases, list)
        assert compatibility_aliases == []

        manifest_field_roles = control_plane.get("manifest_field_roles")
        assert isinstance(manifest_field_roles, dict)

        canonical_input = manifest_field_roles.get("canonical_input")
        assert isinstance(canonical_input, list)
        assert "session.context_files" in canonical_input
        assert "ownership.root_entry_points" in canonical_input

        generated_projection = manifest_field_roles.get("generated_projection")
        assert isinstance(generated_projection, list)
        assert "skills" in generated_projection
        assert "agents" in generated_projection

        descriptive_metadata = manifest_field_roles.get("descriptive_metadata")
        assert isinstance(descriptive_metadata, list)
        assert "framework_version" in descriptive_metadata
        assert "version" in descriptive_metadata

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
        assert config.framework_version == detect_current_version(REPO_ROOT)

    def test_name_and_version(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.name == "ai-engineering"
        assert config.version == "1.0.0"

    def test_session_context_prefers_root_constitution(self, real_manifest_data: dict) -> None:
        session = real_manifest_data.get("session")
        assert isinstance(session, dict)

        context_files = session.get("context_files")
        assert isinstance(context_files, list)
        assert "CONSTITUTION.md" in context_files
        assert ".ai-engineering/CONSTITUTION.md" not in context_files

    def test_template_session_context_prefers_root_constitution(
        self, template_manifest_data: dict
    ) -> None:
        session = template_manifest_data.get("session")
        assert isinstance(session, dict)

        context_files = session.get("context_files")
        assert isinstance(context_files, list)
        assert "CONSTITUTION.md" in context_files
        assert ".ai-engineering/CONSTITUTION.md" not in context_files

    def test_control_plane_authority_table_exists(self, real_manifest_data: dict) -> None:
        self._assert_control_plane_authority_model(real_manifest_data)

    def test_template_control_plane_authority_table_exists(
        self, template_manifest_data: dict
    ) -> None:
        self._assert_control_plane_authority_model(template_manifest_data)


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
        assert "claude-code" in config.ai_providers.enabled
        assert "github-copilot" in config.ai_providers.enabled

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
        # spec-116/117/120: 49 -> 52 (ai-design, ai-animation, ai-canvas,
        # ai-eval-gate). spec-122 (sub-001 hygiene): 52 -> 51 after pruning
        # the legacy /ai-eval-gate skill that duplicated /ai-release-gate.
        # spec-123 (D-123-08/10): 51 -> 49 after deleting the memory
        # subsystem skills /ai-remember and /ai-dream.
        # spec-119 (registered post-squash): 49 -> 50 with /ai-eval skill.
        # spec-127 sub-005 (M4 D-127-04/10/11/12): 50 -> 48 after renames + mergers
        # (delete ai-run, ai-board-discover, ai-board-sync, ai-release-gate;
        # create ai-help, ai-board; rename 8 skills). Spec target was 46;
        # achieved 48 — see CHANGELOG M4 section for the gap explanation.
        assert config.skills.total == len(config.skills.registry) == 48

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
        # spec-116+: bumped 10 -> 11 with addition of evaluator agent.
        # spec-122 (sub-001 hygiene): 11 -> 10 after retiring the standalone
        # `evaluator` agent in favour of the consolidated verify pipeline.
        # spec-127 sub-005 (M4 D-127-12): 10 -> 9 after deleting
        # `run-orchestrator` (functionality absorbed by `autopilot --backlog`).
        assert config.agents.total == 9

    def test_names(self, real_manifest_data: dict) -> None:
        config = ManifestConfig.model_validate(real_manifest_data)
        assert "build" in config.agents.names
        assert "autopilot" in config.agents.names
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
        # spec-122-a (D-122-07): the `tooling` top-level key was removed from
        # manifest.yml because it duplicated `required_tools` (the spec-101
        # source of truth for `ai-eng install` / `ai-eng doctor --fix`). The
        # Pydantic field stays for back-compat with old manifests; new
        # manifests resolve it to the default empty list.
        config = ManifestConfig.model_validate(real_manifest_data)
        assert config.tooling == []


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
# Hot-path SLOs (spec-114 D-114-02)
# ---------------------------------------------------------------------------


class TestHotPathSlos:
    """Hot-path SLO budgets driving ``ai-eng doctor --check hot-path`` (G-2)."""

    def test_defaults_present(self) -> None:
        """An empty manifest still exposes the spec-112 D-112-08 budgets."""
        config = ManifestConfig()
        assert config.hot_path_slos.pre_commit_p95_ms == 1000
        assert config.hot_path_slos.pre_push_p95_ms == 5000
        assert config.hot_path_slos.skill_invocation_overhead_p95_ms == 200
        assert config.hot_path_slos.rolling_window_events == 100

    def test_real_manifest_block(self, real_manifest_data: dict) -> None:
        """The canonical manifest opts into the same budgets explicitly."""
        config = ManifestConfig.model_validate(real_manifest_data)
        assert isinstance(config.hot_path_slos, HotPathSlosConfig)
        assert config.hot_path_slos.pre_commit_p95_ms == 1000
        assert config.hot_path_slos.pre_push_p95_ms == 5000
        assert config.hot_path_slos.skill_invocation_overhead_p95_ms == 200
        assert config.hot_path_slos.rolling_window_events == 100

    def test_partial_override(self, tmp_project: Path) -> None:
        """Operators can tighten a single budget without restating the rest."""
        manifest = tmp_project / ".ai-engineering" / "manifest.yml"
        manifest.write_text("hot_path_slos:\n  pre_commit_p95_ms: 750\n")
        config = load_manifest_config(tmp_project)
        assert config.hot_path_slos.pre_commit_p95_ms == 750
        # Untouched fields fall back to spec defaults.
        assert config.hot_path_slos.pre_push_p95_ms == 5000
        assert config.hot_path_slos.skill_invocation_overhead_p95_ms == 200
        assert config.hot_path_slos.rolling_window_events == 100


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

    def test_missing_file_returns_no_root_entry_point_contract(self, tmp_path: Path) -> None:
        assert load_manifest_root_entry_points(tmp_path) is None

    def test_yaml_only_comment_returns_defaults(self, tmp_project: Path) -> None:
        manifest = tmp_project / ".ai-engineering" / "manifest.yml"
        manifest.write_text("# just a comment\n")

        config = load_manifest_config(tmp_project)

        assert isinstance(config, ManifestConfig)
        assert config.name == ""

    def test_present_manifest_returns_root_entry_point_contract(self, tmp_project: Path) -> None:
        manifest = tmp_project / ".ai-engineering" / "manifest.yml"
        manifest.write_text(
            "ownership:\n"
            "  root_entry_points:\n"
            "    CLAUDE.md:\n"
            "      owner: team\n"
            "      canonical_source: CONSTITUTION.md\n"
            "      runtime_role: ide-overlay\n"
            "      sync:\n"
            "        mode: copy\n"
            "        template_path: src/ai_engineering/templates/project/CLAUDE.md\n"
            "        mirror_paths: []\n",
            encoding="utf-8",
        )

        root_entry_points = load_manifest_root_entry_points(tmp_project)

        assert root_entry_points is not None
        assert root_entry_points["CLAUDE.md"].owner == "team"


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
