"""Tests for spec-120 §4.1 GenAI block + trace-context auto-fill (T-A5/A6).

Covers the pkg-side ``ai_engineering.state.observability``:

* :func:`build_framework_event` reshapes a flat ``usage`` dict into the
  OTel-mirroring nested ``detail.genai`` block and round-trips through
  ``validate_event_schema`` with the new optional fields.
* The hash chain remains unbroken when events carry the new
  ``traceId`` / ``spanId`` / ``parentSpanId`` root fields. We synthesise
  three sequential events and re-walk via
  :func:`audit_chain.verify_audit_chain` to prove the chain is intact.
* :func:`emit_skill_invoked` forwards ``usage`` through to the
  ``detail.genai`` block in the on-disk NDJSON.
* ``span_id`` auto-generation when the caller omits it.
* ``trace_id`` inheritance from a pre-existing ``trace-context.json``.
* Malformed ``usage`` (non-dict, missing required fields) is dropped
  silently AND surfaces a ``framework_error`` event.

Hermetic: every test uses ``tmp_path`` as the project root and a
patched manifest config so the pytest-xdist parallel runner stays
collision-free.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from ai_engineering.state import observability as pkg_obs
from ai_engineering.state import trace_context as tc
from ai_engineering.state.audit_chain import verify_audit_chain
from ai_engineering.state.event_schema import validate_event_schema


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    """Minimal on-disk project layout the observability path needs."""
    state_dir = tmp_path / ".ai-engineering" / "state"
    state_dir.mkdir(parents=True)
    return tmp_path


@pytest.fixture(autouse=True)
def patched_project_name(project_root: Path):
    """Skip manifest loading; the SUT only needs a stable project name."""
    with patch.object(pkg_obs, "_project_name", return_value=project_root.name) as p:
        yield p


def _serialize_for_validator(event: Any) -> dict:
    """Round-trip a Pydantic FrameworkEvent through model_dump for validation.

    ``validate_event_schema`` expects the on-disk JSON shape (camelCase
    aliases, no None values) -- mirror what ``append_framework_event``
    writes so the validator sees the same payload as a downstream
    consumer.
    """
    if hasattr(event, "model_dump"):
        data = event.model_dump(by_alias=True, exclude_none=True)
    else:
        data = dict(event)
    if "timestamp" in data and not isinstance(data["timestamp"], str):
        data["timestamp"] = data["timestamp"].strftime("%Y-%m-%dT%H:%M:%SZ")
    return data


# ---------------------------------------------------------------------------
# T-A5: build_framework_event(usage=...) reshapes into detail.genai
# ---------------------------------------------------------------------------


class TestBuildEventWithUsage:
    """Exercise the OTel-mirroring `genai` block synthesis."""

    def test_build_event_with_usage_validates(self, project_root: Path) -> None:
        """A complete usage dict produces a schema-valid `detail.genai`."""
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
            usage={
                "input_tokens": 1234,
                "output_tokens": 567,
                "model": "claude-sonnet-4-5",
                "system": "anthropic",
                "cost_usd": 0.0143,
            },
        )

        # Pydantic FrameworkEvent retains the genai block under detail.
        assert "genai" in event.detail
        genai = event.detail["genai"]
        assert genai["system"] == "anthropic"
        assert genai["request"] == {"model": "claude-sonnet-4-5"}
        assert genai["usage"]["input_tokens"] == 1234
        assert genai["usage"]["output_tokens"] == 567
        assert genai["usage"]["total_tokens"] == 1801  # auto-summed
        assert genai["usage"]["cost_usd"] == 0.0143

        # Round-trips through the canonical validator without rejection.
        on_disk = _serialize_for_validator(event)
        assert validate_event_schema(on_disk) is True

    def test_total_tokens_auto_computed_when_omitted(self, project_root: Path) -> None:
        """`total_tokens` defaults to input + output when caller omits it."""
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        assert event.detail["genai"]["usage"]["total_tokens"] == 150

    def test_explicit_total_tokens_preserved(self, project_root: Path) -> None:
        """A caller-provided `total_tokens` is preserved as-is."""
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
            usage={
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 999,
            },
        )
        assert event.detail["genai"]["usage"]["total_tokens"] == 999

    def test_genai_optional_fields_omitted_when_absent(self, project_root: Path) -> None:
        """`system` / `request` are only present when caller supplies the keys."""
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        genai = event.detail["genai"]
        assert "system" not in genai
        assert "request" not in genai
        assert "cost_usd" not in genai["usage"]

    def test_no_usage_kwarg_no_genai_block(self, project_root: Path) -> None:
        """Without `usage`, the detail.genai block must not appear."""
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
        )
        assert "genai" not in event.detail


# ---------------------------------------------------------------------------
# T-A5: trace-context auto-fill semantics
# ---------------------------------------------------------------------------


class TestAutoFill:
    """Auto-generated span_id, inherited trace_id."""

    def test_auto_span_id_generated_when_omitted(self, project_root: Path) -> None:
        """Caller omits `span_id` -> 16-hex value present in the event."""
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
        )
        assert event.span_id is not None
        assert len(event.span_id) == 16
        assert all(c in "0123456789abcdef" for c in event.span_id)

    def test_explicit_span_id_preserved(self, project_root: Path) -> None:
        """Caller-supplied `span_id` is forwarded verbatim."""
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
            span_id="abcdef0123456789",
        )
        assert event.span_id == "abcdef0123456789"

    def test_trace_id_inherited_from_context(self, project_root: Path) -> None:
        """A pre-existing trace-context.json supplies traceId on auto-fill."""
        existing_trace = "00112233445566778899aabbccddeeff"
        existing_parent = "1111222233334444"
        tc.write_trace_context(
            project_root,
            {"traceId": existing_trace, "span_stack": [existing_parent]},
        )

        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
        )
        assert event.trace_id == existing_trace
        assert event.parent_span_id == existing_parent

    def test_explicit_trace_id_skips_inheritance(self, project_root: Path) -> None:
        """Caller-supplied trace_id wins over the active context."""
        tc.write_trace_context(
            project_root,
            {"traceId": "00112233445566778899aabbccddeeff", "span_stack": []},
        )
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
            trace_id="ffeeddccbbaa99887766554433221100",
        )
        assert event.trace_id == "ffeeddccbbaa99887766554433221100"

    def test_fresh_trace_id_when_no_context(self, project_root: Path) -> None:
        """No context file + None trace_id => fresh 32-hex traceId."""
        assert not tc.trace_context_path(project_root).exists()
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
        )
        assert event.trace_id is not None
        assert len(event.trace_id) == 32
        assert all(c in "0123456789abcdef" for c in event.trace_id)
        assert event.parent_span_id is None


# ---------------------------------------------------------------------------
# T-A5: Audit-chain non-regression with new trace fields
# ---------------------------------------------------------------------------


class TestChainUnbroken:
    """Spec-120 §4.1 rule: new trace fields are absorbed by the hash chain."""

    def test_chain_unbroken_with_trace_fields(self, project_root: Path) -> None:
        """Three sequential emits produce a chain that ``verify_audit_chain`` accepts."""
        for index in range(3):
            pkg_obs.emit_skill_invoked(
                project_root,
                engine="claude_code",
                skill_name=f"ai-skill-{index}",
                component="hook.telemetry-skill",
                usage={"input_tokens": 100 + index, "output_tokens": 50 + index},
            )

        ndjson_path = pkg_obs.framework_events_path(project_root)
        verdict = verify_audit_chain(ndjson_path)
        assert verdict.ok is True
        assert verdict.entries_checked == 3
        assert verdict.first_break_index is None

    def test_each_chained_event_validates_against_schema(self, project_root: Path) -> None:
        """Every emitted event passes ``validate_event_schema``."""
        for index in range(3):
            pkg_obs.emit_skill_invoked(
                project_root,
                engine="claude_code",
                skill_name=f"ai-skill-{index}",
                component="hook.telemetry-skill",
                usage={"input_tokens": 100, "output_tokens": 50},
            )

        ndjson_path = pkg_obs.framework_events_path(project_root)
        for line in ndjson_path.read_text(encoding="utf-8").splitlines():
            entry = json.loads(line)
            assert validate_event_schema(entry) is True


# ---------------------------------------------------------------------------
# T-A6: emit helpers forward usage / trace context
# ---------------------------------------------------------------------------


class TestEmitHelpersForwarding:
    """`emit_skill_invoked` and `emit_agent_dispatched` forward new kwargs."""

    def test_emit_skill_invoked_with_usage(self, project_root: Path) -> None:
        """The on-disk NDJSON carries the OTel `genai.usage` shape."""
        pkg_obs.emit_skill_invoked(
            project_root,
            engine="claude_code",
            skill_name="brainstorm",
            component="hook.telemetry-skill",
            usage={
                "input_tokens": 1234,
                "output_tokens": 567,
                "model": "claude-sonnet-4-5",
                "system": "anthropic",
                "cost_usd": 0.0143,
            },
        )
        ndjson_path = pkg_obs.framework_events_path(project_root)
        line = ndjson_path.read_text(encoding="utf-8").strip().splitlines()[-1]
        parsed = json.loads(line)
        genai = parsed["detail"]["genai"]
        assert genai["usage"]["input_tokens"] == 1234
        assert genai["usage"]["output_tokens"] == 567
        assert genai["usage"]["total_tokens"] == 1801
        assert genai["usage"]["cost_usd"] == 0.0143
        assert genai["system"] == "anthropic"
        assert genai["request"] == {"model": "claude-sonnet-4-5"}

    def test_emit_skill_invoked_forwards_span_kwargs(self, project_root: Path) -> None:
        """Caller-supplied span_id / parent_span_id reach the on-disk event."""
        pkg_obs.emit_skill_invoked(
            project_root,
            engine="claude_code",
            skill_name="brainstorm",
            component="hook.telemetry-skill",
            span_id="abcdef0123456789",
            parent_span_id="0011223344556677",
            trace_id="ffeeddccbbaa99887766554433221100",
        )
        ndjson_path = pkg_obs.framework_events_path(project_root)
        line = ndjson_path.read_text(encoding="utf-8").strip().splitlines()[-1]
        parsed = json.loads(line)
        assert parsed["spanId"] == "abcdef0123456789"
        assert parsed["parentSpanId"] == "0011223344556677"
        assert parsed["traceId"] == "ffeeddccbbaa99887766554433221100"

    def test_emit_agent_dispatched_with_usage(self, project_root: Path) -> None:
        """`emit_agent_dispatched` mirrors `emit_skill_invoked` for usage."""
        pkg_obs.emit_agent_dispatched(
            project_root,
            engine="claude_code",
            agent_name="build",
            component="hook.dispatch",
            usage={"input_tokens": 200, "output_tokens": 100},
        )
        ndjson_path = pkg_obs.framework_events_path(project_root)
        line = ndjson_path.read_text(encoding="utf-8").strip().splitlines()[-1]
        parsed = json.loads(line)
        genai = parsed["detail"]["genai"]
        assert genai["usage"]["input_tokens"] == 200
        assert genai["usage"]["output_tokens"] == 100
        assert genai["usage"]["total_tokens"] == 300


# ---------------------------------------------------------------------------
# T-A5: Malformed usage = best-effort skip + framework_error
# ---------------------------------------------------------------------------


class TestMalformedUsage:
    """Defensive contract: bad `usage` never breaks the caller's flow."""

    def test_malformed_usage_skipped(self, project_root: Path) -> None:
        """Non-dict `usage` is dropped; framework_error is emitted instead."""
        # Pass a list instead of a dict.
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
            usage=["not", "a", "dict"],  # type: ignore[arg-type]
        )
        # The event itself was still built and contains no genai block.
        assert "genai" not in event.detail

        # And a framework_error landed on disk for forensic visibility.
        ndjson_path = pkg_obs.framework_events_path(project_root)
        assert ndjson_path.exists()
        lines = ndjson_path.read_text(encoding="utf-8").strip().splitlines()
        # At least one framework_error with the expected error_code.
        errors = [json.loads(line) for line in lines]
        assert any(
            e.get("kind") == "framework_error"
            and e.get("detail", {}).get("error_code") == "genai_usage_malformed"
            for e in errors
        )

    def test_usage_missing_required_fields_skipped(self, project_root: Path) -> None:
        """`usage` lacking input_tokens/output_tokens is treated as malformed."""
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
            usage={"model": "claude-sonnet-4-5"},  # no token counts
        )
        assert "genai" not in event.detail

        ndjson_path = pkg_obs.framework_events_path(project_root)
        errors = [
            json.loads(line)
            for line in ndjson_path.read_text(encoding="utf-8").strip().splitlines()
        ]
        assert any(
            e.get("kind") == "framework_error"
            and e.get("detail", {}).get("error_code") == "genai_usage_malformed"
            for e in errors
        )

    def test_usage_with_non_int_tokens_skipped(self, project_root: Path) -> None:
        """Token fields must be ints; strings are rejected."""
        event = pkg_obs.build_framework_event(
            project_root,
            engine="claude_code",
            kind="skill_invoked",
            component="hook.telemetry-skill",
            detail={"skill": "ai-brainstorm"},
            usage={"input_tokens": "1234", "output_tokens": "567"},
        )
        assert "genai" not in event.detail
