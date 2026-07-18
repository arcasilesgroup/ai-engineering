"""spec-187 (W1 T-2/T-3, W5 flip) — portability lint tests.

Locks the W5 false-positive fix: ``check_portability`` flags a genuine
Claude-only tool literal used *as a tool* (a "tool"-qualified mention, a
clause-leading command, an arrow/slash map, a call form) but leaves the
ambiguous English verbs ``Read`` / ``Write`` / ``Edit`` alone, and does
not flag ``/ai-*`` slash idioms (documented harness-provided, AGENTS.md
W4). Findings are MAJOR (blocking) and pure-ASCII on a raw stream
(D-187-10, Windows cp1252 safety).
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from skill_lint.checks.portability import check_portability, write_findings

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


def test_flags_tool_literal_in_tool_context(tmp_path: Path) -> None:
    """A distinctive Claude tool literal used as a tool surfaces MAJOR."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(
        skills,
        "ai-bad",
        "Run the Grep tool over the repo to find every call site.\n",
    )

    results = check_portability(skills, agents)
    flagged = [r for _p, r in results if r.severity == "MAJOR"]
    assert flagged, "expected an un-gated tool-literal finding"
    assert any("Grep" in r.reason for _p, r in results)


def test_flags_clause_leading_tool_command(tmp_path: Path) -> None:
    """A clause-leading imperative tool command (``Grep the diff``) flags."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-bad2", "1. Grep the diff for suppression additions.\n")

    results = check_portability(skills, agents)
    flagged = [r for _p, r in results if r.severity == "MAJOR"]
    assert flagged, "expected a clause-leading tool-command finding"
    assert any("Grep" in r.reason for _p, r in results)


def test_english_verbs_are_not_flagged(tmp_path: Path) -> None:
    """``Read``/``Write``/``Edit`` as English verbs must NOT flag (FP fix)."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(
        skills,
        "ai-prose",
        (
            "1. Read the file and the spec gates before touching any code.\n"
            "2. Write the minimal implementation, then Edit the draft for clarity.\n"
        ),
    )

    results = check_portability(skills, agents)
    flagged = [r for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert not flagged, [r.reason for _p, r in results if r.severity != "OK"]


def test_slash_idiom_is_not_flagged(tmp_path: Path) -> None:
    """``/ai-*`` slash idioms are host-provided conventions — not findings."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-slash", "When ready, invoke /ai-build to run the plan.\n")

    results = check_portability(skills, agents)
    flagged = [r for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert not flagged, [r.reason for _p, r in results if r.severity != "OK"]


def test_neutral_fixture_is_clean(tmp_path: Path) -> None:
    """Gated prose produces no findings."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(
        skills,
        "ai-neutral",
        (
            "Run the test command via the Bash tool or the engine equivalent.\n"
            "Then hand off with `/ai-pr` (the slash layer is host-provided).\n"
        ),
    )

    results = check_portability(skills, agents)
    flagged = [r for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert not flagged, [r.reason for _p, r in results if r.severity != "OK"]


def test_output_is_pure_ascii_on_non_tty(tmp_path: Path) -> None:
    """write_findings emits pure ASCII on a raw stream (D-187-10)."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-bad3", "Use the Bash tool to run the suite.\n")

    results = check_portability(skills, agents)
    buf = io.StringIO()
    write_findings(results, buf)
    out = buf.getvalue()
    assert out.isascii(), "portability findings must be pure ASCII (cp1252-safe)"
    out.encode("cp1252")  # must not raise


def test_live_corpus_runs_without_crashing() -> None:
    """The lint executes over the real canonical corpus (blocking-green)."""
    results = check_portability(
        _REPO_ROOT / ".claude" / "skills",
        _REPO_ROOT / ".claude" / "agents",
    )
    assert isinstance(results, list)
    for _path, result in results:
        assert result.reason.isascii()
    # W5 blocking-green: the neutralised canonical corpus emits 0 MAJOR.
    assert not [r for _p, r in results if r.severity in ("MAJOR", "CRITICAL")]


def test_rejects_bad_severity() -> None:
    from skill_lint.checks.portability import RubricResult

    with pytest.raises(ValueError):
        RubricResult("portability", "FATAL", "bogus")
