"""spec-189 (Phase 1 T-1/T-2) — front-loading/BLUF lint tests.

RED-first (D-189-08): ``check_frontloading`` inspects the skill BODY's
recap region — the text after the ``--- ... ---`` frontmatter fence and
the H1 title, before the first ``## `` header. That region must be the
BLUF: at most two sentences and no list line (``- ``/``* ``/``N.``). A
compliant short recap scores OK; a >2-sentence recap, a recap carrying a
list line, or a missing recap (H1 immediately followed by ``## ``) each
surface a MAJOR ``front_loading_bluf`` finding. Reason strings are pure
ASCII so a raw / non-tty write stays cp1252-safe (D-187-10).
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from skill_lint.checks.frontloading import check_frontloading, write_findings

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_skill(root: Path, name: str, body: str) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    md = skill_dir / "SKILL.md"
    md.write_text(
        "---\nname: " + name + '\ndescription: "x"\n---\n\n# Title\n\n' + body,
        encoding="utf-8",
    )
    return md


_COMPLIANT_RECAP = (
    "Restructure code to change its shape while preserving behavior. "
    "Move, rename, and split without altering the observable contract.\n\n"
    "## Workflow\n\n"
    "1. Identify the seam.\n"
)

_THREE_SENTENCE_RECAP = (
    "Restructure code to change its shape. Preserve the observable "
    "behavior. Escalate after two failed attempts.\n\n"
    "## Workflow\n\n"
    "1. Identify the seam.\n"
)

_LIST_IN_RECAP = (
    "Restructure code with these levers:\n"
    "- Move files across modules.\n"
    "- Rename symbols in place.\n\n"
    "## Workflow\n\n"
    "1. Identify the seam.\n"
)

_MISSING_RECAP = "## Workflow\n\n1. Identify the seam.\n"


def test_compliant_recap_is_ok(tmp_path: Path) -> None:
    """A short 1-2 sentence recap scores OK (no findings)."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-clean", _COMPLIANT_RECAP)

    results = check_frontloading(skills, agents)
    flagged = [r for _p, r in results if r.severity in ("MINOR", "MAJOR", "CRITICAL")]
    assert not flagged, [r.reason for r in flagged]
    assert any(r.severity == "OK" for _p, r in results)


def test_three_sentence_recap_is_major(tmp_path: Path) -> None:
    """A recap over two sentences surfaces MAJOR front_loading_bluf."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-wordy", _THREE_SENTENCE_RECAP)

    results = check_frontloading(skills, agents)
    flagged = [r for _p, r in results if r.severity == "MAJOR"]
    assert flagged, "expected a >2-sentence BLUF finding"
    assert all(r.rule_name == "front_loading_bluf" for r in flagged)


def test_recap_with_list_line_is_major(tmp_path: Path) -> None:
    """A recap carrying a `- ` list line surfaces MAJOR front_loading_bluf."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-listy", _LIST_IN_RECAP)

    results = check_frontloading(skills, agents)
    flagged = [r for _p, r in results if r.severity == "MAJOR"]
    assert flagged, "expected a list-in-BLUF finding"
    assert all(r.rule_name == "front_loading_bluf" for r in flagged)
    assert any("list" in r.reason.lower() for r in flagged)


def test_missing_recap_is_major(tmp_path: Path) -> None:
    """H1 immediately followed by `## ` is a missing BLUF => MAJOR."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-empty", _MISSING_RECAP)

    results = check_frontloading(skills, agents)
    flagged = [r for _p, r in results if r.severity == "MAJOR"]
    assert flagged, "expected a missing-BLUF finding"
    assert all(r.rule_name == "front_loading_bluf" for r in flagged)


def test_output_is_pure_ascii_on_non_tty(tmp_path: Path) -> None:
    """write_findings emits pure ASCII on a raw stream (D-187-10)."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-wordy2", _THREE_SENTENCE_RECAP)

    results = check_frontloading(skills, agents)
    buf = io.StringIO()
    write_findings(results, buf)
    out = buf.getvalue()
    assert out.isascii(), "front-loading findings must be pure ASCII (cp1252-safe)"
    out.encode("cp1252")  # must not raise


def test_live_corpus_runs_without_crashing() -> None:
    """The lint executes over the real canonical corpus and stays ASCII."""
    results = check_frontloading(
        _REPO_ROOT / ".claude" / "skills",
        _REPO_ROOT / ".claude" / "agents",
    )
    assert isinstance(results, list)
    for _path, result in results:
        assert result.reason.isascii()


def test_live_corpus_is_blocking_green() -> None:
    """The real fleet baseline is clean: 0 MAJOR/CRITICAL front-loading findings.

    T-17 (D-189-08) flipped this lint to BLOCKING once Wave 3 fixed all 49
    violations. This locks the clean baseline so a future regression
    (a body that buries its bottom-line) reds CI, mirroring the W5
    blocking-green assertion in ``test_portability.py``.
    """
    results = check_frontloading(
        _REPO_ROOT / ".claude" / "skills",
        _REPO_ROOT / ".claude" / "agents",
    )
    blocking = [(path, r) for path, r in results if r.severity in ("MAJOR", "CRITICAL")]
    assert not blocking, [f"{path}: {r.reason}" for path, r in blocking]


def test_rejects_bad_severity() -> None:
    from skill_lint.checks.frontloading import RubricResult

    with pytest.raises(ValueError):
        RubricResult("front_loading_bluf", "FATAL", "bogus")


def test_abbreviations_do_not_overcount_sentences(tmp_path: Path) -> None:
    """A 2-sentence BLUF using e.g./i.e. must not trip the blocking cap.

    Regression for the /ai-review MEDIUM finding: the sentence terminator
    regex used to count the dot in ``e.g.``/``i.e.``/``etc.``/``vs.`` as a
    sentence boundary, hard-failing a legitimate 2-sentence BLUF once the
    lint went blocking (T-17).
    """
    _write_skill(
        tmp_path,
        "ai-abbr",
        "Do a thing, e.g. edge cases, i.e. the hard parts. "
        "It also handles B.\n\n## Workflow\n\n1. Step.\n",
    )
    sev = [r.severity for _p, r in check_frontloading(tmp_path, tmp_path / "none")]
    assert "MAJOR" not in sev, sev


def test_decimal_opening_is_not_a_list_line(tmp_path: Path) -> None:
    """A BLUF opening with a decimal (``3.5x``) must not read as a list line.

    Regression for the /ai-review LOW finding: the list-line regex lacked a
    trailing-space requirement after ``\\d+\\.``, so a decimal at line start
    tripped the "BLUF contains a list" MAJOR.
    """
    _write_skill(
        tmp_path,
        "ai-dec",
        "3.5x faster than the baseline on cold starts. "
        "Measured across the whole suite.\n\n## Workflow\n\n1. Step.\n",
    )
    sev = [r.severity for _p, r in check_frontloading(tmp_path, tmp_path / "none")]
    assert "MAJOR" not in sev, sev
