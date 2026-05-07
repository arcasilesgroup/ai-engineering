"""RED skeleton for spec-107 G-5 (Phase 3) — GEMINI.md count placeholders.

Spec-107 D-107-04 replaces hand-maintained skill/agent counts in
`templates/project/GEMINI.md` with `__SKILL_COUNT__` and
`__AGENT_COUNT__` placeholders. `scripts/sync_command_mirrors.py` adds
`write_gemini_md(canonical_skills, canonical_agents)` that materializes
the placeholders into actual numeric counts on every sync, so the
generated `.gemini/GEMINI.md` always matches disk reality.

These tests are marked ``spec_107_red`` and excluded from CI default
runs until Phase 3 lands the GREEN implementation. They are the
acceptance contract for T-3.4 / T-3.5.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GEMINI_TEMPLATE = REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / "GEMINI.md"
GEMINI_RENDERED = REPO_ROOT / ".gemini" / "GEMINI.md"


def test_template_uses_skill_count_placeholder() -> None:
    """G-5: template must contain `__SKILL_COUNT__` placeholder."""
    assert GEMINI_TEMPLATE.is_file(), f"template missing: {GEMINI_TEMPLATE}"
    text = GEMINI_TEMPLATE.read_text(encoding="utf-8")
    assert "__SKILL_COUNT__" in text, (
        "GEMINI.md template still hardcodes skill count — Phase 3 T-3.4 "
        "must replace `## Skills (44)` with `## Skills (__SKILL_COUNT__)`"
    )


def test_template_uses_agent_count_placeholder() -> None:
    """G-5: template must contain `__AGENT_COUNT__` placeholder."""
    assert GEMINI_TEMPLATE.is_file(), f"template missing: {GEMINI_TEMPLATE}"
    text = GEMINI_TEMPLATE.read_text(encoding="utf-8")
    assert "__AGENT_COUNT__" in text, (
        "GEMINI.md template missing `__AGENT_COUNT__` placeholder — "
        "Phase 3 T-3.4 must add the agent-count placeholder so the renderer "
        "stays in sync with disk reality"
    )


def test_template_no_hardcoded_counts() -> None:
    """G-5: template must NOT contain literal `## Skills (NN)` numeric headers."""
    assert GEMINI_TEMPLATE.is_file()
    text = GEMINI_TEMPLATE.read_text(encoding="utf-8")
    hardcoded_skill = re.search(r"^## Skills \(\d+\)", text, re.MULTILINE)
    assert hardcoded_skill is None, (
        f"hardcoded skill count survives in GEMINI.md template: "
        f"{hardcoded_skill.group(0)!r}; replace with `__SKILL_COUNT__`"
    )
    hardcoded_agents = re.search(r"^## Agents \(\d+\)", text, re.MULTILINE)
    assert hardcoded_agents is None, (
        f"hardcoded agent count survives in GEMINI.md template: "
        f"{hardcoded_agents.group(0)!r}; replace with `__AGENT_COUNT__`"
    )


def test_rendered_gemini_md_substitutes_placeholders() -> None:
    """G-5: post-sync `.gemini/GEMINI.md` shows numeric counts, not placeholders.

    Post sub-004 meta-cleanup, the rendered template references skill /
    agent counts inside the `Surface Pointers` table rather than as H2
    headings. The contract is unchanged — placeholders must be replaced
    with positive integers — but the matching pattern follows the new
    table layout.
    """
    assert GEMINI_RENDERED.is_file(), (
        f"rendered file missing: {GEMINI_RENDERED}; run `ai-eng sync` first"
    )
    text = GEMINI_RENDERED.read_text(encoding="utf-8")
    assert "__SKILL_COUNT__" not in text, (
        "rendered GEMINI.md still contains placeholder; sync renderer is "
        "not substituting __SKILL_COUNT__"
    )
    assert "__AGENT_COUNT__" not in text, (
        "rendered GEMINI.md still contains placeholder; sync renderer is "
        "not substituting __AGENT_COUNT__"
    )
    skill_match = re.search(r"Skills \((\d+)\)", text)
    agent_match = re.search(r"Agents \((\d+)\)", text)
    assert skill_match is not None, "rendered GEMINI.md missing canonical `Skills (N)` reference"
    assert agent_match is not None, "rendered GEMINI.md missing canonical `Agents (N)` reference"
    skill_count = int(skill_match.group(1))
    agent_count = int(agent_match.group(1))
    assert skill_count > 0, "rendered skill count must be a positive integer"
    assert agent_count > 0, "rendered agent count must be a positive integer"


def test_sync_script_exposes_write_gemini_md() -> None:
    """G-5: sync script must expose `write_gemini_md` rendering function.

    Post spec-122-d D-122-24, the implementation moved into
    `scripts/sync_mirrors/core.py`; the legacy `sync_command_mirrors.py`
    is a backwards-compat shim that re-exports from there. Either the
    canonical module or the shim re-export satisfies the contract.
    """
    canonical = REPO_ROOT / "scripts" / "sync_mirrors" / "core.py"
    shim = REPO_ROOT / "scripts" / "sync_command_mirrors.py"
    assert canonical.is_file() or shim.is_file()
    canonical_text = canonical.read_text(encoding="utf-8") if canonical.is_file() else ""
    shim_text = shim.read_text(encoding="utf-8") if shim.is_file() else ""
    assert (
        "def write_gemini_md(" in canonical_text
        or "def write_gemini_md(" in shim_text
        or "write_gemini_md" in shim_text  # shim re-exports via `from core import *`
    ), (
        "neither sync_mirrors/core.py nor sync_command_mirrors.py exposes "
        "`write_gemini_md` — Phase 3 T-3.5 wiring lost"
    )
