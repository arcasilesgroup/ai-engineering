"""Tests for context safety harness schema (spec-194 T-2).

TDD RED phase: these tests define the contract before implementation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ai_engineering.harness.collector import (
    collect_catalog_metrics,
    collect_root_metrics,
)
from ai_engineering.harness.redactor import (
    contains_secrets,
    redact_json,
    redact_string,
)
from ai_engineering.harness.schema import (
    SCHEMA_VERSION,
    CatalogMetrics,
    ContextSafetyReport,
    HookMetrics,
    McpResidue,
    OutputBounds,
    RootMetrics,
)


class TestRootMetrics:
    """RootMetrics dataclass tests."""

    def test_create_root_metrics(self):
        rm = RootMetrics(
            bytes=1024, estimated_tokens=500, mandatory_reads=2, source_path="AGENTS.md"
        )
        assert rm.bytes == 1024
        assert rm.estimated_tokens == 500
        assert rm.mandatory_reads == 2
        assert rm.source_path == "AGENTS.md"

    def test_root_metrics_frozen(self):
        rm = RootMetrics(bytes=1024, estimated_tokens=500, mandatory_reads=0, source_path="x")
        with pytest.raises(AttributeError):
            rm.bytes = 2048  # type: ignore[misc]


class TestCatalogMetrics:
    """CatalogMetrics dataclass tests."""

    def test_create_catalog_metrics(self):
        cm = CatalogMetrics(
            unique_ids=10, duplicate_ids=2, total_skills=12, duplicate_ids_list=["a", "b"]
        )
        assert cm.unique_ids == 10
        assert cm.duplicate_ids == 2
        assert cm.duplicate_ids_list == ["a", "b"]

    def test_default_empty_list(self):
        cm = CatalogMetrics(unique_ids=0, duplicate_ids=0, total_skills=0)
        assert cm.duplicate_ids_list == []


class TestContextSafetyReport:
    """ContextSafetyReport serialization tests."""

    def _make_report(self) -> ContextSafetyReport:
        return ContextSafetyReport(
            schema_version=SCHEMA_VERSION,
            host="test",
            fixture="test-fixture",
            root=RootMetrics(
                bytes=1024, estimated_tokens=500, mandatory_reads=0, source_path="AGENTS.md"
            ),
            catalog=CatalogMetrics(unique_ids=10, duplicate_ids=0, total_skills=10),
            hooks=HookMetrics(injection_count=0, additional_context_tokens=0, automatic_writes=0),
            mcp_residue=McpResidue(
                reachable_registrations=0, plugins=0, permissions=0, operational_instructions=0
            ),
            output_bounds=OutputBounds(),
            verdict="pass",
        )

    def test_to_json_roundtrip(self):
        report = self._make_report()
        json_str = report.to_json()
        restored = ContextSafetyReport.from_json(json_str)
        assert restored == report

    def test_json_is_sorted_keys(self):
        report = self._make_report()
        json_str = report.to_json()
        parsed = json.loads(json_str)
        keys = list(parsed.keys())
        assert keys == sorted(keys)

    def test_from_json_string(self):
        report = self._make_report()
        json_str = report.to_json()
        restored = ContextSafetyReport.from_json(json_str)
        assert restored.host == "test"
        assert restored.verdict == "pass"

    def test_from_dict(self):
        report = self._make_report()
        data = json.loads(report.to_json())
        restored = ContextSafetyReport.from_json(data)
        assert restored == report

    def test_truncate_to_budget(self):
        report = self._make_report()
        truncated = report.truncate_to_budget(max_bytes=200)
        assert len(truncated.encode("utf-8")) <= 200
        # Should still be valid JSON
        parsed = json.loads(truncated)
        assert "truncated" in parsed


class TestCollectorRootMetrics:
    """Root metrics collector tests."""

    def test_collect_nonexistent_file(self, tmp_path: Path):
        rm = collect_root_metrics(tmp_path / "nonexistent.md")
        assert rm.bytes == 0
        assert rm.estimated_tokens == 0
        assert rm.mandatory_reads == 0

    def test_collect_empty_file(self, tmp_path: Path):
        root = tmp_path / "AGENTS.md"
        root.write_text("")
        rm = collect_root_metrics(root)
        assert rm.bytes == 0
        assert rm.estimated_tokens == 0
        assert rm.mandatory_reads == 0

    def test_collect_with_mandatory_reads(self, tmp_path: Path):
        root = tmp_path / "AGENTS.md"
        root.write_text("# Rules\n\nRead every session this document.\nMust read before coding.\n")
        rm = collect_root_metrics(root)
        assert rm.mandatory_reads >= 2

    def test_collect_token_estimate(self, tmp_path: Path):
        root = tmp_path / "AGENTS.md"
        root.write_text("one two three four five")
        rm = collect_root_metrics(root)
        # 5 words * 4/3 ≈ 6.67 → 6 tokens
        assert rm.estimated_tokens >= 5


class TestCollectorCatalogMetrics:
    """Catalog metrics collector tests."""

    def test_collect_empty_dir(self, tmp_path: Path):
        cm = collect_catalog_metrics(tmp_path / "nonexistent")
        assert cm.unique_ids == 0
        assert cm.total_skills == 0

    def test_collect_with_skills(self, tmp_path: Path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        (skills_dir / "ai-test").mkdir()
        (skills_dir / "ai-test" / "SKILL.md").write_text("# Test")
        (skills_dir / "ai-build").mkdir()
        (skills_dir / "ai-build" / "SKILL.md").write_text("# Build")
        cm = collect_catalog_metrics(skills_dir)
        assert cm.unique_ids == 2
        assert cm.total_skills == 2
        assert cm.duplicate_ids == 0


class TestRedactor:
    """Redaction engine tests."""

    def test_redact_api_key(self):
        text = 'api_key = "sk-1234567890abcdef1234567890abcdef"'
        redacted = redact_string(text)
        assert "1234567890abcdef" not in redacted
        assert "REDACTED" in redacted

    def test_redact_home_path(self):
        text = "Config at /Users/john/.config/app"
        redacted = redact_string(text)
        assert "/Users/john" not in redacted

    def test_contains_secrets(self):
        assert contains_secrets('secret = "abcdef1234567890abcdef1234567890"')
        assert not contains_secrets("no secrets here")

    def test_redact_json(self):
        data = {"key": "sk-1234567890abcdef1234567890abcdef", "safe": "hello"}
        redacted = redact_json(json.dumps(data))
        parsed = json.loads(redacted)
        assert "REDACTED" in parsed["key"]
        assert parsed["safe"] == "hello"
