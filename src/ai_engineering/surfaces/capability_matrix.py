"""Host capability matrix (spec-197 T-1).

Documents skill discovery paths, precedence, invocation mechanisms
for each enabled host.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class HostCapability:
    """Capability record for a single host."""

    host_id: str
    skill_discovery_paths: list[str]
    skill_precedence: str  # "first-wins" or "all-merged"
    invocation_syntax: str  # "/ai-*", "$ai-*", "thin-command"
    agent_path: str | None
    hook_mechanism: str
    root_instruction_path: str
    user_only_policy: str | None  # "disable-model-invocation" or None
    status: str  # "verified", "unverified"

    def to_dict(self) -> dict[str, Any]:
        return {
            "host_id": self.host_id,
            "skill_discovery_paths": self.skill_discovery_paths,
            "skill_precedence": self.skill_precedence,
            "invocation_syntax": self.invocation_syntax,
            "agent_path": self.agent_path,
            "hook_mechanism": self.hook_mechanism,
            "root_instruction_path": self.root_instruction_path,
            "user_only_policy": self.user_only_policy,
            "status": self.status,
        }


# Default capability matrix
CAPABILITY_MATRIX: list[HostCapability] = [
    HostCapability(
        host_id="claude-code",
        skill_discovery_paths=[".claude/skills"],
        skill_precedence="first-wins",
        invocation_syntax="/ai-*",
        agent_path=".claude/agents",
        hook_mechanism="user-prompt-submit",
        root_instruction_path=".claude/AGENTS.md",
        user_only_policy="disable-model-invocation",
        status="verified",
    ),
    HostCapability(
        host_id="codex",
        skill_discovery_paths=[".codex/skills"],
        skill_precedence="first-wins",
        invocation_syntax="$ai-*",
        agent_path=None,
        hook_mechanism="config-based",
        root_instruction_path=".codex/AGENTS.md",
        user_only_policy="policy.allow_implicit_invocation: false",
        status="verified",
    ),
    HostCapability(
        host_id="opencode",
        skill_discovery_paths=[".opencode/commands"],
        skill_precedence="first-wins",
        invocation_syntax="/ai-* (thin command)",
        agent_path=None,
        hook_mechanism="config-based",
        root_instruction_path=".opencode/AGENTS.md",
        user_only_policy=None,
        status="unverified",
    ),
    HostCapability(
        host_id="github-copilot",
        skill_discovery_paths=[".github/skills", ".claude/skills", ".agents/skills"],
        skill_precedence="first-wins",
        invocation_syntax="/ai-*",
        agent_path=".github/agents",
        hook_mechanism="config-based",
        root_instruction_path=".github/copilot-instructions.md",
        user_only_policy=None,
        status="verified",
    ),
    HostCapability(
        host_id="cursor",
        skill_discovery_paths=[".cursor/skills"],
        skill_precedence="first-wins",
        invocation_syntax="/ai-*",
        agent_path=None,
        hook_mechanism="config-based",
        root_instruction_path=".cursor/AGENTS.md",
        user_only_policy=None,
        status="unverified",
    ),
    HostCapability(
        host_id="antigravity",
        skill_discovery_paths=[".agents/skills"],
        skill_precedence="first-wins",
        invocation_syntax="unknown",
        agent_path=".agents/agents",
        hook_mechanism="unknown",
        root_instruction_path=".agents/AGENTS.md",
        user_only_policy=None,
        status="unverified",
    ),
]


def get_capability(host_id: str) -> HostCapability | None:
    """Get capability for a host."""
    for cap in CAPABILITY_MATRIX:
        if cap.host_id == host_id:
            return cap
    return None


def get_verified_hosts() -> list[HostCapability]:
    """Get all verified hosts."""
    return [cap for cap in CAPABILITY_MATRIX if cap.status == "verified"]


def get_unverified_hosts() -> list[HostCapability]:
    """Get all unverified hosts."""
    return [cap for cap in CAPABILITY_MATRIX if cap.status == "unverified"]
