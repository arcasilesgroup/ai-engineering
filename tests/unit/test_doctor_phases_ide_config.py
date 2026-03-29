"""Unit tests for doctor/phases/ide_config.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.config.manifest import AiProvidersConfig, ManifestConfig, ProvidersConfig
from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.doctor.phases import ide_config

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def claude_project(tmp_path: Path) -> Path:
    """Create a project with claude_code provider templates deployed."""
    # CLAUDE.md (provider file)
    (tmp_path / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
    # .claude/ directory (provider tree)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "settings.json").write_text(
        json.dumps({"permissions": {"deny": ["rm -rf"]}}),
        encoding="utf-8",
    )
    # Common files
    (tmp_path / ".gitleaks.toml").write_text("", encoding="utf-8")
    (tmp_path / ".semgrep.yml").write_text("", encoding="utf-8")
    return tmp_path


@pytest.fixture()
def claude_manifest() -> ManifestConfig:
    """ManifestConfig with claude_code as the only AI provider."""
    return ManifestConfig(
        providers=ProvidersConfig(vcs="github", ides=["claude_code"]),
        ai_providers=AiProvidersConfig(enabled=["claude_code"], primary="claude_code"),
    )


@pytest.fixture()
def copilot_manifest() -> ManifestConfig:
    """ManifestConfig with github_copilot as the only AI provider."""
    return ManifestConfig(
        providers=ProvidersConfig(vcs="github", ides=["github_copilot"]),
        ai_providers=AiProvidersConfig(enabled=["github_copilot"], primary="github_copilot"),
    )


@pytest.fixture()
def no_ide_manifest() -> ManifestConfig:
    """ManifestConfig with no AI providers."""
    return ManifestConfig(
        providers=ProvidersConfig(vcs="github", ides=[]),
        ai_providers=AiProvidersConfig(enabled=[], primary=""),
    )


# ---------------------------------------------------------------------------
# check() -- provider-templates
# ---------------------------------------------------------------------------


class TestProviderTemplates:
    def test_ok_when_all_present(self, claude_project: Path, claude_manifest: ManifestConfig):
        ctx = DoctorContext(target=claude_project, manifest_config=claude_manifest)
        results = ide_config.check(ctx)
        tmpl_check = next(r for r in results if r.name == "provider-templates")
        assert tmpl_check.status == CheckStatus.OK

    def test_fail_when_no_manifest(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path, manifest_config=None)
        results = ide_config.check(ctx)
        tmpl_check = next(r for r in results if r.name == "provider-templates")
        assert tmpl_check.status == CheckStatus.FAIL
        assert "No manifest" in tmpl_check.message

    def test_ok_when_no_ides_configured(self, tmp_path: Path, no_ide_manifest: ManifestConfig):
        ctx = DoctorContext(target=tmp_path, manifest_config=no_ide_manifest)
        results = ide_config.check(ctx)
        tmpl_check = next(r for r in results if r.name == "provider-templates")
        assert tmpl_check.status == CheckStatus.OK

    def test_fail_when_claude_md_missing(self, tmp_path: Path, claude_manifest: ManifestConfig):
        # Create .claude dir and common files but not CLAUDE.md
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".gitleaks.toml").write_text("", encoding="utf-8")
        (tmp_path / ".semgrep.yml").write_text("", encoding="utf-8")
        ctx = DoctorContext(target=tmp_path, manifest_config=claude_manifest)
        results = ide_config.check(ctx)
        tmpl_check = next(r for r in results if r.name == "provider-templates")
        assert tmpl_check.status == CheckStatus.FAIL
        assert "CLAUDE.md" in tmpl_check.message

    def test_fail_when_claude_dir_missing(self, tmp_path: Path, claude_manifest: ManifestConfig):
        # Create CLAUDE.md and common files but not .claude/ dir
        (tmp_path / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
        (tmp_path / ".gitleaks.toml").write_text("", encoding="utf-8")
        (tmp_path / ".semgrep.yml").write_text("", encoding="utf-8")
        ctx = DoctorContext(target=tmp_path, manifest_config=claude_manifest)
        results = ide_config.check(ctx)
        tmpl_check = next(r for r in results if r.name == "provider-templates")
        assert tmpl_check.status == CheckStatus.FAIL
        assert ".claude" in tmpl_check.message

    def test_fail_when_copilot_files_missing(
        self, tmp_path: Path, copilot_manifest: ManifestConfig
    ):
        # Only create common files, no copilot-specific ones
        (tmp_path / ".gitleaks.toml").write_text("", encoding="utf-8")
        (tmp_path / ".semgrep.yml").write_text("", encoding="utf-8")
        ctx = DoctorContext(target=tmp_path, manifest_config=copilot_manifest)
        results = ide_config.check(ctx)
        tmpl_check = next(r for r in results if r.name == "provider-templates")
        assert tmpl_check.status == CheckStatus.FAIL

    def test_ok_when_copilot_files_present(self, tmp_path: Path, copilot_manifest: ManifestConfig):
        (tmp_path / "AGENTS.md").write_text("# Agents\n", encoding="utf-8")
        (tmp_path / ".gitleaks.toml").write_text("", encoding="utf-8")
        (tmp_path / ".semgrep.yml").write_text("", encoding="utf-8")
        github_dir = tmp_path / ".github"
        (github_dir / "copilot-instructions.md").parent.mkdir(parents=True, exist_ok=True)
        (github_dir / "copilot-instructions.md").write_text("# Copilot\n", encoding="utf-8")
        (github_dir / "skills").mkdir(parents=True, exist_ok=True)
        (github_dir / "hooks").mkdir(parents=True, exist_ok=True)
        (github_dir / "agents").mkdir(parents=True, exist_ok=True)
        (github_dir / "instructions").mkdir(parents=True, exist_ok=True)

        ctx = DoctorContext(target=tmp_path, manifest_config=copilot_manifest)
        results = ide_config.check(ctx)
        tmpl_check = next(r for r in results if r.name == "provider-templates")
        assert tmpl_check.status == CheckStatus.OK

    def test_fail_when_common_files_missing(self, tmp_path: Path, claude_manifest: ManifestConfig):
        # Create provider-specific but not common files
        (tmp_path / "CLAUDE.md").write_text("# Claude\n", encoding="utf-8")
        (tmp_path / ".claude").mkdir()
        ctx = DoctorContext(target=tmp_path, manifest_config=claude_manifest)
        results = ide_config.check(ctx)
        tmpl_check = next(r for r in results if r.name == "provider-templates")
        assert tmpl_check.status == CheckStatus.FAIL
        assert ".gitleaks.toml" in tmpl_check.message or ".semgrep.yml" in tmpl_check.message


# ---------------------------------------------------------------------------
# check() -- settings-merge
# ---------------------------------------------------------------------------


class TestSettingsMerge:
    def test_ok_with_deny_rules(self, claude_project: Path, claude_manifest: ManifestConfig):
        ctx = DoctorContext(target=claude_project, manifest_config=claude_manifest)
        results = ide_config.check(ctx)
        settings_check = next(r for r in results if r.name == "settings-merge")
        assert settings_check.status == CheckStatus.OK

    def test_ok_when_no_manifest(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path, manifest_config=None)
        results = ide_config.check(ctx)
        settings_check = next(r for r in results if r.name == "settings-merge")
        assert settings_check.status == CheckStatus.OK

    def test_ok_when_not_claude_code(self, tmp_path: Path, copilot_manifest: ManifestConfig):
        ctx = DoctorContext(target=tmp_path, manifest_config=copilot_manifest)
        results = ide_config.check(ctx)
        settings_check = next(r for r in results if r.name == "settings-merge")
        assert settings_check.status == CheckStatus.OK

    def test_warn_when_settings_missing(self, tmp_path: Path, claude_manifest: ManifestConfig):
        ctx = DoctorContext(target=tmp_path, manifest_config=claude_manifest)
        results = ide_config.check(ctx)
        settings_check = next(r for r in results if r.name == "settings-merge")
        assert settings_check.status == CheckStatus.WARN
        assert "not found" in settings_check.message

    def test_fail_when_no_deny(self, tmp_path: Path, claude_manifest: ManifestConfig):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text(
            json.dumps({"permissions": {"allow": ["ls"]}}),
            encoding="utf-8",
        )
        ctx = DoctorContext(target=tmp_path, manifest_config=claude_manifest)
        results = ide_config.check(ctx)
        settings_check = next(r for r in results if r.name == "settings-merge")
        assert settings_check.status == CheckStatus.FAIL
        assert "deny" in settings_check.message

    def test_fail_when_no_permissions_key(self, tmp_path: Path, claude_manifest: ManifestConfig):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text(
            json.dumps({"other": "data"}),
            encoding="utf-8",
        )
        ctx = DoctorContext(target=tmp_path, manifest_config=claude_manifest)
        results = ide_config.check(ctx)
        settings_check = next(r for r in results if r.name == "settings-merge")
        assert settings_check.status == CheckStatus.FAIL
        assert "deny" in settings_check.message

    def test_fail_when_invalid_json(self, tmp_path: Path, claude_manifest: ManifestConfig):
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "settings.json").write_text("not json", encoding="utf-8")
        ctx = DoctorContext(target=tmp_path, manifest_config=claude_manifest)
        results = ide_config.check(ctx)
        settings_check = next(r for r in results if r.name == "settings-merge")
        assert settings_check.status == CheckStatus.FAIL
        assert "not parseable" in settings_check.message


# ---------------------------------------------------------------------------
# fix() -- returns failed unchanged
# ---------------------------------------------------------------------------


class TestIdeConfigFix:
    def test_returns_failed_unchanged(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="provider-templates",
                status=CheckStatus.FAIL,
                message="missing templates",
            ),
            CheckResult(
                name="settings-merge",
                status=CheckStatus.FAIL,
                message="no deny rules",
            ),
        ]
        result = ide_config.fix(ctx, failed)
        assert len(result) == 2
        assert all(r.status == CheckStatus.FAIL for r in result)

    def test_returns_new_list_not_same_reference(self, tmp_path: Path):
        ctx = DoctorContext(target=tmp_path)
        failed = [
            CheckResult(
                name="provider-templates",
                status=CheckStatus.FAIL,
                message="missing",
            )
        ]
        result = ide_config.fix(ctx, failed)
        assert result is not failed


# ---------------------------------------------------------------------------
# check() returns exactly 2 results
# ---------------------------------------------------------------------------


class TestCheckReturnsAllResults:
    def test_check_returns_two_results(self, claude_project: Path, claude_manifest: ManifestConfig):
        ctx = DoctorContext(target=claude_project, manifest_config=claude_manifest)
        results = ide_config.check(ctx)
        assert len(results) == 2
        names = {r.name for r in results}
        assert names == {"provider-templates", "settings-merge"}
