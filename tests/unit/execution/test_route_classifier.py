"""Execution route classifier — spec-145 route-only contract."""

from __future__ import annotations

import pytest

from ai_engineering.execution.route import classify_execution_route


@pytest.mark.unit
def test_single_concern_plan_routes_to_build() -> None:
    route = classify_execution_route(
        spec="spec-test",
        status="approved",
        concern_count=1,
        estimated_files=3,
    )

    assert route.executor == "build"
    assert route.safe_next_command == "/ai-build"
    assert route.executable is True


@pytest.mark.unit
def test_multi_concern_plan_routes_to_autopilot() -> None:
    route = classify_execution_route(
        spec="spec-test",
        status="approved",
        concern_count=3,
        estimated_files=4,
    )

    assert route.executor == "autopilot"
    assert route.safe_next_command == "/ai-autopilot"
    assert route.executable is True


@pytest.mark.unit
def test_large_file_count_plan_routes_to_autopilot() -> None:
    route = classify_execution_route(
        spec="spec-test",
        status="approved",
        concern_count=1,
        estimated_files=10,
    )

    assert route.executor == "autopilot"
    assert "10" in route.reason


@pytest.mark.unit
def test_draft_plan_has_non_executable_recommendation() -> None:
    route = classify_execution_route(
        spec="spec-test",
        status="draft",
        concern_count=1,
        estimated_files=3,
    )

    assert route.executor == "build"
    assert route.safe_next_command == "/ai-build"
    assert route.executable is False
    assert "approved" in route.reason
