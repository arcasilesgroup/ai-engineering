"""Executor-routing skill contract — spec-145 route-only scope."""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]

_SURFACES = (".claude", ".codex", ".gemini", ".github")


def _read(path: Path) -> str:
    assert path.is_file(), f"missing file: {path}"
    return path.read_text(encoding="utf-8")


@pytest.mark.unit
@pytest.mark.parametrize("surface", _SURFACES)
def test_ai_plan_writes_execution_route_metadata(surface: str) -> None:
    body = _read(_REPO_ROOT / surface / "skills" / "ai-plan" / "SKILL.md")

    for marker in (
        "execution_route",
        "safe_next_command",
        "executor: build",
        "executor: autopilot",
        "/ai-build",
        "/ai-autopilot",
    ):
        assert marker in body, f"{surface} ai-plan missing route marker {marker!r}"
    assert "status" in body, f"{surface} ai-plan must keep approval tied to plan status"


@pytest.mark.unit
@pytest.mark.parametrize("surface", _SURFACES)
def test_ai_build_refuses_autopilot_routed_plans(surface: str) -> None:
    body = _read(_REPO_ROOT / surface / "skills" / "ai-build" / "SKILL.md")

    assert "execution_route.executor" in body
    assert "executor: autopilot" in body
    assert "safe_next_command" in body
    assert "/ai-autopilot" in body
    assert "refuse" in body.lower()


@pytest.mark.unit
@pytest.mark.parametrize("surface", _SURFACES)
def test_no_hitl_reads_execution_route_before_legacy_heading_gate(surface: str) -> None:
    body = _read(_REPO_ROOT / surface / "skills" / "ai-build" / "handlers" / "no-hitl.md")

    assert "execution_route.executor" in body
    assert "authoritative" in body.lower()
    assert "legacy" in body.lower()
    assert "executor: autopilot" in body
    assert "/ai-autopilot" in body


@pytest.mark.unit
@pytest.mark.parametrize("surface", _SURFACES)
def test_autopilot_step_zero_does_not_hard_abort_on_host_probe(surface: str) -> None:
    body = _read(_REPO_ROOT / surface / "skills" / "ai-autopilot" / "SKILL.md")
    lower = body.lower()

    assert "ok_to_dispatch == false" not in body
    assert "abort with an operator warning" not in lower
    assert "hard admission gate" not in lower
    assert "refuses to fan out" not in lower
    assert "host probe" in lower
    assert "advisory" in lower or "diagnostic" in lower
