"""Integration tests for spec-104 D-104-04 — async parallel docs + pre-push.

RED phase for spec-104 T-5.1 (D-104-04 — async paralelo, sync, no
fire-and-forget).

Contract under test
-------------------
``/ai-pr`` step 6.5 (2 docs subagents) and step 7 (pre-push gate Wave 2)
must execute **simultaneously** so that the total wall-clock is
``max(docs_a1, docs_a2, prepush_w2)`` instead of the legacy
``sum(docs_a1, docs_a2, prepush_w2)``.  T-5.2 (GREEN) will rewrite the
narrative + Quick Reference of ``.claude/skills/ai-pr/SKILL.md`` to encode
this contract; these assertions are the spec contract that the rewrite
must satisfy.

The contract has 3 sub-clauses:

* Concurrency — step 6.5 mentions concurrent/parallel dispatch of BOTH
  docs subagents AND the pre-push gate (Wave 2).
* Wall-clock semantics — narrative documents
  ``max(docs, pre-push)`` not the legacy serial ``docs ➜ then ➜ pre-push``.
* Coherence preservation — fire-and-forget post-PR generation is
  explicitly rejected (no "commit docs after PR" follow-up). The 2-agent
  docs structure (CHANGELOG+README, docs-portal+quality-gate) is
  preserved. PR creation (``gh pr create`` / step 12) happens AFTER the
  concurrent block resolves.

Test methodology
----------------
These are markdown-content tests over the canonical skill source file:

    .claude/skills/ai-pr/SKILL.md

simply because spec-104 is a skill-narrative + agentic-dispatch change,
not a pure-Python change.  Tests use simple substring / regex assertions
against the file content and reject the legacy serial wording.

TDD CONSTRAINT
--------------
This file is IMMUTABLE after T-5.1 lands. T-5.2 (GREEN) may only edit the
SKILL.md narrative to satisfy the assertions — never the assertions
themselves. Per the framework Iron Law, weakening or modifying tests to
make implementation easier is forbidden.

Coverage (6 tests)
------------------
1. ``test_ai_pr_skill_step_65_documents_concurrent_dispatch`` — step 6.5
   mentions "concurrent" or "parallel" with respect to docs subagents
   AND pre-push gate (Wave 2).
2. ``test_ai_pr_skill_step_7_does_not_serialize_after_step_65`` — step 7
   isn't worded as "after step 6.5 completes"; instead carries the
   max-wall-clock semantic.
3. ``test_ai_pr_skill_total_wall_clock_max_not_sum`` — narrative includes
   ``max(docs, pre-push)`` (or equivalent phrasing) and rejects "serial
   sum" wording.
4. ``test_ai_pr_skill_no_follow_up_commit_for_docs`` — narrative does
   NOT propose "commit docs after PR" (rejecting the fire-and-forget
   alternative explicitly NG'd in spec-104 NG-7).
5. ``test_ai_pr_skill_step_65_dispatches_2_docs_subagents_in_parallel`` —
   preserves the existing 2-agent docs structure (CHANGELOG+README,
   docs-portal+quality-gate).
6. ``test_ai_pr_skill_step_8_pr_creation_after_max_wall`` — PR creation
   happens after the concurrent block resolves, not before; ordering
   invariant preserved.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Constants — canonical skill path; mirrors regenerate from this source
# via `uv run ai-eng sync` (spec-104 T-5.3) so the assertions only target
# the .claude/ canonical file.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AI_PR_SKILL_PATH = _REPO_ROOT / ".claude" / "skills" / "ai-pr" / "SKILL.md"


# ---------------------------------------------------------------------------
# Helpers — read canonical file, slice by step heading, normalise whitespace
# for substring matching.  All helpers are pure / deterministic so the
# 6 tests below stay simple substring/regex assertions per T-5.1 contract.
# ---------------------------------------------------------------------------


def _read_skill_text() -> str:
    """Return the canonical ``.claude/skills/ai-pr/SKILL.md`` text.

    Fails the test loudly if the file is missing — the skill is a hard
    dependency of ``/ai-pr`` and must always exist on disk.
    """

    assert _AI_PR_SKILL_PATH.is_file(), (
        f"canonical ai-pr SKILL.md not found at {_AI_PR_SKILL_PATH}; "
        "spec-104 T-5.1 cannot validate D-104-04 without the source"
    )
    return _AI_PR_SKILL_PATH.read_text(encoding="utf-8")


def _slice_section(text: str, start_heading_pattern: str, end_heading_pattern: str) -> str:
    """Return the substring of ``text`` between two heading regexes.

    The match is line-anchored (``re.MULTILINE``) and case-sensitive. If
    ``start_heading_pattern`` does not match, returns an empty string so
    the caller can assert on emptiness with a clear message.
    """

    start = re.search(start_heading_pattern, text, flags=re.MULTILINE)
    if start is None:
        return ""
    end = re.search(end_heading_pattern, text[start.end() :], flags=re.MULTILINE)
    if end is None:
        return text[start.end() :]
    return text[start.end() : start.end() + end.start()]


def _normalise(text: str) -> str:
    """Collapse whitespace for substring matching robust to wrapping.

    Lower-cases so assertions can match either casing variant of phrases
    like "Concurrent" / "concurrent".  Preserves order of words so the
    sequence-sensitive assertions (max-not-sum, after concurrent block)
    remain meaningful.
    """

    return re.sub(r"\s+", " ", text).strip().lower()


# ---------------------------------------------------------------------------
# Phrase fragments — kept here so each test reads as a small assertion,
# and so a future maintainer can audit the contract surface in one place.
# Per TDD CONSTRAINT, do NOT relax these — instead, evolve the SKILL.md
# narrative to satisfy them.
# ---------------------------------------------------------------------------

# Concurrency vocabulary that the rewritten step 6.5 must use.
_CONCURRENT_TERMS = ("concurrent", "in parallel", "parallel", "simultaneous")

# Wall-clock vocabulary signalling the max(docs, pre-push) contract.
_MAX_WALL_CLOCK_PATTERNS = (
    r"max\s*\(\s*docs\s*,\s*pre[\s-]?push\s*\)",
    r"max\s*\(\s*pre[\s-]?push\s*,\s*docs\s*\)",
    r"max\s+of\s+docs\s+and\s+pre[\s-]?push",
    r"wall[\s-]?clock\s*=\s*max",
    r"max\s+wall[\s-]?clock",
)

# Wording that would indicate a forbidden fire-and-forget post-PR commit.
_FIRE_AND_FORGET_TERMS = (
    "commit docs after pr",
    "commit docs after the pr",
    "follow-up commit for docs",
    "follow up commit for docs",
    "post-pr docs commit",
    "post pr docs commit",
)

# Markers that the step 6.5 narrative still references the 2 docs agents.
_DOCS_AGENT_MARKERS = (
    ("changelog", "readme"),
    ("docs-portal", "quality-gate"),
)

# Markers that step 7 used to be the sequential "after 6.5" trigger
# (the LEGACY phrasing the rewrite must remove). If any of these phrases
# survive, step 7 still serialises and D-104-04 is not satisfied.
_LEGACY_SERIAL_PHRASES = (
    "after step 6.5 completes",
    "after step 6.5 finishes",
    "once step 6.5 has completed",
    "once step 6.5 is complete",
    "after the documentation subagents finish",
    "after the documentation subagents complete",
    "after the docs subagents finish",
    "after the docs subagents complete",
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_ai_pr_skill_step_65_documents_concurrent_dispatch() -> None:
    """Step 6.5 must declare concurrent dispatch of docs AND pre-push.

    The D-104-04 contract requires step 6.5 narrative to reference both
    the documentation subagents AND the pre-push gate (Wave 2) and to
    state that they run concurrently.  A version that only mentions
    "parallel docs subagents" without joining them to the pre-push gate
    leaves Wave 2 serial and fails the contract.
    """

    text = _read_skill_text()
    section = _slice_section(text, r"^###\s+6\.5", r"^###\s+\d")
    assert section, "ai-pr SKILL.md is missing the '### 6.5' section heading"

    normalised = _normalise(section)

    # At least one concurrency term must be present in step 6.5.
    assert any(term in normalised for term in _CONCURRENT_TERMS), (
        f"step 6.5 must reference concurrent/parallel dispatch (one of "
        f"{list(_CONCURRENT_TERMS)!r}); got:\n{section}"
    )

    # The narrative must join the docs subagents to the pre-push gate so
    # both lanes are in the concurrent block. Without this, only the docs
    # are parallelised and Wave 2 still runs after them.
    assert "pre-push" in normalised or "pre push" in normalised or "wave 2" in normalised, (
        "step 6.5 must mention the pre-push gate / Wave 2 alongside the "
        "docs subagents to encode the D-104-04 concurrent block; got:\n" + section
    )

    # And must reference docs subagents in the same section.
    assert "docs" in normalised, (
        "step 6.5 must reference the docs subagents inside the same "
        "concurrent dispatch block; got:\n" + section
    )


def test_ai_pr_skill_step_7_does_not_serialize_after_step_65() -> None:
    """Step 7 must NOT carry the legacy 'after step 6.5 completes' wording.

    Under D-104-04 step 7 (pre-push gate / Wave 2) is dispatched
    concurrently with step 6.5 — the surviving narrative must reflect
    max-wall-clock semantics, not the serial trigger phrasing.
    """

    text = _read_skill_text()
    section = _slice_section(text, r"^###\s+7\.", r"^###\s+\d")
    assert section, "ai-pr SKILL.md is missing the '### 7.' section heading"

    normalised = _normalise(section)

    # No legacy serial-trigger phrase may survive in step 7.
    leaks = [phrase for phrase in _LEGACY_SERIAL_PHRASES if phrase in normalised]
    assert not leaks, (
        "step 7 still uses legacy serial-trigger wording "
        f"({leaks!r}); D-104-04 requires concurrent dispatch with step 6.5; "
        "rewrite step 7 to reference the max-wall-clock concurrent block. "
        f"section text:\n{section}"
    )

    # Step 7 must reference the concurrent dispatch / max wall-clock
    # semantic explicitly so a casual reader cannot mistake it for serial.
    has_concurrency_signal = any(term in normalised for term in _CONCURRENT_TERMS) or any(
        re.search(pat, normalised) for pat in _MAX_WALL_CLOCK_PATTERNS
    )
    assert has_concurrency_signal, (
        "step 7 must signal concurrency (one of "
        f"{list(_CONCURRENT_TERMS)!r}) or max-wall-clock phrasing; "
        f"got:\n{section}"
    )


def test_ai_pr_skill_total_wall_clock_max_not_sum() -> None:
    """Narrative must encode max(docs, pre-push), not legacy sum.

    D-104-04 commits to ``max(~30-60s docs, ~20-40s pre-push)`` ≈ 30-60s
    instead of ``~30-60 + 20-40 = 50-100s``.  At least one phrasing of
    the max contract must appear in the SKILL.md narrative; otherwise an
    agent reading the skill cannot infer concurrency from prose.
    """

    text = _read_skill_text()
    normalised = _normalise(text)

    matched = [pat for pat in _MAX_WALL_CLOCK_PATTERNS if re.search(pat, normalised)]
    assert matched, (
        "ai-pr SKILL.md must include max-wall-clock phrasing (one of "
        f"{list(_MAX_WALL_CLOCK_PATTERNS)!r}); D-104-04 requires the "
        "narrative to encode max(docs, pre-push) so the agent reads "
        "concurrency intent from prose."
    )


def test_ai_pr_skill_no_follow_up_commit_for_docs() -> None:
    """Narrative must NOT propose a fire-and-forget docs commit post-PR.

    spec-104 NG-7 explicitly rules out migrating docs to a follow-up
    commit after the PR (regulated audience prefers a clean history).
    The SKILL.md must keep docs in-tree with the PR body, generated
    inside the concurrent block of step 6.5.

    Two clauses — both must hold:

    * No fire-and-forget wording survives anywhere in the file.
    * Step 6.5 positively asserts the docs are staged BEFORE the PR is
      created (i.e., synchronously with the pre-push gate inside the
      concurrent block).  Without this positive assertion an agent could
      legitimately interpret the silence as "do whatever feels fastest"
      and regress to fire-and-forget.
    """

    text = _read_skill_text()
    normalised = _normalise(text)

    leaks = [phrase for phrase in _FIRE_AND_FORGET_TERMS if phrase in normalised]
    assert not leaks, (
        "ai-pr SKILL.md proposes a forbidden post-PR docs commit "
        f"({leaks!r}); spec-104 NG-7 explicitly rules this out — keep "
        "docs synchronous inside the concurrent block of step 6.5."
    )

    # Step 6.5 must positively state that docs are produced/staged
    # synchronously inside the concurrent block (i.e., before PR creation).
    section_65 = _slice_section(text, r"^###\s+6\.5", r"^###\s+\d")
    assert section_65, "ai-pr SKILL.md is missing the '### 6.5' section heading"
    normalised_65 = _normalise(section_65)

    sync_phrases = (
        "synchronously with the pre-push",
        "synchronous with the pre-push",
        "sync with the pre-push",
        "before pr creation",
        "before the pr is created",
        "before gh pr create",
        "before `gh pr create`",
        "staged before pr creation",
        "staged before the pr",
    )
    has_sync_signal = any(phrase in normalised_65 for phrase in sync_phrases)
    assert has_sync_signal, (
        "step 6.5 must positively assert docs are produced/staged "
        "synchronously with the pre-push gate (one of "
        f"{list(sync_phrases)!r}); without this guard, silence permits "
        "fire-and-forget post-PR commits which spec-104 NG-7 forbids. "
        f"section text:\n{section_65}"
    )


def test_ai_pr_skill_step_65_dispatches_2_docs_subagents_in_parallel() -> None:
    """Step 6.5 must keep the existing 2-agent docs split.

    D-104-04 keeps the 2 consolidated docs subagents (Agent 1 =
    CHANGELOG+README, Agent 2 = docs-portal+quality-gate) so the
    documentation lifecycle keeps its existing structure; only the
    *block* changes (concurrent with pre-push) — the *internal* split
    is preserved.  Removing either pair would silently regress the
    docs scope.
    """

    text = _read_skill_text()
    section = _slice_section(text, r"^###\s+6\.5", r"^###\s+\d")
    assert section, "ai-pr SKILL.md is missing the '### 6.5' section heading"

    normalised = _normalise(section)

    for left, right in _DOCS_AGENT_MARKERS:
        assert left in normalised and right in normalised, (
            f"step 6.5 must reference both '{left}' and '{right}' to "
            "preserve the 2-agent docs split mandated by D-104-04 / "
            "spec-104 NG-7; section text:\n" + section
        )

    # Sanity: the two pairs must coexist in step 6.5, not be split across
    # later sections (which would mean only one agent runs in the block).
    pair_a_present = (
        _DOCS_AGENT_MARKERS[0][0] in normalised and _DOCS_AGENT_MARKERS[0][1] in normalised
    )
    pair_b_present = (
        _DOCS_AGENT_MARKERS[1][0] in normalised and _DOCS_AGENT_MARKERS[1][1] in normalised
    )
    assert pair_a_present and pair_b_present, (
        "both docs agent pairs (CHANGELOG+README, docs-portal+quality-gate) "
        "must live inside the step 6.5 concurrent block to preserve "
        "the 2-agent split."
    )

    # The 2 agents must be described as running concurrently WITH the
    # pre-push gate (3-lane block: docs A1, docs A2, pre-push Wave 2),
    # not just as "2 docs agents in parallel" (the legacy phrasing).
    # We require an explicit reference to "3" lanes/tasks/agents OR a
    # phrasing that joins both docs and pre-push under one concurrent
    # block (covered by step 65 already mentioning pre-push under
    # _CONCURRENT_TERMS).
    three_lane_signals = (
        "3 concurrent",
        "3 parallel",
        "three concurrent",
        "three parallel",
        "3 lanes",
        "three lanes",
        "3 tasks in parallel",
        "three tasks in parallel",
        "docs a1",
        "docs a2",
        "docs agent 1",
        "docs agent 2",
        "agent 1, agent 2, and pre-push",
        "agent 1, agent 2 and pre-push",
        "concurrently with the pre-push",
        "in parallel with the pre-push",
        "alongside the pre-push",
    )
    has_three_lane = any(signal in normalised for signal in three_lane_signals)
    assert has_three_lane, (
        "step 6.5 must explicitly join the 2 docs subagents to the "
        "pre-push gate as a 3-lane concurrent block (one of "
        f"{list(three_lane_signals)!r}); without this signal, the legacy "
        "wording '2 subagents in parallel' leaves Wave 2 serial. "
        f"section text:\n{section}"
    )


def test_ai_pr_skill_step_8_pr_creation_after_max_wall() -> None:
    """PR creation must follow the concurrent block, not precede it.

    D-104-04 requires the PR description to be coherent at
    ``gh pr create`` time — i.e., CHANGELOG/README already generated
    and staged.  The SKILL.md ordering must therefore place the
    PR-creation step (step 12 in the canonical narrative) AFTER step 6.5
    (the concurrent docs+pre-push block) and AFTER step 7's pre-push
    completion.  If PR creation moves earlier, the body would reference
    docs that don't exist yet.
    """

    text = _read_skill_text()

    # Step 6.5 must appear before step 12 (PR creation).
    step_65 = re.search(r"^###\s+6\.5", text, flags=re.MULTILINE)
    step_7 = re.search(r"^###\s+7\.", text, flags=re.MULTILINE)
    step_12 = re.search(r"^###\s+12\.", text, flags=re.MULTILINE)

    assert step_65 is not None, "ai-pr SKILL.md must declare step 6.5"
    assert step_7 is not None, "ai-pr SKILL.md must declare step 7"
    assert step_12 is not None, "ai-pr SKILL.md must declare step 12 (PR creation)"

    assert step_65.start() < step_7.start() < step_12.start(), (
        "section ordering must remain step 6.5 → step 7 → step 12 so "
        "PR creation happens after the concurrent docs+pre-push block."
    )

    # The PR-creation section must not reference forming the body BEFORE
    # the concurrent block resolves — guard against narrative drift that
    # would describe an incoherent PR body.
    section_12 = _slice_section(text, r"^###\s+12\.", r"^###\s+\d|^##\s+\w")
    normalised_12 = _normalise(section_12)

    forbidden_pre_block_phrases = (
        "before the concurrent block",
        "before docs complete",
        "before pre-push completes",
        "before step 6.5",
        "without waiting for docs",
    )
    leaks = [phrase for phrase in forbidden_pre_block_phrases if phrase in normalised_12]
    assert not leaks, (
        "step 12 (PR creation) references pre-block timing "
        f"({leaks!r}); PR body must be assembled AFTER the concurrent "
        "block resolves to keep the description coherent."
    )

    # Positive assertion: somewhere in the SKILL.md (step 6.5, step 7,
    # or step 12) the narrative must EXPLICITLY state PR creation
    # follows the concurrent block. Textual ordering alone is too weak
    # — a future maintainer could shuffle sections without re-reading
    # the contract. Require explicit causal wording.
    full_normalised = _normalise(text)
    after_block_phrases = (
        "after the concurrent block",
        "after the concurrent dispatch",
        "after max(docs, pre-push)",
        "after max wall-clock",
        "after the max wall-clock",
        "after the 3-lane block",
        "after the 3 lane block",
        "once the concurrent block resolves",
        "once the concurrent block completes",
        "after both docs and pre-push",
        "after docs and pre-push complete",
        "after docs and pre-push resolve",
    )
    has_after_block_signal = any(phrase in full_normalised for phrase in after_block_phrases)
    assert has_after_block_signal, (
        "ai-pr SKILL.md must explicitly state PR creation follows the "
        "concurrent docs+pre-push block (one of "
        f"{list(after_block_phrases)!r}); textual ordering alone is "
        "insufficient — D-104-04 requires causal wording so the agent "
        "reads the dependency from prose, not from heading numbers."
    )


# ---------------------------------------------------------------------------
# Module-level guard — the tests above all depend on the canonical skill
# being present.  A ``ValueError`` here surfaces in collection rather
# than as a confusing per-test failure if someone accidentally relocates
# the SKILL.md file without updating the path constant.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _require_canonical_skill_present() -> None:
    if not _AI_PR_SKILL_PATH.is_file():  # pragma: no cover - safety net
        raise ValueError(
            f"spec-104 T-5.1 expects canonical ai-pr SKILL.md at "
            f"{_AI_PR_SKILL_PATH}; got missing file. Update path constant "
            "or restore the skill source."
        )
