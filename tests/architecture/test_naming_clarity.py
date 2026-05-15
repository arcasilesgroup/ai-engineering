"""Naming clarity enforcement (spec-134 D-134-06).

The D-134-06 hard-rename wave eliminates ambiguous skill and agent
names. Once the wave lands, the old slugs MUST NOT appear on disk
under the canonical ``.claude/`` tree.

This file is the single mechanical guard for naming drift:

1. No deprecated skill directory survives under ``.claude/skills/``.
2. No deprecated agent file survives under ``.claude/agents/``.
3. Every specialist agent under ``.claude/agents/`` uses one of the
   canonical family prefixes (``reviewer-``, ``verifier-``,
   ``review-``, ``verify-``). The mixed-prefix legacy is gone.
4. Every renamed target file exists at its new path so the rename is
   complete, not partial.

The test reads ``.claude/`` directly — no manifest lookup, no DB
query — satisfying D-134-10 (no decisions-table dependency).
"""

from __future__ import annotations

from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_SKILLS = _REPO_ROOT / ".claude" / "skills"
_CANONICAL_AGENTS = _REPO_ROOT / ".claude" / "agents"

# Skills that must NOT exist after D-134-06.
_DEPRECATED_SKILLS: tuple[str, ...] = (
    "ai-gtm",
    "ai-eval",
    "ai-guide",
    "ai-observe",
    "ai-create",
    "ai-cleanup",
    "ai-write",
    "ai-prompt",
)

# Agent files that must NOT exist after D-134-06.
_DEPRECATED_AGENTS: tuple[str, ...] = (
    "ai-guard.md",
    "ai-guide.md",
    "verify-deterministic.md",
    "reviewer-context.md",
    "reviewer-validator.md",
)

# Skills that MUST exist at the new path after D-134-06.
_RENAMED_SKILLS: tuple[str, ...] = (
    "ai-marketing",
    "ai-reliability-eval",
    "ai-onboard",
    "ai-session-watch",
    "ai-scaffold",
    "ai-repo-tidy",
    "ai-prose",
    "ai-prompt-tune",
)

# Agent files that MUST exist at the new path after D-134-06.
_RENAMED_AGENTS: tuple[str, ...] = (
    "ai-advise.md",
    "ai-onboard.md",
    "verifier-deterministic.md",
    "review-context.md",
    "review-validator.md",
)

# Canonical specialist-agent family prefixes. Every specialist agent
# (i.e., every agent file whose name does NOT start with ``ai-``)
# under ``.claude/agents/`` MUST match one of these prefixes.
_FAMILY_PREFIXES: tuple[str, ...] = (
    "reviewer-",
    "verifier-",
    "review-",
    "verify-",
)


@pytest.mark.unit
def test_no_deprecated_skill_directories() -> None:
    """No skill directory under ``.claude/skills/`` uses a deprecated slug."""
    survivors = sorted(slug for slug in _DEPRECATED_SKILLS if (_CANONICAL_SKILLS / slug).is_dir())
    assert not survivors, (
        "Deprecated skill directories still present under "
        f"{_CANONICAL_SKILLS}:\n  - "
        + "\n  - ".join(survivors)
        + "\nD-134-06 rename wave is incomplete. Run `git mv` and update "
        "DEFAULT_SKILLS_REGISTRY."
    )


@pytest.mark.unit
def test_no_deprecated_agent_files() -> None:
    """No agent file under ``.claude/agents/`` uses a deprecated name."""
    survivors = sorted(name for name in _DEPRECATED_AGENTS if (_CANONICAL_AGENTS / name).is_file())
    assert not survivors, (
        "Deprecated agent files still present under "
        f"{_CANONICAL_AGENTS}:\n  - "
        + "\n  - ".join(survivors)
        + "\nD-134-06 rename wave is incomplete. Run `git mv` and update "
        "_AGENT_ALIASES / _AGENT_TOPOLOGY / _AGENT_MUTATIONS / "
        "_AGENT_WRITE_SCOPES in state/capabilities.py."
    )


@pytest.mark.unit
def test_specialist_agents_use_canonical_family_prefix() -> None:
    """Every specialist agent must match a canonical family prefix."""
    if not _CANONICAL_AGENTS.is_dir():
        pytest.skip(f"{_CANONICAL_AGENTS} missing")
    offenders: list[str] = []
    for child in sorted(_CANONICAL_AGENTS.iterdir()):
        if not child.is_file() or child.suffix != ".md":
            continue
        stem = child.stem
        if stem.startswith("ai-"):
            continue  # first-class agent
        if not any(stem.startswith(prefix) for prefix in _FAMILY_PREFIXES):
            offenders.append(child.name)
    assert not offenders, (
        "Specialist agents with non-canonical prefix "
        f"(allowed: {_FAMILY_PREFIXES}):\n  - " + "\n  - ".join(offenders)
    )


@pytest.mark.unit
def test_renamed_skill_directories_exist() -> None:
    """Every renamed skill must exist at its new canonical path."""
    missing = sorted(
        slug for slug in _RENAMED_SKILLS if not (_CANONICAL_SKILLS / slug / "SKILL.md").is_file()
    )
    assert not missing, (
        "Renamed skills missing from canonical tree "
        f"(expected under {_CANONICAL_SKILLS}):\n  - " + "\n  - ".join(missing)
    )


@pytest.mark.unit
def test_renamed_agent_files_exist() -> None:
    """Every renamed agent must exist at its new canonical path."""
    missing = sorted(name for name in _RENAMED_AGENTS if not (_CANONICAL_AGENTS / name).is_file())
    assert not missing, (
        "Renamed agents missing from canonical tree "
        f"(expected under {_CANONICAL_AGENTS}):\n  - " + "\n  - ".join(missing)
    )
