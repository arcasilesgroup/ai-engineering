"""Canonical mirror parity — spec-131 S1 acceptance gate (sub-001 T-1.8).

This integration test pins two invariants that the refactor in T-1.7
introduced:

1. **Byte equivalence (D-131-03).** After stripping the
   ``<!-- ide-extras:start -->…<!-- ide-extras:end -->`` fence, the
   canonical payload bytes of ``<repo>/AGENTS.md``, ``<repo>/CLAUDE.md``,
   ``<repo>/GEMINI.md``, and ``<repo>/.github/copilot-instructions.md``
   share the same sha256. Drift in either generator surfaces here.

2. **Sync idempotency (R-1.4).** Running
   ``python scripts/sync_command_mirrors.py --check`` twice produces no
   diff the second time. Catches generator non-determinism (timestamps,
   sorted-iteration drift, etc.).

Both invariants are part of S1's acceptance gate; they back the
`md_mirror.py` lint surface added in T-1.9.
"""

from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SYNC_ENTRY = REPO_ROOT / "scripts" / "sync_command_mirrors.py"

_MIRRORS = (
    "AGENTS.md",
    "CLAUDE.md",
    "GEMINI.md",
    ".github/copilot-instructions.md",
)

_FENCE_RE = re.compile(
    r"<!-- ide-extras:start -->.*?<!-- ide-extras:end -->",
    re.DOTALL,
)


def _strip_ide_extras(text: str) -> str:
    """Strip every ide-extras fenced block from `text`."""
    return _FENCE_RE.sub("", text)


def _sha256_of_payload(path: Path) -> str:
    body = path.read_text(encoding="utf-8")
    return hashlib.sha256(_strip_ide_extras(body).encode("utf-8")).hexdigest()


@pytest.mark.integration
def test_canonical_payload_bytes_are_identical() -> None:
    """All four mirrors share identical canonical-payload sha256 (D-131-03)."""
    hashes = {p: _sha256_of_payload(REPO_ROOT / p) for p in _MIRRORS}
    distinct = set(hashes.values())
    assert len(distinct) == 1, (
        "spec-131 D-131-03: four mirrors must share canonical payload; got\n  "
        + "\n  ".join(f"{p}: {h[:16]}" for p, h in hashes.items())
    )


@pytest.mark.integration
def test_no_agents_md_import_in_any_mirror() -> None:
    """No mirror contains the bare `@AGENTS.md` import directive (D-131-03).

    The string `@AGENTS.md` may appear inside the §14 authoring contract
    table (describing what each file must NOT contain). A real import
    directive is a bare line containing only `@AGENTS.md` (no backticks,
    no surrounding prose).
    """
    import_re = re.compile(r"^\s*@AGENTS\.md\s*$", re.MULTILINE)
    offenders: list[str] = []
    for rel in _MIRRORS:
        text = (REPO_ROOT / rel).read_text(encoding="utf-8")
        if import_re.search(text):
            offenders.append(rel)
    assert not offenders, f"@AGENTS.md import forbidden; offenders: {offenders}"


@pytest.mark.integration
def test_no_gemini_orphan_on_disk() -> None:
    """`.gemini/GEMINI.md` is DELETED per D-131-03 — must not exist."""
    orphan = REPO_ROOT / ".gemini" / "GEMINI.md"
    assert not orphan.exists(), (
        f"D-131-03 deletes {orphan} — Gemini CLI never reads in-repo `.gemini/`"
    )


@pytest.mark.integration
def test_no_codex_agents_orphan_on_disk() -> None:
    """`.codex/AGENTS.md` must not exist — Codex reads root AGENTS.md."""
    orphan = REPO_ROOT / ".codex" / "AGENTS.md"
    assert not orphan.exists(), f"Codex reads root AGENTS.md natively — {orphan} would shadow it"


@pytest.mark.integration
def test_copilot_instructions_has_no_cross_reference_line() -> None:
    """copilot-instructions.md no longer references AGENTS.md (D-131-14)."""
    copilot = (REPO_ROOT / ".github" / "copilot-instructions.md").read_text(encoding="utf-8")
    assert "See [AGENTS.md](../AGENTS.md)" not in copilot, (
        "D-131-14: cross-ref line at core.py:1103 is REMOVED; every mirror is self-contained"
    )


@pytest.mark.integration
def test_sync_check_is_idempotent_on_fresh_tree() -> None:
    """Running `sync_command_mirrors.py --check` twice produces zero diffs.

    R-1.4 mitigation: catches generator non-determinism (timestamp drift,
    unsorted iteration). The first invocation establishes the baseline;
    the second must report "All N mirror files in sync. No changes." and
    exit 0.
    """
    # First pass — current tree must already be clean (T-1.7 sync materialised it).
    first = subprocess.run(
        [sys.executable, str(SYNC_ENTRY), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert first.returncode == 0, (
        f"first --check pass failed (exit={first.returncode}); stderr=\n{first.stderr}"
    )
    assert "in sync" in first.stdout or "No changes" in first.stdout, (
        f"first --check missing 'in sync' confirmation; stdout=\n{first.stdout}"
    )
    # Second pass — idempotency guarantee.
    second = subprocess.run(
        [sys.executable, str(SYNC_ENTRY), "--check"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert second.returncode == 0, (
        f"second --check pass reported drift (exit={second.returncode}); stdout=\n{second.stdout}"
    )
    assert second.stdout.strip() == first.stdout.strip(), (
        "R-1.4: --check stdout differs between two consecutive runs; "
        f"first:\n{first.stdout}\nsecond:\n{second.stdout}"
    )


@pytest.mark.integration
def test_canonical_payload_carries_section_10_principles() -> None:
    """The canonical body cites §10.1-§10.8 anchors (CANONICAL.md §10)."""
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    for anchor in ("§10.1", "§10.5", "§10.8"):
        assert anchor in agents, (
            f"canonical payload must declare engineering principle {anchor}; see CANONICAL.md §10"
        )


@pytest.mark.integration
def test_constitution_has_no_forbidden_ai_behaviour_headers() -> None:
    """CONSTITUTION.md is rescoped to project-identity-only (D-131-04)."""
    constitution = (REPO_ROOT / "CONSTITUTION.md").read_text(encoding="utf-8")
    forbidden = (
        "Simplicity First",
        "Plan-Mode Default",
        "Surgical Changes",
        "Goal-Driven Execution",
        "Subagent Strategy",
        "Self-Improvement Loop",
        "Demand Elegance",
        "Autonomous Bug Fixing",
        "KISS",
        "YAGNI",
        "SOLID",
        "DRY",
        "TDD",
        "SDD",
        "Clean Code",
        "Hexagonal Architecture",
        "Think Before Coding",
    )
    offenders = [
        h for h in forbidden if re.search(rf"^##\s+{re.escape(h)}\b", constitution, re.MULTILINE)
    ]
    assert not offenders, (
        f"D-131-04: CONSTITUTION.md must NOT contain AI-behaviour headers; got {offenders}"
    )
