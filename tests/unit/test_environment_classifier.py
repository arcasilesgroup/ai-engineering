"""RED tests for the shared environment classifier in spec-102."""

from __future__ import annotations

import importlib


def test_classify_failure_maps_runtime_packaging_feeds_tools_and_provider_prereqs() -> None:
    environment = importlib.import_module("ai_engineering.doctor.environment")

    assert (
        environment.classify_failure(RuntimeError("requires Python 3.11+"))
        == environment.FailureCategory.RUNTIME
    )
    assert (
        environment.classify_failure(ImportError("typer requires click>=8.2.1"))
        == environment.FailureCategory.PACKAGING
    )
    assert (
        environment.classify_failure(ConnectionError("feed auth failed for corporate index"))
        == environment.FailureCategory.FEEDS
    )
    assert (
        environment.classify_failure(FileNotFoundError("semgrep executable not found"))
        == environment.FailureCategory.TOOLS
    )
    assert (
        environment.classify_failure(
            RuntimeError("Azure CLI required for configured provider"),
            context={"provider_scoped": True},
        )
        == environment.FailureCategory.PROVIDER_PREREQUISITES
    )


def test_repair_strategy_matches_spec102_policy() -> None:
    environment = importlib.import_module("ai_engineering.doctor.environment")

    assert (
        environment.repair_strategy(environment.FailureCategory.RUNTIME)
        == environment.RemediationPolicy.FAIL_FAST
    )
    assert (
        environment.repair_strategy(environment.FailureCategory.PACKAGING)
        == environment.RemediationPolicy.TRY_REPAIR
    )
    assert (
        environment.repair_strategy(environment.FailureCategory.FEEDS)
        == environment.RemediationPolicy.VALIDATE_THEN_BLOCK
    )
    assert (
        environment.repair_strategy(environment.FailureCategory.TOOLS)
        == environment.RemediationPolicy.REQUIRE_CAPABILITY_CHECK
    )
    assert (
        environment.repair_strategy(environment.FailureCategory.PROVIDER_PREREQUISITES)
        == environment.RemediationPolicy.SCOPE_CHECK_FIRST
    )


def test_classify_failure_does_not_promote_other_provider_requirements() -> None:
    environment = importlib.import_module("ai_engineering.doctor.environment")

    category = environment.classify_failure(
        RuntimeError("Azure CLI required for configured provider"),
        context={
            "provider_scoped": True,
            "vcs_provider": "github",
            "required_provider": "azure_devops",
        },
    )

    assert category == environment.FailureCategory.TOOLS
