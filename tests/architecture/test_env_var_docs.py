"""spec-147 G2 / D-147-08 — every hook-read env var is documented.

Completeness guard: every ``AIENG_*`` / ``AIE_*`` environment variable
that a hook script READS must appear by name in the CLAUDE.md
"Runtime Layer Tunables" fenced block. An undocumented behavior-changing
flag is a silent trap — most dangerously ``AIE_MCP_HEALTH_FAIL_OPEN``,
which flips a blocking gate to pass-through. This complements
``test_tunables_docs_match_code.py`` (which checks that documented
*defaults* match code); this test checks *presence/coverage*.

Plain ``assert`` style, no fixtures — mirrors
``tests/unit/hooks/test_canonical_events_count.py``.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOKS_DIR = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks"
CLAUDE_MD = REPO_ROOT / "CLAUDE.md"

# Reads only: ``os.environ.get("X")``, ``os.getenv("X")``, ``os.environ["X"]``.
# Dict-literal *writes* (e.g. ``{**os.environ, "X": "v"}``) are intentionally
# NOT matched — they set a var for a subprocess, they do not read framework
# config — so they never create a documentation obligation.
_READ_RE = re.compile(
    r"""(?:os\.environ\.get|os\.getenv)\(\s*["'](AIENG_[A-Z0-9_]+|AIE_[A-Z0-9_]+)["']"""
    r"""|os\.environ\[\s*["'](AIENG_[A-Z0-9_]+|AIE_[A-Z0-9_]+)["']\]"""
)

# Intentionally-undocumented reads (dynamic per-server MCP keys whose names
# are constructed at runtime, not literal config knobs). Keep this empty for
# literal vars — a literal hook-read var belongs in the tunables table.
_ALLOWLIST: frozenset[str] = frozenset()


def _hook_read_env_vars() -> set[str]:
    found: set[str] = set()
    for path in HOOKS_DIR.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for match in _READ_RE.finditer(text):
            name = match.group(1) or match.group(2)
            if name:
                found.add(name)
    return found


def _tunables_block() -> str:
    text = CLAUDE_MD.read_text(encoding="utf-8")
    marker = "## Runtime Layer Tunables"
    assert marker in text, "CLAUDE.md missing the Runtime Layer Tunables section"
    after = text.split(marker, 1)[1]
    fence_open = after.find("```")
    assert fence_open != -1, "Tunables section missing opening code fence"
    fence_close = after.find("```", fence_open + 3)
    assert fence_close != -1, "Tunables section missing closing code fence"
    return after[fence_open + 3 : fence_close]


def test_every_hook_read_env_var_is_documented() -> None:
    """Each AIENG_*/AIE_* var a hook reads must be named in the tunables block."""
    documented = _tunables_block()
    read_vars = _hook_read_env_vars() - _ALLOWLIST
    assert read_vars, "expected to find hook env-var reads; grep regex may have broken"

    missing = sorted(
        name for name in read_vars if not re.search(rf"\b{re.escape(name)}\b", documented)
    )
    assert not missing, (
        "Hook-read env vars missing from CLAUDE.md Runtime Layer Tunables: "
        f"{missing}. Document them in scripts/sync_mirrors/core.py `_CLAUDE_EXTRAS` "
        "and regenerate mirrors (`uv run python -m scripts.sync_mirrors`)."
    )


def test_fail_open_flag_is_documented_with_risk_note() -> None:
    """The MCP health fail-open flag must carry a visible risk annotation."""
    block = _tunables_block()
    assert "AIE_MCP_HEALTH_FAIL_OPEN" in block, "AIE_MCP_HEALTH_FAIL_OPEN must be documented"
    # The line for it must flag the security risk so operators are warned.
    line = next(ln for ln in block.splitlines() if "AIE_MCP_HEALTH_FAIL_OPEN" in ln)
    assert "RISK" in line.upper(), (
        "AIE_MCP_HEALTH_FAIL_OPEN documentation must flag the security risk "
        "(it disables a blocking gate)."
    )
