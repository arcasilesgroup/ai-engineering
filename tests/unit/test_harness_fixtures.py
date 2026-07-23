"""Fixture tests for harness adapters (spec-194 T-6).

Each enabled host has a fixture result or UNVERIFIED; no inferred pass.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.harness.adapters.antigravity import AntigravityAdapter
from ai_engineering.harness.adapters.claude import ClaudeAdapter
from ai_engineering.harness.adapters.codex import CodexAdapter
from ai_engineering.harness.adapters.opencode import OpenCodeAdapter

FIXTURES_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "harness"


class TestClaudeFixture:
    """Claude Code fixture tests."""

    def _make_adapter(self) -> ClaudeAdapter:
        adapter = ClaudeAdapter()
        adapter._override_root_paths = [FIXTURES_DIR / "claude" / "AGENTS.md"]
        adapter._override_skills_dir = FIXTURES_DIR / "claude" / "skills"
        return adapter

    def test_fixture_collects(self):
        adapter = self._make_adapter()
        report = adapter.collect(fixture_name="claude-fixture")
        assert report.host == "claude-code"
        assert report.fixture == "claude-fixture"
        assert report.schema_version == "1.0.0"

    def test_fixture_root_under_budget(self):
        adapter = self._make_adapter()
        report = adapter.collect(fixture_name="claude-fixture")
        assert report.root.bytes <= 2048

    def test_fixture_no_duplicates(self):
        adapter = self._make_adapter()
        report = adapter.collect(fixture_name="claude-fixture")
        assert report.catalog.duplicate_ids == 0


class TestCodexFixture:
    """Codex fixture tests."""

    def test_fixture_collects(self):
        adapter = CodexAdapter()
        adapter._override_root_paths = [FIXTURES_DIR / "codex" / "AGENTS.md"]
        adapter._override_skills_dir = FIXTURES_DIR / "codex"
        report = adapter.collect(fixture_name="codex-fixture")
        assert report.host == "codex"


class TestOpenCodeFixture:
    """OpenCode fixture tests."""

    def test_fixture_collects(self):
        adapter = OpenCodeAdapter()
        adapter._override_root_paths = [FIXTURES_DIR / "opencode" / "AGENTS.md"]
        adapter._override_skills_dir = FIXTURES_DIR / "opencode"
        report = adapter.collect(fixture_name="opencode-fixture")
        assert report.host == "opencode"


class TestAntigravityFixture:
    """Antigravity fixture tests."""

    def test_unverified_verdict(self):
        adapter = AntigravityAdapter()
        report = adapter.collect(fixture_name="antigravity-fixture")
        assert report.verdict == "UNVERIFIED"
