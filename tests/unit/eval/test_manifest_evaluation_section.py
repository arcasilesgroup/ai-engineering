"""spec-119 T-1.8 -- manifest.yml `evaluation:` section (D-119-04) conformance."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.eval


@pytest.fixture()
def manifest(repo_root: Path) -> dict:
    return yaml.safe_load(
        (repo_root / ".ai-engineering" / "manifest.yml").read_text(encoding="utf-8")
    )


@pytest.fixture()
def manifest_schema(repo_root: Path) -> dict:
    return json.loads(
        (repo_root / ".ai-engineering" / "schemas" / "manifest.schema.json").read_text(
            encoding="utf-8"
        )
    )


class TestManifestEvaluationSection:
    def test_section_present(self, manifest: dict):
        assert "evaluation" in manifest, "spec-119 D-119-04 requires evaluation section"

    def test_pass_at_k_threshold_and_k(self, manifest: dict):
        ev = manifest["evaluation"]
        assert isinstance(ev["pass_at_k"]["k"], int)
        assert ev["pass_at_k"]["k"] >= 1
        threshold = ev["pass_at_k"]["threshold"]
        assert 0 <= threshold <= 1

    def test_hallucination_rate_max_in_unit_interval(self, manifest: dict):
        max_rate = manifest["evaluation"]["hallucination_rate"]["max"]
        assert 0 <= max_rate <= 1

    def test_regression_tolerance_in_unit_interval(self, manifest: dict):
        tol = manifest["evaluation"]["regression_tolerance"]
        assert 0 <= tol <= 1

    def test_scenario_packs_is_list_of_strings(self, manifest: dict):
        packs = manifest["evaluation"]["scenario_packs"]
        assert isinstance(packs, list)
        assert all(isinstance(p, str) and p for p in packs)

    def test_enforcement_enum(self, manifest: dict):
        assert manifest["evaluation"]["enforcement"] in {"blocking", "advisory"}


class TestManifestSchemaCoverage:
    """Schema validates that the `evaluation:` block matches the section
    declared in spec-119 D-119-04."""

    def test_schema_declares_evaluation_section(self, manifest_schema: dict):
        assert "evaluation" in manifest_schema["properties"]

    def test_evaluation_section_has_required_fields(self, manifest_schema: dict):
        ev = manifest_schema["properties"]["evaluation"]
        assert set(ev["required"]) == {
            "pass_at_k",
            "hallucination_rate",
            "regression_tolerance",
            "scenario_packs",
            "enforcement",
        }

    def test_enforcement_enum_in_schema(self, manifest_schema: dict):
        ev = manifest_schema["properties"]["evaluation"]
        assert set(ev["properties"]["enforcement"]["enum"]) == {"blocking", "advisory"}


class TestEvalRunInAuditSchema:
    """The audit-event schema declares the eval_run discriminated branch."""

    @pytest.fixture()
    def audit_schema(self, repo_root: Path) -> dict:
        return json.loads(
            (repo_root / ".ai-engineering" / "schemas" / "audit-event.schema.json").read_text(
                encoding="utf-8"
            )
        )

    def test_detail_eval_run_defs_present(self, audit_schema: dict):
        assert "detail_eval_run" in audit_schema["$defs"]

    def test_eight_operations_enumerated(self, audit_schema: dict):
        ops = audit_schema["$defs"]["detail_eval_run"]["properties"]["operation"]["enum"]
        assert set(ops) == {
            "eval_started",
            "scenario_executed",
            "pass_at_k_computed",
            "hallucination_rate_computed",
            "regression_detected",
            "regression_cleared",
            "eval_gated",
            "baseline_updated",
        }

    def test_verdict_enum_present(self, audit_schema: dict):
        verdict_enum = audit_schema["$defs"]["detail_eval_run"]["properties"]["verdict"]["enum"]
        assert set(verdict_enum) == {"GO", "CONDITIONAL", "NO_GO", "SKIPPED"}

    def test_eval_run_branch_in_allOf(self, audit_schema: dict):
        branches = audit_schema["allOf"]
        assert any(b["if"]["properties"]["event"].get("const") == "eval_run" for b in branches)


class TestEvalRunInPythonValidator:
    """The Python state.event_schema validator accepts eval_run."""

    def test_eval_run_in_allowed_event_kinds(self):
        from ai_engineering.state.event_schema import ALLOWED_EVENT_KINDS

        assert "eval_run" in ALLOWED_EVENT_KINDS

    def test_memory_event_repaired_in_allowed_event_kinds(self):
        """Side-effect of spec-119 Phase 1: memory_event is now in the
        Python validator (the canonical hook had it but the validator did
        not, so memory_event events from the canonical hook would fail
        validate_event_schema in callers using the Python library path)."""
        from ai_engineering.state.event_schema import ALLOWED_EVENT_KINDS

        assert "memory_event" in ALLOWED_EVENT_KINDS
