"""Capability-card construction and task-packet acceptance for HX-06."""

from __future__ import annotations

from collections.abc import Iterable

from ai_engineering.config.manifest import ManifestConfig, SkillEntry
from ai_engineering.state.models import (
    CapabilityAcceptanceResult,
    CapabilityCard,
    CapabilityKind,
    CapabilityTaskPacket,
    CapabilityToolScope,
    MutationClass,
    ProviderCompatibility,
    ProviderCompatibilityStatus,
    TopologyRole,
    WriteScopeClass,
)

_AGENT_ALIASES = {
    "autopilot": "ai-autopilot",
    "build": "ai-build",
    "explore": "ai-explore",
    "guard": "ai-guard",
    "guide": "ai-guide",
    "plan": "ai-plan",
    "review": "ai-review",
    "run": "ai-run-orchestrator",
    "run-orchestrator": "ai-run-orchestrator",
    "simplify": "ai-simplify",
    "verify": "ai-verify",
}

_INTERNAL_SPECIALIST_PREFIXES = ("reviewer-", "verifier-", "review-", "verify-")

_AGENT_TOPOLOGY = {
    "ai-autopilot": TopologyRole.ORCHESTRATOR,
    "ai-run-orchestrator": TopologyRole.ORCHESTRATOR,
    "ai-plan": TopologyRole.ORCHESTRATOR,
    "ai-review": TopologyRole.ORCHESTRATOR,
    "ai-verify": TopologyRole.ORCHESTRATOR,
    "ai-build": TopologyRole.PUBLIC_FIRST_CLASS,
    "ai-explore": TopologyRole.LEAF,
    "ai-guard": TopologyRole.LEAF,
    "ai-guide": TopologyRole.LEAF,
    "ai-simplify": TopologyRole.LEAF,
}

_AGENT_MUTATIONS = {
    "ai-autopilot": {
        MutationClass.READ,
        MutationClass.ADVISE,
        MutationClass.SPEC_WRITE,
        MutationClass.STATE_WRITE,
        MutationClass.GIT_WRITE,
        MutationClass.BOARD_WRITE,
        MutationClass.TELEMETRY_EMIT,
    },
    "ai-build": {
        MutationClass.READ,
        MutationClass.ADVISE,
        MutationClass.CODE_WRITE,
        MutationClass.SPEC_WRITE,
        MutationClass.STATE_WRITE,
    },
    "ai-explore": {MutationClass.READ, MutationClass.ADVISE},
    "ai-guard": {
        MutationClass.READ,
        MutationClass.ADVISE,
        MutationClass.STATE_WRITE,
        MutationClass.TELEMETRY_EMIT,
    },
    "ai-guide": {MutationClass.READ, MutationClass.ADVISE},
    "ai-plan": {
        MutationClass.READ,
        MutationClass.ADVISE,
        MutationClass.SPEC_WRITE,
        MutationClass.STATE_WRITE,
    },
    "ai-review": {MutationClass.READ, MutationClass.ADVISE, MutationClass.SPEC_WRITE},
    "ai-run-orchestrator": {
        MutationClass.READ,
        MutationClass.ADVISE,
        MutationClass.SPEC_WRITE,
        MutationClass.STATE_WRITE,
        MutationClass.GIT_WRITE,
        MutationClass.BOARD_WRITE,
        MutationClass.TELEMETRY_EMIT,
    },
    "ai-simplify": {MutationClass.READ, MutationClass.ADVISE, MutationClass.CODE_WRITE},
    "ai-verify": {MutationClass.READ, MutationClass.ADVISE, MutationClass.SPEC_WRITE},
}

_AGENT_WRITE_SCOPES = {
    "ai-autopilot": {
        WriteScopeClass.SPEC,
        WriteScopeClass.STATE,
        WriteScopeClass.DOCUMENTATION,
        WriteScopeClass.GIT,
        WriteScopeClass.BOARD,
        WriteScopeClass.TELEMETRY,
    },
    "ai-build": {
        WriteScopeClass.SOURCE,
        WriteScopeClass.TEST,
        WriteScopeClass.SPEC,
        WriteScopeClass.STATE,
        WriteScopeClass.MANIFEST,
        WriteScopeClass.MIRROR,
        WriteScopeClass.DOCUMENTATION,
        WriteScopeClass.HOOK,
        WriteScopeClass.GENERATED,
    },
    "ai-explore": {WriteScopeClass.NONE},
    "ai-guard": {WriteScopeClass.SPEC, WriteScopeClass.STATE, WriteScopeClass.TELEMETRY},
    "ai-guide": {WriteScopeClass.NONE},
    "ai-plan": {WriteScopeClass.SPEC, WriteScopeClass.STATE, WriteScopeClass.DOCUMENTATION},
    "ai-review": {WriteScopeClass.SPEC, WriteScopeClass.DOCUMENTATION},
    "ai-run-orchestrator": {
        WriteScopeClass.SPEC,
        WriteScopeClass.STATE,
        WriteScopeClass.DOCUMENTATION,
        WriteScopeClass.GIT,
        WriteScopeClass.BOARD,
        WriteScopeClass.TELEMETRY,
    },
    "ai-simplify": {WriteScopeClass.SOURCE, WriteScopeClass.TEST},
    "ai-verify": {WriteScopeClass.SPEC, WriteScopeClass.DOCUMENTATION},
}

_DEFAULT_AGENT_TOOLS = {
    CapabilityToolScope.READ,
    CapabilityToolScope.SEARCH,
    CapabilityToolScope.MEMORY,
}

_WRITE_AGENT_TOOLS = {
    *_DEFAULT_AGENT_TOOLS,
    CapabilityToolScope.EDIT,
    CapabilityToolScope.TERMINAL,
    CapabilityToolScope.TEST,
    CapabilityToolScope.VALIDATE,
}

_ORCHESTRATOR_TOOLS = {
    *_WRITE_AGENT_TOOLS,
    CapabilityToolScope.GIT,
    CapabilityToolScope.GITHUB,
    CapabilityToolScope.SUBAGENT,
}

_PROVIDER_SCOPED_SKILLS = {
    "ai-analyze-permissions": {
        "claude_code": ProviderCompatibilityStatus.COMPATIBLE,
        "github_copilot": ProviderCompatibilityStatus.UNSUPPORTED,
        "gemini": ProviderCompatibilityStatus.UNSUPPORTED,
        "codex": ProviderCompatibilityStatus.UNSUPPORTED,
    }
}

_SKILL_TYPE_MUTATIONS = {
    "workflow": {MutationClass.READ, MutationClass.ADVISE, MutationClass.SPEC_WRITE},
    "delivery": {MutationClass.READ, MutationClass.ADVISE, MutationClass.GIT_WRITE},
    "enterprise": {MutationClass.READ, MutationClass.ADVISE, MutationClass.STATE_WRITE},
    "teaching": {MutationClass.READ, MutationClass.ADVISE},
    "writing": {MutationClass.READ, MutationClass.ADVISE, MutationClass.SPEC_WRITE},
    "sdlc": {MutationClass.READ, MutationClass.ADVISE, MutationClass.SPEC_WRITE},
    "meta": {MutationClass.READ, MutationClass.ADVISE, MutationClass.STATE_WRITE},
    "design": {MutationClass.READ, MutationClass.ADVISE, MutationClass.CODE_WRITE},
}

_SKILL_TAG_MUTATIONS = {
    "implementation": {MutationClass.CODE_WRITE},
    "git": {MutationClass.GIT_WRITE},
    "board": {MutationClass.BOARD_WRITE},
    "sync": {MutationClass.BOARD_WRITE},
    "bootstrap": {MutationClass.STATE_WRITE, MutationClass.TELEMETRY_EMIT},
    "learning": {MutationClass.STATE_WRITE},
    "continuous-improvement": {MutationClass.STATE_WRITE},
    "orchestration": {MutationClass.STATE_WRITE},
}

_SKILL_TYPE_WRITE_SCOPES = {
    "workflow": {WriteScopeClass.SPEC, WriteScopeClass.DOCUMENTATION},
    "delivery": {WriteScopeClass.GIT, WriteScopeClass.STATE},
    "enterprise": {WriteScopeClass.STATE, WriteScopeClass.MANIFEST, WriteScopeClass.HOOK},
    "teaching": {WriteScopeClass.NONE},
    "writing": {WriteScopeClass.DOCUMENTATION, WriteScopeClass.SPEC},
    "sdlc": {WriteScopeClass.SPEC, WriteScopeClass.DOCUMENTATION, WriteScopeClass.STATE},
    "meta": {WriteScopeClass.STATE, WriteScopeClass.SPEC, WriteScopeClass.MIRROR},
    "design": {WriteScopeClass.SOURCE, WriteScopeClass.DOCUMENTATION},
}

_SKILL_TAG_WRITE_SCOPES = {
    "implementation": {WriteScopeClass.SOURCE, WriteScopeClass.TEST},
    "git": {WriteScopeClass.GIT},
    "board": {WriteScopeClass.BOARD},
    "sync": {WriteScopeClass.BOARD},
    "bootstrap": {WriteScopeClass.STATE, WriteScopeClass.TELEMETRY},
    "orchestration": {WriteScopeClass.SPEC, WriteScopeClass.STATE},
    "framework": {WriteScopeClass.MIRROR, WriteScopeClass.MANIFEST},
}

_SKILL_TYPE_TOOLS = {
    "workflow": {
        CapabilityToolScope.READ,
        CapabilityToolScope.SEARCH,
        CapabilityToolScope.EDIT,
        CapabilityToolScope.TERMINAL,
        CapabilityToolScope.TEST,
        CapabilityToolScope.VALIDATE,
    },
    "delivery": {
        CapabilityToolScope.READ,
        CapabilityToolScope.SEARCH,
        CapabilityToolScope.TERMINAL,
        CapabilityToolScope.GIT,
        CapabilityToolScope.GITHUB,
        CapabilityToolScope.VALIDATE,
    },
    "enterprise": {
        CapabilityToolScope.READ,
        CapabilityToolScope.SEARCH,
        CapabilityToolScope.EDIT,
        CapabilityToolScope.TERMINAL,
        CapabilityToolScope.VALIDATE,
        CapabilityToolScope.GITHUB,
    },
    "teaching": {CapabilityToolScope.READ, CapabilityToolScope.SEARCH},
    "writing": {
        CapabilityToolScope.READ,
        CapabilityToolScope.SEARCH,
        CapabilityToolScope.EDIT,
        CapabilityToolScope.TERMINAL,
    },
    "sdlc": {
        CapabilityToolScope.READ,
        CapabilityToolScope.SEARCH,
        CapabilityToolScope.EDIT,
        CapabilityToolScope.TERMINAL,
        CapabilityToolScope.GIT,
        CapabilityToolScope.GITHUB,
    },
    "meta": {
        CapabilityToolScope.READ,
        CapabilityToolScope.SEARCH,
        CapabilityToolScope.EDIT,
        CapabilityToolScope.TERMINAL,
        CapabilityToolScope.VALIDATE,
        CapabilityToolScope.SUBAGENT,
    },
    "design": {
        CapabilityToolScope.READ,
        CapabilityToolScope.SEARCH,
        CapabilityToolScope.EDIT,
        CapabilityToolScope.TERMINAL,
        CapabilityToolScope.BROWSER,
    },
}

_WRITE_SCOPE_TO_MUTATION = {
    WriteScopeClass.NONE: MutationClass.READ,
    WriteScopeClass.SOURCE: MutationClass.CODE_WRITE,
    WriteScopeClass.TEST: MutationClass.CODE_WRITE,
    WriteScopeClass.SPEC: MutationClass.SPEC_WRITE,
    WriteScopeClass.STATE: MutationClass.STATE_WRITE,
    WriteScopeClass.MANIFEST: MutationClass.STATE_WRITE,
    WriteScopeClass.MIRROR: MutationClass.STATE_WRITE,
    WriteScopeClass.DOCUMENTATION: MutationClass.SPEC_WRITE,
    WriteScopeClass.HOOK: MutationClass.STATE_WRITE,
    WriteScopeClass.GENERATED: MutationClass.CODE_WRITE,
    WriteScopeClass.GIT: MutationClass.GIT_WRITE,
    WriteScopeClass.BOARD: MutationClass.BOARD_WRITE,
    WriteScopeClass.TELEMETRY: MutationClass.TELEMETRY_EMIT,
    WriteScopeClass.UNKNOWN: MutationClass.CODE_WRITE,
}


def normalize_capability_name(name: str) -> str:
    """Normalize task owner roles and manifest agent names to capability ids."""
    normalized = name.strip().lower().replace("_", "-").replace(" ", "-")
    if not normalized:
        return normalized
    if normalized in _AGENT_ALIASES:
        return _AGENT_ALIASES[normalized]
    if normalized.startswith("ai-"):
        return normalized
    return f"ai-{normalized}"


def classify_write_scope(scope: str) -> WriteScopeClass:
    """Classify a task write-scope path into the HX-06 write taxonomy."""
    normalized = scope.strip().replace("\\", "/")
    while normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.rstrip("/")

    if not normalized:
        return WriteScopeClass.UNKNOWN
    if normalized in {"*", "**"}:
        return WriteScopeClass.UNKNOWN
    if normalized.startswith(".ai-engineering/specs/"):
        return WriteScopeClass.SPEC
    if normalized.startswith(".ai-engineering/state/"):
        if normalized.endswith("framework-events.ndjson"):
            return WriteScopeClass.TELEMETRY
        return WriteScopeClass.STATE
    if normalized in {".ai-engineering/manifest.yml", "sonar-project.properties"}:
        return WriteScopeClass.MANIFEST
    if normalized.startswith("src/ai_engineering/templates/.ai-engineering/"):
        return WriteScopeClass.GENERATED
    if normalized.startswith((".claude/", ".codex/", ".gemini/")):
        return WriteScopeClass.MIRROR
    if normalized.startswith((".github/agents/", ".github/skills/")):
        return WriteScopeClass.MIRROR
    if normalized.startswith((".github/hooks/", ".ai-engineering/scripts/hooks/")):
        return WriteScopeClass.HOOK
    if normalized.startswith("tests/"):
        return WriteScopeClass.TEST
    if normalized.startswith(("src/", "scripts/")):
        return WriteScopeClass.SOURCE
    if normalized.startswith("docs/") or normalized.endswith(".md"):
        return WriteScopeClass.DOCUMENTATION
    if normalized.startswith(".git/"):
        return WriteScopeClass.GIT
    return WriteScopeClass.UNKNOWN


def infer_mutation_classes(write_scopes: Iterable[str]) -> list[MutationClass]:
    """Infer minimum mutation classes implied by write-scope paths."""
    mutations = {MutationClass.READ}
    for scope in write_scopes:
        mutations.add(_WRITE_SCOPE_TO_MUTATION[classify_write_scope(scope)])
    return sorted(mutations, key=lambda item: item.value)


def build_capability_cards(config: ManifestConfig) -> list[CapabilityCard]:
    """Build capability cards from manifest registry metadata."""
    provider_names = list(
        dict.fromkeys(config.ai_providers.enabled or [config.ai_providers.primary])
    )
    cards = [
        _build_skill_card(name, entry, provider_names)
        for name, entry in sorted(config.skills.registry.items())
    ]
    cards.extend(_build_agent_card(name, provider_names) for name in sorted(config.agents.names))
    return sorted(cards, key=lambda card: (card.capability_kind.value, card.name))


def _build_agent_card(name: str, provider_names: list[str]) -> CapabilityCard:
    normalized_name = normalize_capability_name(name)
    topology_role = _agent_topology_role(normalized_name)
    mutations = _AGENT_MUTATIONS.get(normalized_name, {MutationClass.READ, MutationClass.ADVISE})
    write_scopes = _AGENT_WRITE_SCOPES.get(normalized_name, {WriteScopeClass.NONE})
    tools = _agent_tools_for(normalized_name, topology_role)
    return CapabilityCard(
        name=normalized_name,
        capabilityKind=CapabilityKind.AGENT,
        topologyRole=topology_role,
        mutationClasses=sorted(mutations, key=lambda item: item.value),
        writeScopeClasses=sorted(write_scopes, key=lambda item: item.value),
        toolScope=sorted(tools, key=lambda item: item.value),
        providerCompatibility=_provider_compatibility(normalized_name, provider_names),
        acceptsTaskPackets=topology_role != TopologyRole.INTERNAL_SPECIALIST,
        public=topology_role != TopologyRole.INTERNAL_SPECIALIST,
    )


def _agent_topology_role(name: str) -> TopologyRole:
    if _is_internal_specialist_name(name):
        return TopologyRole.INTERNAL_SPECIALIST
    return _AGENT_TOPOLOGY.get(name, TopologyRole.PUBLIC_FIRST_CLASS)


def _is_internal_specialist_name(name: str) -> bool:
    bare_name = name.removeprefix("ai-")
    return any(bare_name.startswith(prefix) for prefix in _INTERNAL_SPECIALIST_PREFIXES)


def _agent_tools_for(name: str, topology_role: TopologyRole) -> set[CapabilityToolScope]:
    if topology_role == TopologyRole.ORCHESTRATOR:
        return _ORCHESTRATOR_TOOLS
    if MutationClass.CODE_WRITE in _AGENT_MUTATIONS.get(name, set()):
        return _WRITE_AGENT_TOOLS
    return _DEFAULT_AGENT_TOOLS


def _build_skill_card(
    name: str,
    entry: SkillEntry,
    provider_names: list[str],
) -> CapabilityCard:
    normalized_type = entry.type.strip().lower()
    tags = {tag.strip().lower() for tag in entry.tags}
    mutations = {MutationClass.READ, MutationClass.ADVISE}
    mutations.update(_SKILL_TYPE_MUTATIONS.get(normalized_type, set()))
    for tag in tags:
        mutations.update(_SKILL_TAG_MUTATIONS.get(tag, set()))

    write_scopes = set(_SKILL_TYPE_WRITE_SCOPES.get(normalized_type, {WriteScopeClass.NONE}))
    for tag in tags:
        write_scopes.update(_SKILL_TAG_WRITE_SCOPES.get(tag, set()))

    tools = set(_SKILL_TYPE_TOOLS.get(normalized_type, {CapabilityToolScope.READ}))
    if MutationClass.CODE_WRITE in mutations:
        tools.update({CapabilityToolScope.EDIT, CapabilityToolScope.TERMINAL})
    if MutationClass.GIT_WRITE in mutations:
        tools.add(CapabilityToolScope.GIT)
    if MutationClass.BOARD_WRITE in mutations:
        tools.add(CapabilityToolScope.GITHUB)

    return CapabilityCard(
        name=name,
        capabilityKind=CapabilityKind.SKILL,
        topologyRole=TopologyRole.PUBLIC_FIRST_CLASS,
        mutationClasses=sorted(mutations, key=lambda item: item.value),
        writeScopeClasses=sorted(write_scopes, key=lambda item: item.value),
        toolScope=sorted(tools, key=lambda item: item.value),
        providerCompatibility=_provider_compatibility(name, provider_names),
        acceptsTaskPackets=True,
        public=True,
    )


def _provider_compatibility(
    capability_name: str,
    provider_names: list[str],
) -> list[ProviderCompatibility]:
    scoped_status = _PROVIDER_SCOPED_SKILLS.get(capability_name, {})
    providers = provider_names or ["claude_code"]
    return [
        ProviderCompatibility(
            provider=provider,
            status=scoped_status.get(provider, ProviderCompatibilityStatus.COMPATIBLE),
        )
        for provider in providers
    ]


def validate_task_packet_acceptance(
    cards: Iterable[CapabilityCard],
    packet: CapabilityTaskPacket,
) -> CapabilityAcceptanceResult:
    """Validate whether a capability may accept a derived task packet."""
    cards_by_name = {card.name: card for card in cards}
    capability_name = normalize_capability_name(packet.owner_role)
    card = cards_by_name.get(capability_name)
    if card is None:
        return CapabilityAcceptanceResult(
            accepted=False,
            errors=[f"{packet.task_id}: no capability card for ownerRole {packet.owner_role}"],
        )

    errors: list[str] = []
    warnings: list[str] = []
    if not card.accepts_task_packets:
        errors.append(f"{packet.task_id}: {card.name} does not accept task packets")

    requested_mutations = set(packet.mutation_classes or infer_mutation_classes(packet.write_scope))
    illegal_mutations = requested_mutations - set(card.mutation_classes)
    if illegal_mutations:
        rendered = ", ".join(sorted(item.value for item in illegal_mutations))
        errors.append(f"{packet.task_id}: {card.name} cannot perform mutation classes: {rendered}")

    requested_write_classes = {classify_write_scope(scope) for scope in packet.write_scope}
    illegal_write_classes = requested_write_classes - set(card.write_scope_classes)
    if illegal_write_classes:
        rendered = ", ".join(sorted(item.value for item in illegal_write_classes))
        errors.append(f"{packet.task_id}: {card.name} cannot write scope classes: {rendered}")

    broad_or_unknown = requested_write_classes & {WriteScopeClass.UNKNOWN}
    if broad_or_unknown:
        warnings.append(f"{packet.task_id}: write scope contains broad or unknown paths")

    illegal_tools = set(packet.tool_requests) - set(card.tool_scope)
    if illegal_tools:
        rendered = ", ".join(sorted(item.value for item in illegal_tools))
        errors.append(f"{packet.task_id}: {card.name} cannot request tool scopes: {rendered}")

    if packet.provider:
        _validate_provider(card, packet.provider, packet.task_id, errors, warnings)

    return CapabilityAcceptanceResult(accepted=not errors, errors=errors, warnings=warnings)


def _validate_provider(
    card: CapabilityCard,
    provider: str,
    task_id: str,
    errors: list[str],
    warnings: list[str],
) -> None:
    compatibility = {item.provider: item.status for item in card.provider_compatibility}
    status = compatibility.get(provider)
    if status is None:
        errors.append(f"{task_id}: {card.name} has no compatibility declaration for {provider}")
        return
    if status == ProviderCompatibilityStatus.UNSUPPORTED:
        errors.append(f"{task_id}: {card.name} is incompatible with provider {provider}")
    elif status == ProviderCompatibilityStatus.DEGRADED:
        warnings.append(f"{task_id}: {card.name} runs degraded on provider {provider}")
