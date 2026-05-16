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
    """§10.x anchors live in `.ai-engineering/reference/principles.md`.

    spec-134 D-134-05 / sub-005 mirror diet + spec-136 D-136-04:
    §10 Engineering Principles live in the canonical reference home;
    the four IDE mirrors carry pointer rows only. The chain
    `AGENTS.md → .ai-engineering/reference/principles.md` resolves;
    the §10.1/§10.5/§10.8 anchors that 76 skill/agent files cite
    survive at the new home.
    """
    rel = ".ai-engineering/reference/principles.md"
    principles_doc = REPO_ROOT / ".ai-engineering" / "reference" / "principles.md"
    assert principles_doc.is_file(), (
        f"{rel} MUST exist as the canonical home for §10 anchors "
        "(sub-005 extracts §10 prose out of mirrors)"
    )
    principles_text = principles_doc.read_text(encoding="utf-8")
    for anchor in ("§10.1", "§10.5", "§10.8"):
        assert anchor in principles_text, (
            f"{rel} must declare engineering-principle anchor {anchor}"
        )
    agents = (REPO_ROOT / "AGENTS.md").read_text(encoding="utf-8")
    assert rel in agents, (
        "AGENTS.md (canonical payload) must carry a pointer line referencing "
        f"{rel} so consumers can locate §10.x anchors"
    )


# Headings of the four sections extracted to `docs/` by sub-005. The
# match anchors `^…$` (MULTILINE) so a pointer-stub heading that adds
# a suffix (e.g. `## 10. Engineering Principles (pointer)`) is
# correctly distinguished from the verbatim extracted heading.
_EXTRACTED_HEADING_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"^## 10\. Engineering Principles\s*$", re.MULTILINE),
    re.compile(r"^## 14\. Strict Content Contracts\b.*$", re.MULTILINE),
    re.compile(r"^## 15\. IDE-Extras Escape Hatch\b.*$", re.MULTILINE),
    re.compile(r"^## 16\. Surface Axioms\b.*$", re.MULTILINE),
)


@pytest.mark.integration
def test_canonical_payload_extracts_principles_and_axioms_to_docs() -> None:
    """sub-005 mirror diet contract: §10 / §14 / §15 / §16 live in docs/.

    After spec-134 sub-005 ships, the four IDE mirrors carry pointer
    rows only — the verbatim prose lives in:

    - `.ai-engineering/reference/principles.md` (§10 §10.1-§10.8)
    - `.ai-engineering/reference/mirror-authoring.md` (§14 + §15)
    - `.ai-engineering/reference/surface-axioms.md` (§16 A1 / A2)

    This test pins the extraction contract end-to-end so the lint
    surface (`tools/skill_lint/checks/md_mirror.py` sub-checks 6 + 7)
    has a matching integration-level guard.
    """
    # (a) .ai-engineering/reference/principles.md exists and carries §10.1..§10.8 anchors.
    principles_doc = REPO_ROOT / ".ai-engineering" / "reference" / "principles.md"
    assert principles_doc.is_file(), (
        f"missing canonical home: {principles_doc.relative_to(REPO_ROOT)}"
    )
    principles_text = principles_doc.read_text(encoding="utf-8")
    rel_principles = ".ai-engineering/reference/principles.md"
    for n in range(1, 9):
        anchor = f"§10.{n}"
        assert anchor in principles_text, (
            f"{rel_principles} must carry anchor {anchor} (sub-005 lossless migration)"
        )

    # (b) reference/mirror-authoring.md exists and carries the authoring table.
    authoring_doc = REPO_ROOT / ".ai-engineering" / "reference" / "mirror-authoring.md"
    assert authoring_doc.is_file(), (
        f"missing canonical home: {authoring_doc.relative_to(REPO_ROOT)}"
    )
    authoring_text = authoring_doc.read_text(encoding="utf-8")
    assert "MUST contain" in authoring_text and "MUST NOT contain" in authoring_text, (
        ".ai-engineering/reference/mirror-authoring.md must preserve the per-file authoring table "
        "(MUST contain / MUST NOT contain columns)"
    )

    # (c) .ai-engineering/reference/surface-axioms.md exists and carries A1 / A2 headers.
    axioms_doc = REPO_ROOT / ".ai-engineering" / "reference" / "surface-axioms.md"
    assert axioms_doc.is_file(), f"missing canonical home: {axioms_doc.relative_to(REPO_ROOT)}"
    axioms_text = axioms_doc.read_text(encoding="utf-8")
    assert "A1 — Surface Axiom" in axioms_text, (
        ".ai-engineering/reference/surface-axioms.md must carry the A1 Surface Axiom heading"
    )
    assert "A2 — No-Twin Axiom" in axioms_text, (
        ".ai-engineering/reference/surface-axioms.md must carry the A2 No-Twin Axiom heading"
    )

    # (d) NONE of the four root mirrors carry the extracted section
    # headings VERBATIM. Pointer stubs that adopt a distinct heading
    # (e.g. `## 10. Engineering Principles (pointer)`) are allowed
    # because they signal the new home and do NOT carry the
    # extracted prose.
    offenders: list[tuple[str, str]] = []
    for rel in _MIRRORS:
        body = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for pattern in _EXTRACTED_HEADING_PATTERNS:
            match = pattern.search(body)
            if match is not None:
                offenders.append((rel, match.group(0)))
    assert not offenders, (
        "sub-005 contract: mirrors must not carry extracted section prose; offenders:\n  "
        + "\n  ".join(f"{rel}: {h}" for rel, h in offenders)
    )

    # (e) every mirror carries pointer lines back to the three docs/ destinations.
    for rel in _MIRRORS:
        body = (REPO_ROOT / rel).read_text(encoding="utf-8")
        for target in (
            ".ai-engineering/reference/principles.md",
            ".ai-engineering/reference/mirror-authoring.md",
            ".ai-engineering/reference/surface-axioms.md",
        ):
            assert target in body, (
                f"{rel} must carry a pointer line referencing {target} (sub-005 mirror diet)"
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
