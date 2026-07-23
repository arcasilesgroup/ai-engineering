"""Tests for capability matrix (spec-197 T-1)."""

from __future__ import annotations

from ai_engineering.surfaces.capability_matrix import (
    CAPABILITY_MATRIX,
    HostCapability,
    get_capability,
    get_unverified_hosts,
    get_verified_hosts,
)


class TestHostCapability:
    """HostCapability dataclass tests."""

    def test_to_dict(self):
        cap = HostCapability(
            host_id="test",
            skill_discovery_paths=[".test/skills"],
            skill_precedence="first-wins",
            invocation_syntax="/ai-*",
            agent_path=None,
            hook_mechanism="config",
            root_instruction_path=".test/AGENTS.md",
            user_only_policy=None,
            status="verified",
        )
        d = cap.to_dict()
        assert d["host_id"] == "test"
        assert d["status"] == "verified"


class TestCapabilityMatrix:
    """Capability matrix tests."""

    def test_all_hosts_have_capabilities(self):
        assert len(CAPABILITY_MATRIX) >= 6

    def test_claude_code_exists(self):
        cap = get_capability("claude-code")
        assert cap is not None
        assert cap.host_id == "claude-code"

    def test_codex_exists(self):
        cap = get_capability("codex")
        assert cap is not None
        assert cap.invocation_syntax == "$ai-*"

    def test_opencode_is_unverified(self):
        cap = get_capability("opencode")
        assert cap is not None
        assert cap.status == "unverified"

    def test_antigravity_is_unverified(self):
        cap = get_capability("antigravity")
        assert cap is not None
        assert cap.status == "unverified"

    def test_verified_hosts(self):
        verified = get_verified_hosts()
        assert len(verified) >= 2
        host_ids = {h.host_id for h in verified}
        assert "claude-code" in host_ids

    def test_unverified_hosts(self):
        unverified = get_unverified_hosts()
        assert len(unverified) >= 2
        host_ids = {h.host_id for h in unverified}
        assert "opencode" in host_ids

    def test_unknown_host_returns_none(self):
        assert get_capability("nonexistent") is None

    def test_single_root_per_host(self):
        """Each host should have exactly one root instruction path."""
        for cap in CAPABILITY_MATRIX:
            assert cap.root_instruction_path, f"{cap.host_id} missing root path"
