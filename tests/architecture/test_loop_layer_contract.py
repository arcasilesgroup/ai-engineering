"""Loop-layer content contract (spec-201 sub-006, D-201-14).

Pins four properties of the canonical skill prose that make the loop
layer executable on a host that has no subagent primitive:

1. Every dispatch-only skill carries an inline-fallback paragraph.
2. Every fallback line carries the registered gate phrase
   ``on a host without`` (``tools/skill_lint/checks/portability.py``
   ``_GATE_PHRASES``), so the sub-007 widening of ``_TOOL_LITERALS``
   cannot turn the fallback prose into a MAJOR finding and no
   allowlist entry is needed.
3. No dispatch-only skill contradicts its own fallback elsewhere in
   the same file — two conflicting instructions are worse than none
   (D-201-14 rationale).
4. The unbacked "isolated worktree" claim is absent from every tracked
   file outside the spec record.

Roster note (sub-006 Risk 1): ``spec.md:41-43``, ``spec.md:319``
(D-201-14) and the parent plan's T-22 all say *five* skills lack a
fallback and *nine* dispatch. The tree says **six and ten** —
``ai-onboard`` is omitted from every one of those lists even though
``.claude/skills/ai-onboard/SKILL.md`` is the purest dispatch-only
wrapper in the fleet. The roster below is the corrected ten.

Reads ``.claude/skills/`` directly (canonical only) plus ``git grep``
for the tracked-tree sweep, so generated mirrors are covered by
property 4 without this test knowing the mirror layout.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_SKILLS = _REPO_ROOT / ".claude" / "skills"

# The registered gate phrase (portability.py `_GATE_PHRASES`). Every line of
# every fallback paragraph must carry it. Matched case-insensitively because
# `portability._has_gate` lowercases the line before testing membership.
GATE_PHRASE = "on a host without"

# The 10 dispatch-only skills: a subagent dispatch IS their execution path,
# so each needs an inline fallback to run at all on a host without the
# primitive. Six of these (autopilot, build, explore, onboard, plan, pr)
# had no fallback before spec-201 sub-006.
DISPATCH_ONLY_SKILLS: tuple[str, ...] = (
    "ai-advise",
    "ai-autopilot",
    "ai-build",
    "ai-explore",
    "ai-onboard",
    "ai-plan",
    "ai-pr",
    "ai-review",
    "ai-simplify",
    "ai-verify",
)

# Sentences that contradict a fallback paragraph in the same file.
CONTRADICTION_MARKERS: tuple[str, ...] = (
    "inline instead of dispatching",
    "never reads the agent file inline",
)

# The claim: no code anywhere creates a worktree for a build dispatch.
WORKTREE_CLAIM = "isolated worktree"

# The spec record documents the removal and must keep the phrase.
_CLAIM_ALLOWED_PREFIXES: tuple[str, ...] = (".ai-engineering/specs/",)


def _skill_path(name: str) -> Path:
    return _CANONICAL_SKILLS / name / "SKILL.md"


def _fallback_lines(text: str) -> list[str]:
    """Return every line that reads as an inline-fallback declaration."""
    return [line for line in text.splitlines() if "inline fallback" in line.lower()]


@pytest.mark.unit
def test_every_dispatch_only_skill_has_a_gated_inline_fallback() -> None:
    """Each of the 10 dispatch-only skills documents a host-neutral floor."""
    missing: list[str] = []
    ungated: list[str] = []
    for name in DISPATCH_ONLY_SKILLS:
        path = _skill_path(name)
        assert path.is_file(), f"{name}: canonical SKILL.md not found at {path}"
        lines = _fallback_lines(path.read_text(encoding="utf-8"))
        if not lines:
            missing.append(name)
            continue
        for line in lines:
            if GATE_PHRASE not in line.lower():
                ungated.append(f"{name}: {line.strip()[:120]}")

    assert not missing, (
        f"dispatch-only skills with no inline fallback ({len(missing)}): {sorted(missing)}"
    )
    assert not ungated, (
        "inline-fallback lines missing the registered gate phrase "
        f"{GATE_PHRASE!r} (portability.py _GATE_PHRASES): {ungated}"
    )


@pytest.mark.unit
def test_no_fallback_self_contradiction() -> None:
    """No dispatch-only skill forbids inline execution it elsewhere documents."""
    offenders: list[str] = []
    for name in DISPATCH_ONLY_SKILLS:
        path = _skill_path(name)
        if not path.is_file():
            continue
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            lowered = line.lower()
            for marker in CONTRADICTION_MARKERS:
                if marker in lowered:
                    offenders.append(f"{name}:{number} -> {marker!r}")

    assert not offenders, (
        "skills contradicting their own inline fallback (D-201-14: two conflicting "
        f"instructions are worse than none): {offenders}"
    )


@pytest.mark.unit
def test_no_unbacked_worktree_claim() -> None:
    """No tracked file outside the spec record claims worktree isolation."""
    proc = subprocess.run(
        ["git", "grep", "-l", WORKTREE_CLAIM],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    # git grep exits 1 with no output when there are no matches.
    assert proc.returncode in (0, 1), f"git grep failed: {proc.stderr}"
    hits = [line for line in proc.stdout.splitlines() if line.strip()]
    residual = [hit for hit in hits if not hit.startswith(_CLAIM_ALLOWED_PREFIXES)]
    assert not residual, (
        f"unbacked {WORKTREE_CLAIM!r} claim still present in {len(residual)} tracked "
        f"file(s) outside .ai-engineering/specs/: {residual}. The canonical source is "
        ".claude/skills/ai-build/SKILL.md frontmatter; edit it and run `ai-eng dev sync` "
        "rather than hand-editing the generated mirrors."
    )
