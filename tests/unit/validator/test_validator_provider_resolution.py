"""Tests for manifest-driven provider resolution in the validator.

These tests verify that instruction file lists, path patterns, and mirror
sync checks are derived from ``ai_providers.enabled`` in manifest.yml
rather than being hardcoded.

RED phase: all tests target functionality that does not yet exist and MUST
fail against the current codebase.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.validator._shared import (
    _PATH_REF_PATTERN,
    IntegrityReport,
    IntegrityStatus,
    _instruction_files,
)
from ai_engineering.validator.categories.mirror_sync import (
    _check_instruction_parity,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MANIFEST_TEMPLATE = """\
name: test-project
version: 1.0.0
ai_providers:
  enabled: [{providers}]
  primary: {primary}
"""

_ROOT_ENTRY_POINTS_MANIFEST_TEMPLATE = """\
name: test-project
version: 1.0.0
ai_providers:
    enabled: [{providers}]
    primary: {primary}
ownership:
    root_entry_points:
        "AGENTS.md":
            owner: framework
            canonical_source: scripts/sync_command_mirrors.py:generate_agents_md
            runtime_role: shared-runtime-contract
            sync:
                mode: generate
                template_path: {agents_template_path}
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


def _write_manifest(ai: Path, providers: list[str]) -> None:
    """Write a manifest.yml with the given AI providers."""
    primary = providers[0] if providers else "claude_code"
    content = _MANIFEST_TEMPLATE.format(
        providers=", ".join(providers),
        primary=primary,
    )
    manifest = ai / "manifest.yml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(content, encoding="utf-8")


def _write_manifest_with_root_entry_points(
    ai: Path,
    providers: list[str],
    *,
    agents_template_path: str,
) -> None:
    """Write a manifest.yml that declares root entry point sync metadata."""
    primary = providers[0] if providers else "claude_code"
    content = _ROOT_ENTRY_POINTS_MANIFEST_TEMPLATE.format(
        providers=", ".join(providers),
        primary=primary,
        agents_template_path=agents_template_path,
    )
    manifest = ai / "manifest.yml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(content, encoding="utf-8")


def _make_governance(root: Path) -> Path:
    """Create a minimal .ai-engineering governance tree."""
    ai = root / ".ai-engineering"
    for d in [
        "contexts/languages",
        "contexts/frameworks",
        "contexts/team",
        "specs",
        "state",
    ]:
        (ai / d).mkdir(parents=True, exist_ok=True)
    return ai


# ---------------------------------------------------------------------------
# T10: instruction files — claude_code only
# ---------------------------------------------------------------------------


class TestInstructionFilesClaudeOnly:
    """With only claude_code enabled, only CLAUDE.md paths are returned."""

    def test_instruction_files_claude_only(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_manifest(ai, ["claude_code"])

        files = _instruction_files(tmp_path)

        # Must include CLAUDE.md
        assert any("CLAUDE.md" in f for f in files)
        # Must NOT include AGENTS.md or copilot-instructions.md
        assert not any("AGENTS.md" in f for f in files), (
            "_instruction_files should not return AGENTS.md "
            "when github_copilot is not in ai_providers.enabled"
        )
        assert not any("copilot-instructions" in f for f in files), (
            "_instruction_files should not return copilot-instructions.md "
            "when github_copilot is not in ai_providers.enabled"
        )


# ---------------------------------------------------------------------------
# T11: instruction files — claude_code + github_copilot
# ---------------------------------------------------------------------------


class TestInstructionFilesClaudeCopilot:
    """With claude_code and github_copilot enabled, all three file types appear."""

    def test_instruction_files_claude_copilot(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_manifest(ai, ["claude_code", "github_copilot"])

        files = _instruction_files(tmp_path)

        assert any("CLAUDE.md" in f for f in files), (
            "CLAUDE.md must be present when claude_code is enabled"
        )
        assert any("AGENTS.md" in f for f in files), (
            "AGENTS.md must be present when github_copilot is enabled"
        )
        assert any("copilot-instructions" in f for f in files), (
            "copilot-instructions.md must be present when github_copilot is enabled"
        )

    def test_instruction_files_copilot_only_excludes_claude(self, tmp_path: Path) -> None:
        """When only github_copilot is enabled, CLAUDE.md must NOT appear."""
        ai = _make_governance(tmp_path)
        _write_manifest(ai, ["github_copilot"])

        files = _instruction_files(tmp_path)

        assert any("AGENTS.md" in f for f in files), (
            "AGENTS.md must be present when github_copilot is enabled"
        )
        assert not any("CLAUDE.md" in f for f in files), (
            "_instruction_files must not return CLAUDE.md "
            "when claude_code is not in ai_providers.enabled"
        )


class TestInstructionFilesRootEntryPointMetadata:
    """Source-repo template counterparts should come from manifest metadata."""

    def test_instruction_files_uses_manifest_declared_template_path(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        custom_template_path = "src/ai_engineering/templates/project/custom/AGENTS.custom.md"
        _write_manifest_with_root_entry_points(
            ai,
            ["github_copilot"],
            agents_template_path=custom_template_path,
        )
        (tmp_path / "src" / "ai_engineering" / "templates").mkdir(parents=True, exist_ok=True)

        files = _instruction_files(tmp_path)

        assert "AGENTS.md" in files
        assert ".github/copilot-instructions.md" in files
        assert custom_template_path in files, (
            "_instruction_files should include the manifest-declared template_path "
            "for AGENTS.md in a source-repo layout"
        )
        assert "src/ai_engineering/templates/project/AGENTS.md" not in files, (
            "_instruction_files should not derive the AGENTS.md template counterpart "
            "from the hardcoded default map when the manifest declares a custom template_path"
        )


# ---------------------------------------------------------------------------
# T12: validator errors on missing instruction file with remediation
# ---------------------------------------------------------------------------


class TestValidatorErrorOnMissingInstructionFile:
    """Missing instruction file for an enabled provider produces an error
    with actionable remediation."""

    def test_validator_errors_on_missing_instruction_file(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_manifest(ai, ["claude_code"])
        # Deliberately do NOT create CLAUDE.md on disk.

        report = IntegrityReport()
        # Import the counter accuracy checker which iterates _instruction_files
        from ai_engineering.validator.categories.counter_accuracy import (
            _check_counter_accuracy,
        )

        _check_counter_accuracy(tmp_path, report)

        fail_checks = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL and "CLAUDE.md" in c.message
        ]
        assert len(fail_checks) >= 1, "Expected at least one FAIL check for missing CLAUDE.md"
        # The error message must contain a remediation hint
        remediation_found = any("ai-eng update" in c.message for c in fail_checks)
        assert remediation_found, (
            "Missing instruction file error must include 'ai-eng update' "
            "remediation hint in the message"
        )


# ---------------------------------------------------------------------------
# T13: no error for disabled provider
# ---------------------------------------------------------------------------


class TestValidatorNoErrorForDisabledProvider:
    """When a provider is not in ai_providers.enabled, its missing instruction
    files must not produce errors."""

    def test_validator_no_error_for_disabled_provider(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_manifest(ai, ["claude_code"])
        # Create CLAUDE.md so the enabled provider passes
        (tmp_path / "CLAUDE.md").write_text("# Instructions\n", encoding="utf-8")
        # Deliberately do NOT create AGENTS.md or copilot-instructions.md

        files = _instruction_files(tmp_path)

        # Disabled provider files must not appear in the list
        assert not any("AGENTS.md" in f for f in files), (
            "AGENTS.md should not be in instruction files when github_copilot is disabled"
        )
        assert not any("copilot-instructions" in f for f in files), (
            "copilot-instructions.md should not be in instruction files "
            "when github_copilot is disabled"
        )

        # Also verify that the validator does not report errors for them
        report = IntegrityReport()
        from ai_engineering.validator.categories.counter_accuracy import (
            _check_counter_accuracy,
        )

        _check_counter_accuracy(tmp_path, report)

        # No FAIL checks should reference AGENTS.md or copilot-instructions.md
        unexpected_fails = [
            c
            for c in report.checks
            if c.status == IntegrityStatus.FAIL
            and ("AGENTS.md" in c.message or "copilot-instructions" in c.message)
        ]
        assert unexpected_fails == [], (
            f"Validator should not report errors for disabled providers, "
            f"but found: {[c.message for c in unexpected_fails]}"
        )


# ---------------------------------------------------------------------------
# T14: _PATH_REF_PATTERN — contexts/ yes, context/ no
# ---------------------------------------------------------------------------


class TestPathRefPattern:
    """_PATH_REF_PATTERN must match ``contexts/`` but reject ``context/``."""

    def test_matches_contexts_path(self) -> None:
        text = "`contexts/team/foo.md`"
        match = _PATH_REF_PATTERN.search(text)
        assert match is not None, "_PATH_REF_PATTERN must match 'contexts/team/foo.md'"

    def test_rejects_obsolete_context_path(self) -> None:
        text = "`context/team/foo.md`"
        match = _PATH_REF_PATTERN.search(text)
        assert match is None, (
            "_PATH_REF_PATTERN must NOT match obsolete 'context/team/foo.md' "
            "(only 'contexts/' is valid)"
        )


# ---------------------------------------------------------------------------
# T15: mirror_sync parity checks only enabled providers
# ---------------------------------------------------------------------------


class TestMirrorSyncEnabledProviders:
    """_check_instruction_parity should only validate files for providers
    listed in ai_providers.enabled."""

    def test_mirror_sync_checks_only_enabled_providers(self, tmp_path: Path) -> None:
        ai = _make_governance(tmp_path)
        _write_manifest(ai, ["claude_code"])

        # Create CLAUDE.md with required sections
        claude_content = "# Instructions\n\n## Skills\n\n- skill1\n\n## Agents\n\n- agent1\n\n"
        (tmp_path / "CLAUDE.md").write_text(claude_content, encoding="utf-8")

        # Do NOT create AGENTS.md — github_copilot is disabled, so
        # parity check must not require AGENTS.md.
        report = IntegrityReport()
        _check_instruction_parity(tmp_path, report)

        # There should be no warning/failure about AGENTS.md being missing
        agents_checks = [
            c
            for c in report.checks
            if "AGENTS.md" in c.message and c.status in (IntegrityStatus.FAIL, IntegrityStatus.WARN)
        ]
        assert agents_checks == [], (
            "mirror_sync parity should not check AGENTS.md when "
            "github_copilot is not enabled, but found: "
            f"{[c.message for c in agents_checks]}"
        )
