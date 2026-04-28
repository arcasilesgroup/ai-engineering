"""RED skeleton for spec-107 G-4 (Phase 3) — Copilot Explorer rename.

Spec-107 D-107-03 renames `.github/agents/explore.agent.md` to
`.github/agents/ai-explore.agent.md`, updates the front-matter
`name: ai-explore`, and ships a new chatmode alias
`.github/chatmodes/ai-explore.chatmode.md` so Copilot users get parity
with Claude / Codex / Gemini (`@ai-explore` and `/ai-explore`).

`scripts/sync_command_mirrors.py` `AGENT_METADATA["explore"]["name"]`
must change from `"Explorer"` to `"ai-explore"` so every IDE mirror
regenerates with the canonical slug.

These tests are marked ``spec_107_red`` and excluded from CI default
runs until Phase 3 lands the GREEN implementation. They are the
acceptance contract for T-3.1 / T-3.2 / T-3.3.
"""

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
GITHUB_AGENTS_DIR = REPO_ROOT / ".github" / "agents"
CHATMODES_DIR = REPO_ROOT / ".github" / "chatmodes"


@pytest.mark.spec_107_red
def test_renamed_agent_file_exists() -> None:
    """G-4: `.github/agents/ai-explore.agent.md` must exist post-rename."""
    renamed = GITHUB_AGENTS_DIR / "ai-explore.agent.md"
    assert renamed.is_file(), (
        f"renamed agent file missing: {renamed} — Phase 3 T-3.1 must rename "
        "explore.agent.md to ai-explore.agent.md"
    )


@pytest.mark.spec_107_red
def test_legacy_agent_file_removed() -> None:
    """G-4: legacy `.github/agents/explore.agent.md` must NOT linger."""
    legacy = GITHUB_AGENTS_DIR / "explore.agent.md"
    assert not legacy.exists(), (
        f"legacy agent file still present: {legacy} — Phase 3 T-3.1 must "
        "delete the original after renaming"
    )


@pytest.mark.spec_107_red
def test_renamed_agent_front_matter_name() -> None:
    """G-4: front-matter `name:` must equal canonical slug `ai-explore`."""
    renamed = GITHUB_AGENTS_DIR / "ai-explore.agent.md"
    assert renamed.is_file(), "preconditions: agent file must exist first"
    text = renamed.read_text(encoding="utf-8")
    # Look for `name: ai-explore` or `name: "ai-explore"` in front-matter.
    assert ("name: ai-explore" in text) or ('name: "ai-explore"' in text), (
        f"front-matter `name:` not set to canonical `ai-explore` in {renamed}. "
        "Spec-107 D-107-03 requires the slug to be ai-explore for cross-IDE "
        "parity (Claude / Codex / Gemini already use ai-explore)."
    )


@pytest.mark.spec_107_red
def test_chatmode_alias_exists() -> None:
    """G-4: `.github/chatmodes/ai-explore.chatmode.md` provides slash alias."""
    chatmode = CHATMODES_DIR / "ai-explore.chatmode.md"
    assert chatmode.is_file(), (
        f"chatmode alias missing: {chatmode} — Phase 3 T-3.3 must create "
        "this file so Copilot users can invoke `/ai-explore` Claude-style"
    )


@pytest.mark.spec_107_red
def test_sync_metadata_canonical_name() -> None:
    """G-4: `AGENT_METADATA["explore"]["name"]` is `ai-explore`, not Explorer."""
    sync_script = REPO_ROOT / "scripts" / "sync_command_mirrors.py"
    assert sync_script.is_file(), f"sync script missing: {sync_script}; cannot validate metadata"
    text = sync_script.read_text(encoding="utf-8")
    # Crude but reliable: the canonical name string must appear at least
    # once near the explore entry, and the legacy "Explorer" label must
    # not be the active value.
    assert '"ai-explore"' in text, (
        "canonical name `ai-explore` not present in AGENT_METADATA; "
        "Phase 3 T-3.2 must update the metadata table"
    )
