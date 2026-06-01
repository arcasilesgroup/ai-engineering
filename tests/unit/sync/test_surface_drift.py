"""Fail-loud surface-drift guard for sync_mirrors (spec-159 T-2 / D-159-08).

The framework keeps a canonical authoring copy of every installable surface
at the repo root and a packaged install-template copy under
``src/ai_engineering/templates/``. ``scripts/sync_mirrors/core.py`` is the
generation pipeline that must keep template == canonical.

Before spec-159 three surface classes drifted *invisibly* because the
pipeline had no sync step (or generated the wrong content) for them:

1. ``.ai-engineering/scripts/hooks/**/*.py`` (incl. ``_lib/``) had no sync
   step at all -- 16 files perpetually drifted (D-159-04).
2. ``generate_specialist_agent`` injected provenance frontmatter into the
   ``.claude/agents/*`` install template that the canonical source lacks,
   guaranteeing a permanent byte mismatch (D-159-05).

This module asserts byte-parity for those framework-managed surfaces *and*
that ``sync_all(check_only=True)`` reports clean. It is the fail-loud signal:
any future surface edit that is not propagated into the install template
turns this red, naming ``python scripts/sync_mirrors/core.py`` as the remedy.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_REMEDY = "run: python scripts/sync_mirrors/core.py"


def test_sync_all_check_mode_reports_clean() -> None:
    """``sync_all(check_only=True)`` must exit 0 -- no tracked drift."""
    from scripts.sync_command_mirrors import sync_all

    exit_code = sync_all(check_only=True)
    assert exit_code == 0, f"Mirror drift detected -- {_REMEDY}"


def test_hook_scripts_template_matches_canonical() -> None:
    """Every canonical hook ``.py`` (incl. ``_lib/``) is byte-identical in template."""
    from scripts.sync_command_mirrors import ROOT

    canonical_root = ROOT / ".ai-engineering" / "scripts" / "hooks"
    template_root = (
        ROOT / "src" / "ai_engineering" / "templates" / ".ai-engineering" / "scripts" / "hooks"
    )

    drifted: list[str] = []
    for src_file in sorted(canonical_root.rglob("*.py")):
        if "__pycache__" in src_file.parts:
            continue
        relative = src_file.relative_to(canonical_root)
        tpl_file = template_root / relative
        if not tpl_file.exists():
            drifted.append(f"MISSING: {relative}")
            continue
        if src_file.read_bytes() != tpl_file.read_bytes():
            drifted.append(f"DRIFT: {relative}")

    assert not drifted, (
        f"Hook-script install templates drifted from canonical ({_REMEDY}):\n" + "\n".join(drifted)
    )


def test_specialist_agent_claude_template_is_verbatim() -> None:
    """``.claude/agents/*`` install templates are verbatim canonical copies.

    The native ``.claude`` authoring surface carries no provenance frontmatter;
    the install template must match it byte-for-byte (no injected
    ``mirror_family``/``generated_by``/``canonical_source``/``edit_policy``).
    """
    from scripts.sync_command_mirrors import (
        TPL_CLAUDE_AGENTS,
        discover_specialist_agents,
    )

    drifted: list[str] = []
    for specialist_path in discover_specialist_agents():
        tpl_file = TPL_CLAUDE_AGENTS / specialist_path.name
        if not tpl_file.exists():
            drifted.append(f"MISSING: {specialist_path.name}")
            continue
        if specialist_path.read_bytes() != tpl_file.read_bytes():
            drifted.append(f"DRIFT: {specialist_path.name}")

    assert not drifted, (
        f"Specialist-agent .claude install templates drifted from canonical "
        f"({_REMEDY}):\n" + "\n".join(drifted)
    )
