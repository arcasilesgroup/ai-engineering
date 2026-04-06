"""RED tests for framework runtime dependency-closure validation."""

from __future__ import annotations

import importlib

import pytest


def test_validate_framework_dependency_closure_detects_typer_click_incompatibility(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependency_closure = importlib.import_module("ai_engineering.doctor.dependency_closure")

    monkeypatch.setattr(
        dependency_closure,
        "_installed_version",
        lambda name: {"typer": "0.24.1", "click": "8.1.8"}[name],
        raising=False,
    )
    monkeypatch.setattr(
        dependency_closure,
        "_required_dependencies",
        lambda name: ["click>=8.2.1"] if name == "typer" else [],
        raising=False,
    )

    violations = dependency_closure.validate_framework_dependency_closure()

    assert len(violations) == 1
    violation = violations[0]
    assert violation.package == "typer"
    assert violation.dependency == "click"
    assert violation.required_specifier == ">=8.2.1"
    assert violation.actual_version == "8.1.8"


def test_validate_framework_dependency_closure_returns_empty_when_runtime_is_consistent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dependency_closure = importlib.import_module("ai_engineering.doctor.dependency_closure")

    monkeypatch.setattr(
        dependency_closure,
        "_installed_version",
        lambda name: {"typer": "0.24.1", "click": "8.3.1"}[name],
        raising=False,
    )
    monkeypatch.setattr(
        dependency_closure,
        "_required_dependencies",
        lambda name: ["click>=8.2.1"] if name == "typer" else [],
        raising=False,
    )

    violations = dependency_closure.validate_framework_dependency_closure()

    assert violations == []
