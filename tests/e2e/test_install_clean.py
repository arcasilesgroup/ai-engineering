"""E2E test: install on a completely empty repository.

Validates that ``ai-eng install`` on a blank directory creates the
full governance framework structure with all expected directories,
state files, and template content.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.installer.service import install
from ai_engineering.state.io import read_json_model, read_ndjson_entries
from ai_engineering.state.models import AuditEntry, InstallManifest


class TestInstallClean:
    """End-to-end tests for installing on an empty repo."""

    def test_install_creates_ai_engineering_dir(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        ai_dir = tmp_path / ".ai-engineering"
        assert ai_dir.is_dir()

    def test_install_creates_required_dirs(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        ai_dir = tmp_path / ".ai-engineering"

        required = [
            "standards",
            "standards/framework",
            "standards/team",
            "context",
            "state",
            "skills",
            "agents",
        ]
        for dirname in required:
            assert (ai_dir / dirname).is_dir(), f"Missing: {dirname}"

    def test_install_creates_state_files(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        state_dir = tmp_path / ".ai-engineering" / "state"

        expected_files = [
            "install-manifest.json",
            "ownership-map.json",
            "decision-store.json",
            "sources.lock.json",
        ]
        for fname in expected_files:
            assert (state_dir / fname).is_file(), f"Missing: {fname}"

    def test_install_manifest_has_correct_stacks(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        manifest_path = tmp_path / ".ai-engineering" / "state" / "install-manifest.json"
        manifest = read_json_model(manifest_path, InstallManifest)
        assert "python" in manifest.installed_stacks
        assert "vscode" in manifest.installed_ides

    def test_install_creates_audit_entry(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        audit_path = tmp_path / ".ai-engineering" / "state" / "audit-log.ndjson"
        entries = read_ndjson_entries(audit_path, AuditEntry)
        assert len(entries) >= 1
        assert any(e.event == "install" for e in entries)

    def test_install_creates_project_templates(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        assert (tmp_path / "CLAUDE.md").is_file()

    def test_install_creates_governance_content(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        ai_dir = tmp_path / ".ai-engineering"

        # Should have the manifest template
        assert (ai_dir / "manifest.yml").is_file()

        # Should have framework standards
        assert (ai_dir / "standards" / "framework" / "core.md").is_file()

    def test_install_result_counts(
        self,
        tmp_path: Path,
    ) -> None:
        result = install(tmp_path, stacks=["python"], ides=["vscode"])
        assert result.total_created > 0
        assert result.total_skipped == 0
        assert not result.already_installed

    def test_install_idempotent(self, tmp_path: Path) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        second = install(tmp_path, stacks=["python"], ides=["vscode"])

        assert second.already_installed is True
        # Second install should skip all governance and project files
        assert len(second.governance_files.created) == 0
        assert len(second.project_files.created) == 0

    def test_state_files_are_valid_json(
        self,
        tmp_path: Path,
    ) -> None:
        install(tmp_path, stacks=["python"], ides=["vscode"])
        state_dir = tmp_path / ".ai-engineering" / "state"

        for f in state_dir.glob("*.json"):
            content = f.read_text(encoding="utf-8")
            data = json.loads(content)
            assert isinstance(data, dict), f"{f.name} is not a JSON object"
