"""Tests for _lib.observability -- the stdlib-only hook-local observability module.

Validates that the self-contained _lib version produces identical NDJSON output
to the canonical ai_engineering.state.observability package version, using only
Python stdlib (no Pydantic, no third-party imports).
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path
from typing import ClassVar
from unittest.mock import patch

import pytest

from ai_engineering.state import observability as pkg_obs

# Insert hooks _lib onto sys.path so we can import without the pip package.
_HOOKS_DIR = Path(__file__).parents[2] / ".ai-engineering" / "scripts" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
lib_obs = importlib.import_module("_lib.observability")


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Create a minimal project structure for event emission."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True)
    # Create minimal contexts for emit_declared_context_loads
    contexts = tmp_path / ".ai-engineering" / "contexts"
    (contexts / "team").mkdir(parents=True)
    (contexts / "team" / "lessons.md").write_text("# Lessons\n")
    (contexts / "team" / "conventions.md").write_text("# Conventions\n")
    (tmp_path / ".ai-engineering" / "CONSTITUTION.md").write_text("# Identity\n")
    (tmp_path / ".ai-engineering" / "specs").mkdir(parents=True)
    (tmp_path / ".ai-engineering" / "specs" / "spec.md").write_text("# Spec\n")
    (tmp_path / ".ai-engineering" / "specs" / "plan.md").write_text("# Plan\n")
    (tmp_path / ".ai-engineering" / "state" / "decision-store.json").write_text("{}\n")
    return tmp_path


@pytest.fixture()
def ndjson_path(project_root: Path) -> Path:
    """Return the framework events NDJSON path."""
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


# ---------------------------------------------------------------------------
# 1. build_framework_event returns dict with all required fields
# ---------------------------------------------------------------------------


class TestBuildFrameworkEvent:
    """Verify build_framework_event produces a complete dict."""

    REQUIRED_KEYS: ClassVar[set[str]] = {
        "schemaVersion",
        "timestamp",
        "project",
        "engine",
        "kind",
        "outcome",
        "component",
        "correlationId",
        "detail",
    }

    def test_returns_dict(self, project_root: Path) -> None:
        result = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
        )
        assert isinstance(result, dict)

    def test_contains_all_required_keys(self, project_root: Path) -> None:
        result = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
        )
        assert self.REQUIRED_KEYS.issubset(result.keys())

    def test_schema_version(self, project_root: Path) -> None:
        result = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
        )
        assert result["schemaVersion"] == "1.0"

    def test_project_name_from_dir(self, project_root: Path) -> None:
        result = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
        )
        assert result["project"] == project_root.name

    def test_optional_fields_included_when_set(self, project_root: Path) -> None:
        result = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
            source="hook/session-start",
            session_id="sess-123",
            trace_id="trace-456",
            parent_id="parent-789",
        )
        assert result["source"] == "hook/session-start"
        assert result["sessionId"] == "sess-123"
        assert result["traceId"] == "trace-456"
        assert result["parentId"] == "parent-789"

    def test_optional_fields_excluded_when_none(self, project_root: Path) -> None:
        result = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
        )
        assert "source" not in result
        assert "sessionId" not in result
        assert "traceId" not in result
        assert "parentId" not in result

    def test_degraded_outcome_for_codex_without_session(self, project_root: Path) -> None:
        result = lib_obs.build_framework_event(
            project_root,
            engine="codex",
            kind="skill_invoked",
            component="test",
        )
        assert result["outcome"] == "degraded"
        assert "degraded_reason" in result["detail"]
        assert "sessionId" in result["detail"]["missing_fields"]

    def test_force_outcome_overrides_degraded(self, project_root: Path) -> None:
        result = lib_obs.build_framework_event(
            project_root,
            engine="codex",
            kind="framework_error",
            component="test",
            force_outcome="failure",
        )
        assert result["outcome"] == "failure"

    def test_custom_correlation_id(self, project_root: Path) -> None:
        result = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
            correlation_id="custom-id-123",
        )
        assert result["correlationId"] == "custom-id-123"

    def test_timestamp_format_iso8601(self, project_root: Path) -> None:
        result = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
        )
        ts = result["timestamp"]
        assert ts.endswith("Z")
        # Verify it parses without error
        from datetime import datetime

        datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# 2. append_framework_event writes valid JSON line with sort_keys=True
# ---------------------------------------------------------------------------


class TestAppendFrameworkEvent:
    """Verify NDJSON serialization."""

    def test_writes_single_json_line(self, project_root: Path, ndjson_path: Path) -> None:
        entry = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
        )
        lib_obs.append_framework_event(project_root, entry)
        lines = ndjson_path.read_text().strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["kind"] == "skill_invoked"

    def test_sort_keys_order(self, project_root: Path, ndjson_path: Path) -> None:
        entry = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
        )
        lib_obs.append_framework_event(project_root, entry)
        raw_line = ndjson_path.read_text().strip()
        parsed = json.loads(raw_line)
        keys = list(parsed.keys())
        assert keys == sorted(keys), "NDJSON output must use sort_keys=True"

    def test_multiple_appends_produce_multiple_lines(
        self, project_root: Path, ndjson_path: Path
    ) -> None:
        for i in range(3):
            entry = lib_obs.build_framework_event(
                project_root,
                engine="claude_code",
                kind="skill_invoked",
                component=f"test-{i}",
            )
            lib_obs.append_framework_event(project_root, entry)
        lines = ndjson_path.read_text().strip().splitlines()
        assert len(lines) == 3

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        deep_root = tmp_path / "deep" / "nested" / "project"
        deep_root.mkdir(parents=True)
        entry = lib_obs.build_framework_event(
            deep_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
        )
        lib_obs.append_framework_event(deep_root, entry)
        ndjson = deep_root / ".ai-engineering" / "state" / "framework-events.ndjson"
        assert ndjson.exists()


# ---------------------------------------------------------------------------
# 3. Each emit function returns correct dict with proper kind
# ---------------------------------------------------------------------------


class TestEmitFunctions:
    """Verify each emit helper sets the correct kind and detail fields."""

    def test_emit_skill_invoked(self, project_root: Path) -> None:
        result = lib_obs.emit_skill_invoked(
            project_root,
            engine="claude_code",
            skill_name="brainstorm",
            component="hook/user-prompt-submit",
        )
        assert result["kind"] == "skill_invoked"
        assert result["detail"]["skill"] == "ai-brainstorm"

    def test_emit_agent_dispatched(self, project_root: Path) -> None:
        result = lib_obs.emit_agent_dispatched(
            project_root,
            engine="claude_code",
            agent_name="build",
            component="hook/post-tool-use",
        )
        assert result["kind"] == "agent_dispatched"
        assert result["detail"]["agent"] == "ai-build"

    def test_emit_ide_hook_outcome(self, project_root: Path) -> None:
        result = lib_obs.emit_ide_hook_outcome(
            project_root,
            engine="claude_code",
            hook_kind="session-start",
            component="hook/session-start",
            outcome="success",
        )
        assert result["kind"] == "ide_hook"
        assert result["outcome"] == "success"
        assert result["detail"]["hook_kind"] == "session-start"

    def test_emit_framework_error(self, project_root: Path) -> None:
        result = lib_obs.emit_framework_error(
            project_root,
            engine="claude_code",
            component="hook/error",
            error_code="E_HOOK_FAILED",
            summary="Hook timed out",
        )
        assert result["kind"] == "framework_error"
        assert result["outcome"] == "failure"
        assert result["detail"]["error_code"] == "E_HOOK_FAILED"
        assert result["detail"]["summary"] == "Hook timed out"

    def test_emit_control_outcome(self, project_root: Path) -> None:
        result = lib_obs.emit_control_outcome(
            project_root,
            category="quality",
            control="ruff-check",
            component="gate-engine",
            outcome="success",
        )
        assert result["kind"] == "control_outcome"
        assert result["engine"] == "ai_engineering"
        assert result["detail"]["category"] == "quality"
        assert result["detail"]["control"] == "ruff-check"

    def test_emit_framework_operation(self, project_root: Path) -> None:
        result = lib_obs.emit_framework_operation(
            project_root,
            operation="capabilities-refresh",
            component="cli",
            outcome="success",
        )
        assert result["kind"] == "framework_operation"
        assert result["engine"] == "ai_engineering"
        assert result["detail"]["operation"] == "capabilities-refresh"

    def test_emit_skill_invoked_with_metadata(self, project_root: Path) -> None:
        result = lib_obs.emit_skill_invoked(
            project_root,
            engine="claude_code",
            skill_name="plan",
            component="hook/user-prompt-submit",
            metadata={"prompt_length": 42},
        )
        assert result["detail"]["skill"] == "ai-plan"
        assert result["detail"]["prompt_length"] == 42


# ---------------------------------------------------------------------------
# 4. emit_declared_context_loads emits only fixed contexts
# ---------------------------------------------------------------------------


class TestEmitDeclaredContextLoads:
    """Verify the simplified _lib version emits fixed contexts + team dir."""

    def test_emits_fixed_contexts(self, project_root: Path) -> None:
        events = lib_obs.emit_declared_context_loads(
            project_root,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-brainstorm",
            component="hook/user-prompt-submit",
        )
        # 4 fixed contexts + 2 team files = 6
        assert len(events) == 6

    def test_fixed_context_classes(self, project_root: Path) -> None:
        events = lib_obs.emit_declared_context_loads(
            project_root,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-brainstorm",
            component="hook/user-prompt-submit",
        )
        classes = [e["detail"]["context_class"] for e in events]
        assert "constitution" in classes
        assert "spec" in classes
        assert "plan" in classes
        assert "decision-store" in classes
        assert "team" in classes

    def test_all_events_are_context_load(self, project_root: Path) -> None:
        events = lib_obs.emit_declared_context_loads(
            project_root,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-brainstorm",
            component="hook/user-prompt-submit",
        )
        for event in events:
            assert event["kind"] == "context_load"

    def test_existing_file_outcome_success(self, project_root: Path) -> None:
        events = lib_obs.emit_declared_context_loads(
            project_root,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-brainstorm",
            component="hook/user-prompt-submit",
        )
        spec_event = next(e for e in events if e["detail"]["context_class"] == "spec")
        assert spec_event["outcome"] == "success"

    def test_missing_file_outcome_failure(self, tmp_path: Path) -> None:
        # Bare project root with no files
        events = lib_obs.emit_declared_context_loads(
            tmp_path,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-brainstorm",
            component="hook/user-prompt-submit",
        )
        spec_event = next(e for e in events if e["detail"]["context_class"] == "spec")
        assert spec_event["outcome"] == "failure"

    def test_team_dir_scanning(self, project_root: Path) -> None:
        events = lib_obs.emit_declared_context_loads(
            project_root,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-brainstorm",
            component="hook/user-prompt-submit",
        )
        team_events = [e for e in events if e["detail"]["context_class"] == "team"]
        team_names = sorted(e["detail"]["context_name"] for e in team_events)
        assert team_names == ["conventions", "lessons"]

    def test_root_constitution_is_preferred_when_present(self, project_root: Path) -> None:
        (project_root / "CONSTITUTION.md").write_text("# Root Constitution\n", encoding="utf-8")

        events = lib_obs.emit_declared_context_loads(
            project_root,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-brainstorm",
            component="hook/user-prompt-submit",
        )

        constitution_event = next(
            event for event in events if event["detail"]["context_class"] == "constitution"
        )
        assert constitution_event["detail"]["path"] == "CONSTITUTION.md"

    def test_nested_constitution_remains_compatibility_fallback(self, project_root: Path) -> None:
        (project_root / ".ai-engineering" / "CONSTITUTION.md").unlink()

        events = lib_obs.emit_declared_context_loads(
            project_root,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-brainstorm",
            component="hook/user-prompt-submit",
        )

        constitution_event = next(
            event for event in events if event["detail"]["context_class"] == "constitution"
        )
        assert constitution_event["detail"]["path"] == ".ai-engineering/CONSTITUTION.md"

    def test_active_pointer_redirects_declared_spec_contexts(self, project_root: Path) -> None:
        resolved_specs_dir = project_root / "resolved-work-plane"
        resolved_specs_dir.mkdir()
        (resolved_specs_dir / "spec.md").write_text("resolved spec\n", encoding="utf-8")
        (resolved_specs_dir / "plan.md").write_text("resolved plan\n", encoding="utf-8")
        (project_root / ".ai-engineering" / "specs" / "active-work-plane.json").write_text(
            json.dumps({"specsDir": "resolved-work-plane"}),
            encoding="utf-8",
        )

        events = lib_obs.emit_declared_context_loads(
            project_root,
            engine="claude_code",
            initiator_kind="skill",
            initiator_name="ai-brainstorm",
            component="hook/user-prompt-submit",
        )

        spec_event = next(e for e in events if e["detail"]["context_class"] == "spec")
        plan_event = next(e for e in events if e["detail"]["context_class"] == "plan")
        assert spec_event["detail"]["path"] == "resolved-work-plane/spec.md"
        assert plan_event["detail"]["path"] == "resolved-work-plane/plan.md"


# ---------------------------------------------------------------------------
# 5. Secret redaction in _bounded_summary
# ---------------------------------------------------------------------------


class TestBoundedSummary:
    """Verify secret redaction and truncation."""

    def test_none_input_returns_none(self) -> None:
        assert lib_obs._bounded_summary(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert lib_obs._bounded_summary("") is None

    def test_short_text_unchanged(self) -> None:
        assert lib_obs._bounded_summary("hello world") == "hello world"

    def test_redacts_api_key(self) -> None:
        result = lib_obs._bounded_summary('api_key="fake"')
        assert "[REDACTED]" in result
        assert "fake" not in result

    def test_redacts_token(self) -> None:
        result = lib_obs._bounded_summary("token: ghp_xxxxxxxxxxxx")
        assert "[REDACTED]" in result
        assert "ghp_xxxxxxxxxxxx" not in result

    def test_redacts_password(self) -> None:
        result = lib_obs._bounded_summary("password = mysecretpass123")
        assert "[REDACTED]" in result
        assert "mysecretpass123" not in result

    def test_redacts_authorization(self) -> None:
        result = lib_obs._bounded_summary("authorization: Bearer_tok123abc")
        assert "[REDACTED]" in result
        assert "Bearer_tok123abc" not in result

    def test_truncates_long_text(self) -> None:
        long_text = "x" * 300
        result = lib_obs._bounded_summary(long_text)
        assert result.endswith("...[truncated]")
        assert len(result) == 200 + len("...[truncated]")

    def test_redacts_then_truncates(self) -> None:
        # Build a string where redaction still leaves >200 chars
        long_prefix = "x" * 180
        text = long_prefix + " token: secretval " + "y" * 40
        result = lib_obs._bounded_summary(text)
        assert "[REDACTED]" in result
        assert result.endswith("...[truncated]")


# ---------------------------------------------------------------------------
# 6. _normalize_skill_name and _normalize_agent_name
# ---------------------------------------------------------------------------


class TestNormalization:
    """Verify name normalization helpers."""

    def test_skill_adds_prefix(self) -> None:
        assert lib_obs._normalize_skill_name("brainstorm") == "ai-brainstorm"

    def test_skill_preserves_existing_prefix(self) -> None:
        assert lib_obs._normalize_skill_name("ai-plan") == "ai-plan"

    def test_skill_strips_whitespace(self) -> None:
        assert lib_obs._normalize_skill_name("  debug  ") == "ai-debug"

    def test_skill_lowercases(self) -> None:
        assert lib_obs._normalize_skill_name("Brainstorm") == "ai-brainstorm"

    def test_agent_adds_prefix(self) -> None:
        assert lib_obs._normalize_agent_name("build") == "ai-build"

    def test_agent_strips_ai_colon_prefix(self) -> None:
        assert lib_obs._normalize_agent_name("ai:build") == "ai-build"

    def test_agent_preserves_existing_prefix(self) -> None:
        assert lib_obs._normalize_agent_name("ai-verify") == "ai-verify"

    def test_agent_strips_whitespace(self) -> None:
        assert lib_obs._normalize_agent_name("  guard  ") == "ai-guard"

    def test_agent_lowercases(self) -> None:
        assert lib_obs._normalize_agent_name("EXPLORE") == "ai-explore"


# ---------------------------------------------------------------------------
# 7. NDJSON equivalence: _lib vs package produce matching structure
# ---------------------------------------------------------------------------


class TestNDJSONEquivalence:
    """Compare _lib output against the canonical ai_engineering.state.observability."""

    # Fields that are generated per-call and cannot match
    _VOLATILE_KEYS: ClassVar[set[str]] = {"timestamp", "correlationId"}
    # Spec-107 H2: ``prev_event_hash`` is a write-order-dependent chain
    # pointer (SHA256 of the prior entry on disk). When _lib writes first
    # then pkg writes second, the pkg entry's pointer references the _lib
    # entry, so the values differ even though the *structure* is parity.
    # Strip the field from both sides before comparing values.
    _DETAIL_VOLATILE_KEYS: ClassVar[set[str]] = {"prev_event_hash"}

    def _strip_volatile(self, d: dict) -> dict:
        out = {k: v for k, v in d.items() if k not in self._VOLATILE_KEYS}
        detail = out.get("detail")
        if isinstance(detail, dict):
            out["detail"] = {k: v for k, v in detail.items() if k not in self._DETAIL_VOLATILE_KEYS}
        return out

    def test_skill_invoked_key_parity(self, project_root: Path, ndjson_path: Path) -> None:
        """Both modules produce the same JSON keys for skill_invoked."""
        common_args = {
            "engine": "claude_code",
            "skill_name": "brainstorm",
            "component": "hook/user-prompt-submit",
            "source": "hook/user-prompt-submit",
            "session_id": "sess-abc",
            "trace_id": "trace-xyz",
        }

        lib_entry = lib_obs.emit_skill_invoked(project_root, **common_args)

        # Package version writes to the same NDJSON file
        with patch.object(pkg_obs, "_project_name", return_value=project_root.name):
            pkg_entry = pkg_obs.emit_skill_invoked(project_root, **common_args)

        # Convert Pydantic model to dict with aliases (matching NDJSON serialization)
        pkg_dict = pkg_entry.model_dump(by_alias=True, exclude_none=True)

        # Keys must be identical
        assert set(lib_entry.keys()) == set(pkg_dict.keys())

        # Values must match (excluding volatile fields)
        lib_clean = self._strip_volatile(lib_entry)
        pkg_clean = self._strip_volatile(pkg_dict)
        assert lib_clean == pkg_clean

    def test_ndjson_sort_order_matches(self, project_root: Path, ndjson_path: Path) -> None:
        """Both modules serialize with sort_keys=True, producing identical key order."""
        lib_entry = lib_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="test",
            source="test",
            session_id="sess-1",
        )
        lib_line = json.dumps(lib_entry, sort_keys=True)
        lib_keys = list(json.loads(lib_line).keys())
        assert lib_keys == sorted(lib_keys)

    def test_framework_error_structure_matches(self, project_root: Path) -> None:
        """framework_error events have identical structure between lib and package."""
        common_args = {
            "engine": "claude_code",
            "component": "hook/error",
            "error_code": "E_TEST",
            "summary": "Test error occurred",
        }

        lib_entry = lib_obs.emit_framework_error(project_root, **common_args)

        with patch.object(pkg_obs, "_project_name", return_value=project_root.name):
            pkg_entry = pkg_obs.emit_framework_error(project_root, **common_args)

        pkg_dict = pkg_entry.model_dump(by_alias=True, exclude_none=True)

        assert set(lib_entry.keys()) == set(pkg_dict.keys())
        lib_clean = self._strip_volatile(lib_entry)
        pkg_clean = self._strip_volatile(pkg_dict)
        assert lib_clean == pkg_clean


# ---------------------------------------------------------------------------
# 8. Zero third-party imports in _lib module
# ---------------------------------------------------------------------------


class TestStdlibOnly:
    """Verify the _lib module uses only stdlib imports."""

    def test_no_ai_engineering_imports(self) -> None:
        import ast

        source = (_HOOKS_DIR / "_lib" / "observability.py").read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("ai_engineering"), (
                        f"Forbidden import: {alias.name}"
                    )
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert not node.module.startswith("ai_engineering"), (
                    f"Forbidden import from: {node.module}"
                )

    def test_no_pydantic_imports(self) -> None:
        source = (_HOOKS_DIR / "_lib" / "observability.py").read_text()
        assert "pydantic" not in source

    def test_no_third_party_imports(self) -> None:
        """Only stdlib modules should be imported."""
        source = (_HOOKS_DIR / "_lib" / "observability.py").read_text()
        # Allowlist of stdlib modules used. Spec-107 H2 added ``hashlib``
        # for the audit-chain pointer (SHA256 of the prior entry's
        # canonical-JSON payload) -- pure stdlib, no third-party dep.
        allowed = {
            "json",
            "os",
            "re",
            "datetime",
            "uuid",
            "pathlib",
            "__future__",
            "hashlib",
        }
        import ast

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top = alias.name.split(".")[0]
                    assert top in allowed, f"Non-stdlib import: {alias.name}"
            elif isinstance(node, ast.ImportFrom) and node.module:
                top = node.module.split(".")[0]
                assert top in allowed, f"Non-stdlib import from: {node.module}"
