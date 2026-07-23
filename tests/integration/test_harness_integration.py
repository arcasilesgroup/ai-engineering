"""Integration tests for context safety harness (spec-194 T-9).

Tests determinism, compare diffs, and budget regressions.
"""

from __future__ import annotations

import json

from ai_engineering.harness.adapters.claude import ClaudeAdapter
from ai_engineering.harness.schema import ContextSafetyReport


class TestHarnessDeterminism:
    """Same inputs produce byte-identical JSON."""

    def test_deterministic_output(self):
        adapter = ClaudeAdapter()
        report1 = adapter.collect(fixture_name="determinism-test")
        report2 = adapter.collect(fixture_name="determinism-test")
        assert report1.to_json() == report2.to_json()

    def test_sorted_keys(self):
        adapter = ClaudeAdapter()
        report = adapter.collect()
        json_str = report.to_json()
        parsed = json.loads(json_str)
        keys = list(parsed.keys())
        assert keys == sorted(keys)


class TestHarnessCompare:
    """Compare reports shows diffs."""

    def test_no_diff_on_same_report(self):
        adapter = ClaudeAdapter()
        report = adapter.collect()
        # Compare with itself
        json_str = report.to_json()
        restored = ContextSafetyReport.from_json(json_str)
        assert report.to_json() == restored.to_json()

    def test_diff_detected(self):
        from ai_engineering.harness.schema import (
            SCHEMA_VERSION,
            CatalogMetrics,
            HookMetrics,
            McpResidue,
            OutputBounds,
            RootMetrics,
        )

        report1 = ContextSafetyReport(
            schema_version=SCHEMA_VERSION,
            host="test",
            fixture="test",
            root=RootMetrics(bytes=100, estimated_tokens=50, mandatory_reads=0, source_path="x"),
            catalog=CatalogMetrics(unique_ids=10, duplicate_ids=0, total_skills=10),
            hooks=HookMetrics(injection_count=0, additional_context_tokens=0, automatic_writes=0),
            mcp_residue=McpResidue(
                reachable_registrations=0, plugins=0, permissions=0, operational_instructions=0
            ),
            output_bounds=OutputBounds(),
            verdict="pass",
        )
        report2 = ContextSafetyReport(
            schema_version=SCHEMA_VERSION,
            host="test",
            fixture="test",
            root=RootMetrics(bytes=200, estimated_tokens=100, mandatory_reads=1, source_path="x"),
            catalog=CatalogMetrics(unique_ids=10, duplicate_ids=1, total_skills=11),
            hooks=HookMetrics(injection_count=2, additional_context_tokens=0, automatic_writes=0),
            mcp_residue=McpResidue(
                reachable_registrations=0, plugins=0, permissions=0, operational_instructions=0
            ),
            output_bounds=OutputBounds(),
            verdict="fail",
        )
        # They should differ
        assert report1.to_json() != report2.to_json()


class TestHarnessBudgetRegression:
    """Budget regression detection."""

    def test_root_budget_enforcement(self):
        adapter = ClaudeAdapter()
        report = adapter.collect()
        # Current repo root is way over 2 KiB - this should fail
        if report.root.bytes > 2048:
            assert report.verdict == "fail"

    def test_output_caps(self):
        adapter = ClaudeAdapter()
        report = adapter.collect()
        assert report.output_bounds.normal_cap == 8192
        assert report.output_bounds.lines_cap == 200
