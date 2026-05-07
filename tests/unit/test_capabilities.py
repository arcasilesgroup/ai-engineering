"""Tests for HX-06 capability-card task acceptance."""

from __future__ import annotations

from ai_engineering.config.manifest import (
    AgentsConfig,
    AiProvidersConfig,
    ManifestConfig,
    SkillEntry,
    SkillsConfig,
)
from ai_engineering.state.capabilities import (
    build_capability_cards,
    classify_write_scope,
    infer_mutation_classes,
    validate_task_packet_acceptance,
)
from ai_engineering.state.models import (
    CapabilityTaskPacket,
    CapabilityToolScope,
    MutationClass,
    ProviderCompatibilityStatus,
    TopologyRole,
    WriteScopeClass,
)


def _manifest_config() -> ManifestConfig:
    return ManifestConfig(
        skills=SkillsConfig(
            total=2,
            registry={
                "ai-code": SkillEntry(type="workflow", tags=["implementation"]),
                "ai-analyze-permissions": SkillEntry(type="meta", tags=["permissions"]),
            },
        ),
        agents=AgentsConfig(total=3, names=["plan", "build", "explore"]),
        ai_providers=AiProvidersConfig(
            enabled=["claude-code", "github-copilot", "gemini", "codex"],
            primary="claude-code",
        ),
    )


def test_classify_write_scope_uses_hx06_taxonomy() -> None:
    assert classify_write_scope("src/ai_engineering/state/models.py") == WriteScopeClass.SOURCE
    assert classify_write_scope("tests/unit/test_capabilities.py") == WriteScopeClass.TEST
    assert classify_write_scope(".ai-engineering/specs/plan.md") == WriteScopeClass.SPEC
    assert classify_write_scope(".ai-engineering/state/framework-events.ndjson") == (
        WriteScopeClass.TELEMETRY
    )
    assert classify_write_scope(".codex/skills/ai-code/SKILL.md") == WriteScopeClass.MIRROR


def test_infer_mutation_classes_from_write_scopes() -> None:
    assert infer_mutation_classes(
        ["src/ai_engineering/state/models.py", ".ai-engineering/specs/plan.md"]
    ) == [MutationClass.CODE_WRITE, MutationClass.READ, MutationClass.SPEC_WRITE]


def test_build_capability_cards_models_provider_scoped_skills() -> None:
    cards = build_capability_cards(_manifest_config())
    permissions_card = next(card for card in cards if card.name == "ai-analyze-permissions")
    statuses = {entry.provider: entry.status for entry in permissions_card.provider_compatibility}

    assert statuses["claude-code"] == ProviderCompatibilityStatus.COMPATIBLE
    assert statuses["github-copilot"] == ProviderCompatibilityStatus.UNSUPPORTED


def test_internal_specialist_agent_names_never_become_public_capabilities() -> None:
    config = _manifest_config()
    config.agents.names.append("reviewer-correctness")

    cards = build_capability_cards(config)
    specialist_card = next(card for card in cards if card.name == "ai-reviewer-correctness")

    assert specialist_card.topology_role == TopologyRole.INTERNAL_SPECIALIST
    assert specialist_card.public is False
    assert specialist_card.accepts_task_packets is False


def test_build_agent_packet_accepts_source_write_and_edit_tool() -> None:
    cards = build_capability_cards(_manifest_config())
    packet = CapabilityTaskPacket(
        taskId="T-build",
        ownerRole="Build",
        mutationClasses=[MutationClass.CODE_WRITE],
        writeScope=["src/ai_engineering/state/models.py"],
        toolRequests=[CapabilityToolScope.EDIT],
    )

    result = validate_task_packet_acceptance(cards, packet)

    assert result.accepted is True
    assert result.errors == []


def test_plan_packet_rejects_source_code_write() -> None:
    cards = build_capability_cards(_manifest_config())
    packet = CapabilityTaskPacket(
        taskId="T-plan",
        ownerRole="Plan",
        mutationClasses=[MutationClass.CODE_WRITE],
        writeScope=["src/ai_engineering/state/models.py"],
    )

    result = validate_task_packet_acceptance(cards, packet)

    assert result.accepted is False
    assert any("cannot perform mutation classes: code-write" in error for error in result.errors)
    assert any("cannot write scope classes: source" in error for error in result.errors)


def test_read_only_agent_packet_rejects_edit_tool_request() -> None:
    cards = build_capability_cards(_manifest_config())
    packet = CapabilityTaskPacket(
        taskId="T-explore",
        ownerRole="ai-explore",
        toolRequests=[CapabilityToolScope.EDIT],
    )

    result = validate_task_packet_acceptance(cards, packet)

    assert result.accepted is False
    assert any("cannot request tool scopes: edit" in error for error in result.errors)


def test_provider_incompatible_skill_packet_rejects_provider_binding() -> None:
    cards = build_capability_cards(_manifest_config())
    packet = CapabilityTaskPacket(
        taskId="T-provider",
        ownerRole="ai-analyze-permissions",
        provider="github-copilot",
    )

    result = validate_task_packet_acceptance(cards, packet)

    assert result.accepted is False
    assert any("incompatible with provider github-copilot" in error for error in result.errors)


def test_unknown_owner_rejects_packet() -> None:
    cards = build_capability_cards(_manifest_config())
    packet = CapabilityTaskPacket(
        taskId="T-unknown",
        ownerRole="Mystery",
        writeScope=[".ai-engineering/specs/plan.md"],
    )

    result = validate_task_packet_acceptance(cards, packet)

    assert result.accepted is False
    assert result.errors == ["T-unknown: no capability card for ownerRole Mystery"]
