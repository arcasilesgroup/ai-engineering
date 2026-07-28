"""Validate sync_command_mirrors.py metadata and drift detection.

Tests the sync script's internal constants match the current architecture
and verifies --check mode reports zero drift against the real repo.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_MANIFEST_TEMPLATE = """\
name: test-project
version: 1.0.0
surfaces:
    enabled: [{providers}]
"""

_ROOT_ENTRY_POINTS_MANIFEST_TEMPLATE = """\
name: test-project
version: 1.0.0
surfaces:
    enabled: [{providers}]
ownership:
    root_entry_points:
        "CLAUDE.md":
            owner: framework
            canonical_source: CLAUDE.md
            runtime_role: ide-overlay
            sync:
                mode: copy
                template_path: src/ai_engineering/templates/project/CLAUDE.md
                mirror_paths: [".claude/ignored-CLAUDE.md"]
        "AGENTS.md":
            owner: framework
            canonical_source: scripts/sync_command_mirrors.py:generate_agents_md
            runtime_role: shared-runtime-contract
            sync:
                mode: generate
                template_path: src/ai_engineering/templates/project/AGENTS.md
                mirror_paths: []
        ".github/copilot-instructions.md":
            owner: framework
            canonical_source: src/ai_engineering/templates/project/copilot-instructions.md
            runtime_role: ide-overlay
            sync:
                mode: render
                template_path: src/ai_engineering/templates/project/copilot-instructions.md
                mirror_paths: []
"""

# Expected architecture values (post spec-127 sub-005 D-127-12 — run-orchestrator
# absorbed by autopilot --backlog).
_EXPECTED_AGENT_COUNT = 9
_EXPECTED_AGENT_NAMES = frozenset(
    {
        "autopilot",
        "build",
        "explore",
        "advise",  # spec-134 D-134-06: renamed from "guard"
        "onboard",  # spec-134 D-134-06: renamed from "guide"
        "plan",
        "review",
        "simplify",
        "verify",
    }
)


class TestSyncScriptMetadata:
    """Verify sync script constants match current architecture."""

    def test_agent_metadata_count(self) -> None:
        from scripts.sync_command_mirrors import AGENT_METADATA

        assert len(AGENT_METADATA) == _EXPECTED_AGENT_COUNT, (
            f"AGENT_METADATA has {len(AGENT_METADATA)} entries, expected {_EXPECTED_AGENT_COUNT}"
        )

    def test_agent_metadata_names(self) -> None:
        from scripts.sync_command_mirrors import AGENT_METADATA

        names = set(AGENT_METADATA.keys())
        assert names == _EXPECTED_AGENT_NAMES, (
            f"Missing: {_EXPECTED_AGENT_NAMES - names}, Extra: {names - _EXPECTED_AGENT_NAMES}"
        )

    def test_all_agents_have_required_meta_fields(self) -> None:
        from scripts.sync_command_mirrors import AGENT_METADATA

        for name, meta in AGENT_METADATA.items():
            assert meta.display_name, f"{name}: missing display_name"
            assert meta.description, f"{name}: missing description"
            assert meta.model, f"{name}: missing model"
            assert meta.effort, f"{name}: missing effort"
            assert meta.color, f"{name}: missing color"
            assert meta.copilot_renamed_tools, f"{name}: empty copilot_renamed_tools"
            assert meta.copilot_native_tools, f"{name}: empty copilot_native_tools"
            assert meta.claude_tools, f"{name}: empty claude_tools"


class TestEffortModelSemantics:
    """spec-189 D-189-04: `effort` is the sole semantic source for agent model."""

    def test_every_agent_has_valid_effort(self) -> None:
        from scripts.sync_command_mirrors import AGENT_METADATA
        from scripts.sync_mirrors.core import VALID_EFFORTS

        assert sorted(VALID_EFFORTS) == ["cheap", "high", "mid"]
        for name, meta in AGENT_METADATA.items():
            assert meta.effort in VALID_EFFORTS, (
                f"{name}: effort {meta.effort!r} not in {sorted(VALID_EFFORTS)}"
            )

    def test_effort_to_model_round_trips(self) -> None:
        from scripts.sync_command_mirrors import _effort_to_model, _model_to_effort

        # Forward mapping is the documented Claude-valid contract.
        assert _effort_to_model("high") == "opus"
        assert _effort_to_model("mid") == "sonnet"
        assert _effort_to_model("cheap") == "haiku"
        # Round-trip: effort -> model -> effort is the identity.
        for effort in ("cheap", "mid", "high"):
            assert _model_to_effort(_effort_to_model(effort)) == effort
        # Unknown inputs fail loudly rather than silently defaulting.
        with pytest.raises(ValueError):
            _effort_to_model("gigantic")
        with pytest.raises(ValueError):
            _model_to_effort("gpt-9")

    def test_agent_meta_model_matches_effort(self) -> None:
        # The retained `model` literal must mirror the effort-derived model so
        # AGENT_METADATA never carries internally contradictory data.
        from scripts.sync_command_mirrors import AGENT_METADATA, _effort_to_model

        for name, meta in AGENT_METADATA.items():
            assert meta.model == _effort_to_model(meta.effort), (
                f"{name}: model {meta.model!r} != effort-derived {_effort_to_model(meta.effort)!r}"
            )

    def test_validator_passes_on_canonical_sources(self) -> None:
        from scripts.sync_command_mirrors import (
            discover_agents,
            discover_skills,
            validate_canonical,
        )

        errors, _warnings = validate_canonical(discover_skills(), discover_agents())
        drift = [e for e in errors if "disagrees with effort" in e]
        assert not drift, f"canonical model/effort drift: {drift}"

    def test_validator_fires_on_model_effort_mismatch(self) -> None:
        # Seed a synthetic canonical agent whose hand-typed model disagrees with
        # its AGENT_METADATA effort. `build` is effort=high (-> opus); claiming
        # `model: sonnet` MUST be flagged as a build-time canonical error.
        from scripts.sync_command_mirrors import CLAUDE_AGENTS, validate_canonical

        seeded = [("build", {"name": "Build", "model": "sonnet"}, CLAUDE_AGENTS / "ai-build.md")]
        errors, _warnings = validate_canonical([], seeded)
        assert any("disagrees with effort" in e for e in errors), (
            "validator did not fire on a seeded model/effort mismatch"
        )

    def test_validator_quiet_on_matching_model(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_AGENTS, validate_canonical

        matched = [("build", {"name": "Build", "model": "opus"}, CLAUDE_AGENTS / "ai-build.md")]
        errors, _warnings = validate_canonical([], matched)
        assert not any("disagrees with effort" in e for e in errors)


class TestCrossReferenceResolution:
    """Verify sync cross-reference validation follows enabled root surfaces."""

    def _write_manifest(self, root: Path, providers: list[str]) -> None:
        manifest = root / ".ai-engineering" / "manifest.yml"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            _MANIFEST_TEMPLATE.format(
                providers=", ".join(providers),
                primary=providers[0],
            ),
            encoding="utf-8",
        )

    def _write_manifest_with_root_entry_points(self, root: Path, providers: list[str]) -> None:
        manifest = root / ".ai-engineering" / "manifest.yml"
        manifest.parent.mkdir(parents=True, exist_ok=True)
        manifest.write_text(
            _ROOT_ENTRY_POINTS_MANIFEST_TEMPLATE.format(
                providers=", ".join(providers),
                primary=providers[0],
            ),
            encoding="utf-8",
        )

    def test_resolve_cross_reference_files_uses_antigravity_agents_root(
        self, tmp_path: Path
    ) -> None:
        self._write_manifest(tmp_path, ["claude-code", "github-copilot", "antigravity"])

        from scripts.sync_command_mirrors import _resolve_cross_reference_files

        resolved = {
            path.relative_to(tmp_path).as_posix()
            for path in _resolve_cross_reference_files(tmp_path)
        }

        # Antigravity shares the AGENTS.md root instruction with Codex/Copilot;
        # GEMINI.md is no longer a current root entry point.
        assert resolved == {
            ".github/copilot-instructions.md",
            "AGENTS.md",
            "CLAUDE.md",
        }

    def test_resolve_cross_reference_files_uses_enabled_providers_only(
        self, tmp_path: Path
    ) -> None:
        self._write_manifest(tmp_path, ["github-copilot"])

        from scripts.sync_command_mirrors import _resolve_cross_reference_files

        resolved = {
            path.relative_to(tmp_path).as_posix()
            for path in _resolve_cross_reference_files(tmp_path)
        }

        assert resolved == {
            ".github/copilot-instructions.md",
            "AGENTS.md",
        }

    def test_resolve_cross_reference_files_includes_manifest_declared_mirror_paths(
        self, tmp_path: Path
    ) -> None:
        self._write_manifest_with_root_entry_points(
            tmp_path,
            ["github-copilot", "antigravity"],
        )

        from scripts.sync_command_mirrors import _resolve_cross_reference_files

        resolved = {
            path.relative_to(tmp_path).as_posix()
            for path in _resolve_cross_reference_files(tmp_path)
        }

        assert resolved == {
            ".github/copilot-instructions.md",
            "AGENTS.md",
        }, (
            "_resolve_cross_reference_files should include manifest-declared mirror_paths "
            "for enabled root entry points and ignore disabled-provider root surfaces"
        )


class TestSyncDriftDetection:
    """Verify sync --check reports zero drift against real repo."""

    def test_check_mode_returns_zero(self, template_hooks_lock) -> None:
        """sync_command_mirrors.py --check should exit 0 (no drift)."""
        from scripts.sync_command_mirrors import sync_all

        with template_hooks_lock():  # serialize vs test_orphan_* probe writes
            exit_code = sync_all(check_only=True)
        assert exit_code == 0, (
            "Mirror drift detected -- run: python scripts/sync_command_mirrors.py"
        )

    def test_discover_skills_matches_filesystem(self) -> None:
        """Discovered skills match canonical .claude/skills/ai-* directories."""
        from scripts.sync_command_mirrors import CLAUDE_SKILLS, discover_skills

        skills = discover_skills()
        expected = {
            d.name.removeprefix("ai-")
            for d in CLAUDE_SKILLS.iterdir()
            if d.is_dir() and d.name.startswith("ai-") and (d / "SKILL.md").is_file()
        }
        actual = {name for name, _, _ in skills}
        assert actual == expected, (
            f"Skill discovery mismatch. Missing: {expected - actual}, Extra: {actual - expected}"
        )

    def test_discover_agents_matches_filesystem(self) -> None:
        """Discovered agents match canonical .claude/agents/ai-*.md files."""
        from scripts.sync_command_mirrors import CLAUDE_AGENTS, discover_agents

        agents = discover_agents()
        expected = {f.stem.removeprefix("ai-") for f in CLAUDE_AGENTS.glob("ai-*.md")}
        actual = {name for name, _, _ in agents}
        assert actual == expected


# -- Generation functions (pure -- input/output, no I/O) ----


class TestGenerationFunctions:
    """Test content generation -- pure functions, no filesystem access."""

    def test_generate_shared_skill_includes_frontmatter(self) -> None:
        # spec-201 D-201-04: the codex and copilot skill generators were
        # deleted with their trees; .agents/skills is the sole generated
        # skill surface left.
        from scripts.sync_command_mirrors import (
            CLAUDE_SKILLS,
            generate_antigravity_skill,
        )

        # Arrange -- use real canonical skill
        skill_path = CLAUDE_SKILLS / "ai-commit" / "SKILL.md"

        # Act
        content = generate_antigravity_skill("commit", skill_path)

        # Assert -- frontmatter comes from canonical
        assert "---" in content
        assert "name: ai-commit" in content
        assert "tags:" in content
        assert len(content) > 100

    def test_generate_copilot_instructions_preserves_slash_command_boundary(self) -> None:
        from scripts.sync_command_mirrors import (
            discover_agents,
            discover_skills,
            generate_copilot_instructions,
        )

        content = generate_copilot_instructions(discover_skills(), discover_agents())

        # Slash-command boundary preserved post-sub-004 simplification: copilot
        # instructions explicitly call out that `/ai-*` are IDE slash commands
        # rather than `ai-eng` CLI subcommands.
        assert "`/ai-start`" in content
        assert "`/ai-*` are IDE slash" in content
        assert "not `ai-eng` CLI subcommands" in content

    def test_generate_opencode_agent_wrapper_format(self) -> None:
        # spec-201 D-201-23: `.codex/agents` was a namespace squat Codex
        # never read. The generator survives only for OpenCode, whose
        # files previously claimed the codex-agents family.
        from scripts.sync_command_mirrors import (
            CLAUDE_AGENTS,
            generate_opencode_agent_markdown,
        )

        # Arrange
        agent_path = CLAUDE_AGENTS / "ai-build.md"

        # Act
        content = generate_opencode_agent_markdown("build", agent_path)

        # Assert -- content is fully embedded from canonical source
        assert len(content) > 100
        assert "mirror_family: opencode-agents" in content

    def test_generate_copilot_agent_includes_per_agent_metadata(self) -> None:
        from scripts.sync_command_mirrors import (
            AGENT_METADATA,
            CLAUDE_AGENTS,
            generate_copilot_agent,
        )

        # Arrange
        meta = AGENT_METADATA["explore"]
        agent_path = CLAUDE_AGENTS / "ai-explore.md"

        # Act
        content = generate_copilot_agent("explore", meta, agent_path)

        # Assert -- spec-107 D-107-03 renamed Explorer -> ai-explore for
        # cross-IDE parity (Claude/Codex/Antigravity already use the canonical
        # ai-explore slug).
        assert 'name: "ai-explore"' in content
        # spec-189 D-189-04: copilot model: is derived from effort. explore is
        # effort=mid -> sonnet (was hard-coded opus before the effort source).
        assert "model: sonnet" in content
        # `color` is intentionally omitted: GitHub Copilot's documented
        # custom-agents schema does not include a color field, matching
        # the Cursor/Antigravity strip policy.
        assert "color:" not in content
        assert "readFile" in content  # explore has limited tools
        assert "editFiles" not in content  # explore is read-only

    def test_generate_specialist_agent_adds_internal_provenance(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_AGENTS, generate_specialist_agent

        content = generate_specialist_agent(CLAUDE_AGENTS / "reviewer-correctness.md")

        assert "mirror_family: specialist-agents" in content
        assert "generated_by: ai-eng sync" in content
        assert "canonical_source: .claude/agents/reviewer-correctness.md" in content
        assert "edit_policy: generated-do-not-edit" in content
        assert "You are a senior reviewer specializing in FUNCTIONAL CORRECTNESS" in content

    def test_install_claude_specialist_template_carries_provenance(self) -> None:
        # spec-159 D-159-05 (corrected): the `.claude` install TEMPLATE for a
        # specialist agent is a GENERATED mirror carrying governed provenance
        # frontmatter (canonical body + provenance), enforced by
        # validator/_check_claude_specialist_agents_mirror. Only the authored
        # canonical `.claude/agents/<name>.md` source is provenance-free. The
        # dogfood `ai-eng update --preview` "updated" delta on these files is
        # by design. An earlier draft wrote the template verbatim; that violated
        # the mirror-sync governance contract and is reverted.
        from scripts.sync_command_mirrors import CLAUDE_AGENTS, generate_specialist_agent

        canonical = CLAUDE_AGENTS / "reviewer-correctness.md"

        # The authored canonical source carries NO provenance.
        canonical_text = canonical.read_text(encoding="utf-8")
        assert "mirror_family: specialist-agents" not in canonical_text

        # The generated `.claude` install template (and copilot mirrors) DO
        # carry provenance frontmatter, matching the validator's expected shape.
        provenance = generate_specialist_agent(canonical)
        assert provenance != canonical_text
        assert "mirror_family: specialist-agents" in provenance
        assert "canonical_source: .claude/agents/reviewer-correctness.md" in provenance
        assert "edit_policy: generated-do-not-edit" in provenance

    def test_copilot_agent_tools_and_delegation_match_metadata(self) -> None:
        from scripts.sync_command_mirrors import (
            AGENT_METADATA,
            CLAUDE_AGENTS,
            generate_copilot_agent,
        )
        from scripts.sync_mirrors.core import _translate_copilot_tools

        for name, meta in AGENT_METADATA.items():
            content = generate_copilot_agent(name, meta, CLAUDE_AGENTS / f"ai-{name}.md")
            frontmatter = content.split("---", 2)[1]
            # spec-189 D-189-06: the emitted tools are the map-translated renamed
            # tools merged with the passthrough native tools, then the injected
            # delegation `agent` tool when subagents are declared.
            expected_tools = sorted(
                _translate_copilot_tools(meta.copilot_renamed_tools)
                | set(meta.copilot_native_tools)
            )
            if meta.copilot_agents:
                expected_tools.append("agent")

            assert f"tools: [{', '.join(expected_tools)}]" in frontmatter
            if meta.copilot_agents:
                assert f"agents: [{', '.join(meta.copilot_agents)}]" in frontmatter
            else:
                assert "\nagents:" not in frontmatter

    def test_generate_install_claude_skill_copies_content(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_SKILLS, generate_install_claude_skill

        skill_path = CLAUDE_SKILLS / "ai-commit" / "SKILL.md"
        content = generate_install_claude_skill(skill_path)
        # Should be an exact copy
        assert content == skill_path.read_text(encoding="utf-8")

    def test_generate_install_codex_surface_copies_content(self) -> None:
        from scripts.sync_command_mirrors import ROOT, generate_install_codex_surface

        surface_path = ROOT / ".codex" / "hooks.json"
        content = generate_install_codex_surface(surface_path)
        assert content == surface_path.read_text(encoding="utf-8")

    def test_generate_agents_md_preserves_provider_rows_and_counts(self) -> None:
        from scripts.sync_command_mirrors import (
            discover_agents,
            discover_skills,
            generate_agents_md,
        )

        skills = discover_skills()
        agents = discover_agents()

        content = generate_agents_md(skill_count=len(skills), agent_count=len(agents))

        # Platform Mirrors table removed (spec-087) -- only check the current
        # shared runtime contract content.
        assert f"## Skills ({len(skills)})" in content
        assert "Canonical skills and agents live under `.claude/`" in content
        assert f"| Skills ({len(skills)}) | `.claude/skills/ai-<name>/SKILL.md` |" in content
        assert f"| Agents ({len(agents)}) | `.claude/agents/ai-<name>.md` |" in content
        assert (
            "| Placement contract | `.ai-engineering/reference/knowledge-placement.md` |" in content
        )

    def test_codex_provider_surfaces_match_install_templates(self) -> None:
        root_hooks = (_PROJECT_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8")
        tpl_hooks = (
            _PROJECT_ROOT
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".codex"
            / "hooks.json"
        ).read_text(encoding="utf-8")
        root_config = (_PROJECT_ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")
        tpl_config = (
            _PROJECT_ROOT
            / "src"
            / "ai_engineering"
            / "templates"
            / "project"
            / ".codex"
            / "config.toml"
        ).read_text(encoding="utf-8")

        assert root_hooks == tpl_hooks
        assert root_config == tpl_config

    def test_codex_hooks_are_bash_only_for_tool_events(self) -> None:
        hooks = json.loads((_PROJECT_ROOT / ".codex" / "hooks.json").read_text(encoding="utf-8"))
        pre = hooks["hooks"]["PreToolUse"]
        post = hooks["hooks"]["PostToolUse"]

        assert all(entry["matcher"] == "Bash" for entry in pre)
        assert all(entry["matcher"] == "Bash" for entry in post)


# -- Validation functions --


class TestValidationFunctions:
    """Test validation logic -- uses tmp_path for filesystem state."""

    def test_validate_runbooks_warns_when_empty(self, tmp_path: Path) -> None:
        # Arrange -- empty runbooks dir (monkeypatch RUNBOOKS_ROOT on the
        # canonical core module; the legacy shim re-exports from there).
        from scripts.sync_command_mirrors import validate_runbooks
        from scripts.sync_mirrors import core as mod

        original = mod.RUNBOOKS_ROOT
        mod.RUNBOOKS_ROOT = tmp_path / "nonexistent"

        # Act
        warnings = validate_runbooks()

        # Assert
        assert any("not found" in w for w in warnings)

        # Cleanup
        mod.RUNBOOKS_ROOT = original

    def test_check_or_write_unchanged_returns_none(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import _check_or_write
        from scripts.sync_mirrors import core as mod

        # Arrange -- file exists with same content
        test_file = tmp_path / "test.md"
        test_file.write_text("hello", encoding="utf-8")

        original_root = mod.ROOT
        mod.ROOT = tmp_path

        try:
            # Act
            result = _check_or_write(test_file, "hello", check_only=False)
            # Assert
            assert result is None  # unchanged
        finally:
            mod.ROOT = original_root

    def test_check_or_write_drift_updates_file(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import _check_or_write
        from scripts.sync_mirrors import core as mod

        # Arrange -- file exists with different content
        test_file = tmp_path / "test.md"
        test_file.write_text("old content", encoding="utf-8")

        original_root = mod.ROOT
        mod.ROOT = tmp_path

        try:
            # Act
            result = _check_or_write(test_file, "new content", check_only=False)
            # Assert
            assert result is not None
            assert "UPDATED" in result
            assert test_file.read_text() == "new content"
        finally:
            mod.ROOT = original_root

    def test_check_or_write_missing_creates_file(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import _check_or_write
        from scripts.sync_mirrors import core as mod

        # Arrange -- file doesn't exist
        test_file = tmp_path / "subdir" / "new.md"

        original_root = mod.ROOT
        mod.ROOT = tmp_path

        try:
            # Act
            result = _check_or_write(test_file, "created", check_only=False)
            # Assert
            assert result is not None
            assert "CREATED" in result
            assert test_file.read_text() == "created"
        finally:
            mod.ROOT = original_root

    def test_check_or_write_check_only_does_not_write(self, tmp_path: Path) -> None:
        from scripts.sync_command_mirrors import _check_or_write
        from scripts.sync_mirrors import core as mod

        # Arrange -- file exists with different content
        test_file = tmp_path / "test.md"
        test_file.write_text("old", encoding="utf-8")

        original_root = mod.ROOT
        mod.ROOT = tmp_path

        try:
            # Act
            result = _check_or_write(test_file, "new", check_only=True)
            # Assert
            assert "DRIFT" in result
            assert test_file.read_text() == "old"  # NOT modified
        finally:
            mod.ROOT = original_root


# -- Canonical content helpers --


class TestCanonicalHelpers:
    """Test read/serialize/format helpers for canonical frontmatter."""

    def test_read_frontmatter_returns_dict(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_SKILLS, read_frontmatter

        fm = read_frontmatter(CLAUDE_SKILLS / "ai-commit" / "SKILL.md")
        assert "name" in fm
        assert "tags" in fm

    def test_read_frontmatter_missing_frontmatter(self, tmp_path: Path) -> None:
        f = tmp_path / "no-fm.md"
        f.write_text("# No frontmatter here\n")

        from scripts.sync_command_mirrors import read_frontmatter

        fm = read_frontmatter(f)
        assert fm == {}

    def test_read_frontmatter_unclosed_fence(self, tmp_path: Path) -> None:
        f = tmp_path / "bad-fm.md"
        f.write_text("---\nname: broken\n# No closing fence\n")

        from scripts.sync_command_mirrors import read_frontmatter

        fm = read_frontmatter(f)
        assert fm == {}

    def test_serialize_frontmatter_round_trip(self) -> None:
        from scripts.sync_command_mirrors import _serialize_frontmatter

        data = {
            "name": "test",
            "version": "1.0.0",
            "description": "A test skill",
            "tags": ["a", "b"],
        }
        result = _serialize_frontmatter(data)
        assert result.startswith("---")
        assert result.endswith("---")
        assert "name: test" in result
        assert "tags: [a, b]" in result

    def test_serialize_frontmatter_preserves_key_order(self) -> None:
        from scripts.sync_command_mirrors import _serialize_frontmatter

        data = {"tags": ["x"], "name": "first", "version": "2.0.0"}
        result = _serialize_frontmatter(data)
        lines = result.splitlines()
        name_idx = next(i for i, ln in enumerate(lines) if ln.startswith("name:"))
        tags_idx = next(i for i, ln in enumerate(lines) if ln.startswith("tags:"))
        assert name_idx < tags_idx

    def test_format_yaml_field_string(self) -> None:
        from scripts.sync_command_mirrors import _format_yaml_field

        assert _format_yaml_field("name", "test") == "name: test"

    def test_format_yaml_field_string_with_special_chars(self) -> None:
        from scripts.sync_command_mirrors import _format_yaml_field

        result = _format_yaml_field("description", "Run tests: unit + integration")
        assert result == 'description: "Run tests: unit + integration"'

    def test_format_yaml_field_list(self) -> None:
        from scripts.sync_command_mirrors import _format_yaml_field

        result = _format_yaml_field("tags", ["a", "b", "c"])
        assert result == "tags: [a, b, c]"

    def test_format_yaml_field_dict(self) -> None:
        from scripts.sync_command_mirrors import _format_yaml_field

        result = _format_yaml_field("requires", {"bins": ["ruff"]})
        assert "requires:" in result
        assert "bins:" in result

    def test_format_yaml_field_integer(self) -> None:
        from scripts.sync_command_mirrors import _format_yaml_field

        assert _format_yaml_field("count", 42) == "count: 42"


# -- Cross-reference translation --


class TestCrossReferenceTranslation:
    """Test translate_refs path translation for each IDE target."""

    def test_translate_skill_path_claude(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Read `.claude/skills/ai-plan/SKILL.md` for details."
        result = translate_refs(content, "claude")
        # Claude is the canonical form -- unchanged
        assert "`.claude/skills/ai-plan/SKILL.md`" in result

    # spec-201 D-201-04: every non-Claude target resolves skills from
    # the single shared `.agents/skills` tree.
    @pytest.mark.parametrize("target_ide", ["copilot", "cursor", "opencode", "antigravity"])
    def test_translate_skill_path_uses_shared_tree(self, target_ide: str) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Read `.claude/skills/ai-plan/SKILL.md` for details."
        result = translate_refs(content, target_ide)
        assert "`.agents/skills/ai-plan/SKILL.md`" in result

    def test_translate_agent_path_claude(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Delegates to `.claude/agents/ai-build.md`."
        result = translate_refs(content, "claude")
        assert "`.claude/agents/ai-build.md`" in result

    def test_translate_agent_path_copilot(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Delegates to `.claude/agents/ai-build.md`."
        result = translate_refs(content, "copilot")
        assert "`.github/agents/build.agent.md`" in result

    def test_translate_agent_path_opencode(self) -> None:
        # D-201-22: agent trees stay surface-local through the collapse.
        from scripts.sync_command_mirrors import translate_refs

        content = "Delegates to `.claude/agents/ai-build.md`."
        result = translate_refs(content, "opencode")
        assert "`.opencode/agents/ai-build.md`" in result

    def test_specs_not_translated(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "Check `.ai-engineering/specs/_active.md`."
        result = translate_refs(content, "claude")
        assert ".ai-engineering/specs/_active.md" in result

    def test_multiple_references_in_one_line(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "See `.claude/skills/ai-plan/SKILL.md` and `.claude/agents/ai-build.md`."
        result = translate_refs(content, "copilot")
        assert ".agents/skills/ai-plan/SKILL.md" in result
        assert ".github/agents/build.agent.md" in result

    def test_no_translation_for_bare_text(self) -> None:
        from scripts.sync_command_mirrors import translate_refs

        content = "No references here, just plain text."
        result = translate_refs(content, "claude")
        assert result == content


# -- Platform-neutral content --


class TestPlatformNeutralContent:
    """Verify canonical skills avoid Claude Code-specific tool references."""

    _FORBIDDEN_PATTERNS = ("Agent(", "Write tool", "Read tool", "Bash tool", "run_in_background")
    _ALLOWED_EXCEPTIONS: frozenset[str] = frozenset()

    def test_platform_neutral_content(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_SKILLS

        violations: list[str] = []
        for skill_dir in sorted(CLAUDE_SKILLS.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith("ai-"):
                continue
            skill_file = skill_dir / "SKILL.md"
            if not skill_file.is_file():
                continue
            bare_name = skill_dir.name.removeprefix("ai-")
            if bare_name in self._ALLOWED_EXCEPTIONS:
                continue
            content = skill_file.read_text(encoding="utf-8")
            for pattern in self._FORBIDDEN_PATTERNS:
                if pattern in content:
                    violations.append(f"{skill_dir.name}: found '{pattern}'")
        assert not violations, (
            f"Platform-specific patterns found in {len(violations)} skill(s):\n"
            + "\n".join(f"  - {v}" for v in violations)
        )


# -- Handler parity --


class TestHandlerParity:
    """Verify handler mirrors exist for every canonical handler.

    spec-201 D-201-04: the only generated skill tree is ``.agents/skills``
    (``.claude/skills`` is canonical, not a mirror).
    """

    def test_handler_parity(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_SKILLS, discover_handlers

        missing: list[str] = []
        antigravity_skills = _PROJECT_ROOT / ".agents" / "skills"

        for skill_dir in sorted(CLAUDE_SKILLS.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith("ai-"):
                continue
            bare_name = skill_dir.name.removeprefix("ai-")
            handlers = discover_handlers(skill_dir)
            for handler_name, _ in handlers:
                ag_handler = (
                    antigravity_skills / f"ai-{bare_name}" / "handlers" / f"{handler_name}.md"
                )
                if not ag_handler.is_file():
                    missing.append(f".agents/skills/ai-{bare_name}/handlers/{handler_name}.md")
        assert not missing, f"{len(missing)} handler mirror(s) missing:\n" + "\n".join(
            f"  - {m}" for m in missing
        )


class TestReferenceParity:
    """Verify reference mirrors exist for every canonical reference file."""

    def test_reference_parity(self) -> None:
        from scripts.sync_command_mirrors import CLAUDE_SKILLS, discover_reference_files

        missing: list[str] = []
        antigravity_skills = _PROJECT_ROOT / ".agents" / "skills"

        for skill_dir in sorted(CLAUDE_SKILLS.iterdir()):
            if not skill_dir.is_dir() or not skill_dir.name.startswith("ai-"):
                continue
            bare_name = skill_dir.name.removeprefix("ai-")
            references = discover_reference_files(skill_dir)
            for ref_name, _ in references:
                ag_ref = antigravity_skills / f"ai-{bare_name}" / "references" / ref_name
                if not ag_ref.is_file():
                    missing.append(f".agents/skills/ai-{bare_name}/references/{ref_name}")

        assert not missing, f"{len(missing)} reference mirror(s) missing:\n" + "\n".join(
            f"  - {m}" for m in missing
        )
