"""Unit tests for doctor service fix_tools remediation."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.doctor import service as doctor_service


def test_remediate_python_tools_skips_ready_tools(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        doctor_service,
        "detect_python_tools",
        lambda: {
            "uv": {"ready": True},
            "ruff": {"ready": True},
            "ty": {"ready": True},
            "pipAudit": {"ready": True},
        },
    )
    remediation_calls: list[str] = []
    monkeypatch.setattr(
        doctor_service,
        "_attempt_tool_remediation",
        lambda _root, tool: (remediation_calls.append(tool), (True, "ok"))[-1],
    )

    results = doctor_service._remediate_python_tools(Path.cwd())

    assert all(r["ready"] for r in results.values())
    assert all(not r["remediated"] for r in results.values())
    assert remediation_calls == []


def test_remediate_python_tools_attempts_fix_for_missing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        doctor_service,
        "detect_python_tools",
        lambda: {
            "uv": {"ready": False},
            "ruff": {"ready": True},
            "ty": {"ready": True},
            "pipAudit": {"ready": True},
        },
    )
    monkeypatch.setattr(
        doctor_service,
        "_attempt_tool_remediation",
        lambda _root, _tool: (True, "auto-remediation installed uv"),
    )

    results = doctor_service._remediate_python_tools(Path.cwd())

    assert results["uv"]["ready"] is True
    assert results["uv"]["remediated"] is True
    assert results["ruff"]["remediated"] is False
