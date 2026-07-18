"""spec-187 W1 (T-2/T-3) — portability lint tests.

RED-first: asserts ``check_portability`` flags un-gated Claude-only tool
literals and bare ``/ai-*`` dispatch idioms in canonical prose, stays
clean on a neutral (gated) fixture, and emits pure-ASCII findings on a
non-tty / raw stream (D-187-10, Windows cp1252 safety).
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


def test_flags_ungated_tool_literal(tmp_path: Path) -> None:
    """A bare Claude tool literal in prose surfaces a warn finding."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(
        skills,
        "ai-bad",
        "Use the Bash tool to run the suite, then Read the output file.\n",
    )

    results = check_portability(skills, agents)
    flagged = [r for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert flagged, "expected an un-gated tool-literal finding"
    assert any("Bash" in r.reason or "Read" in r.reason for _p, r in results)


def test_flags_bare_slash_dispatch(tmp_path: Path) -> None:
    """A bare (non-code) /ai-* dispatch idiom surfaces a warn finding."""
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-bad2", "When ready, invoke /ai-build to run the plan.\n")

    results = check_portability(skills, agents)
    flagged = [r for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert flagged, "expected an un-gated /ai-* dispatch finding"
    assert any("/ai-build" in r.reason for _p, r in results)


def test_neutral_fixture_is_clean(tmp_path: Path) -> None:
    """Gated prose + code-fenced slash idioms produce no warn findings."""
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
    _write_skill(skills, "ai-bad3", "Use the Bash tool and invoke /ai-build now.\n")

    results = check_portability(skills, agents)
    buf = io.StringIO()
    write_findings(results, buf)
    out = buf.getvalue()
    assert out.isascii(), "portability findings must be pure ASCII (cp1252-safe)"
    out.encode("cp1252")  # must not raise


def test_live_corpus_runs_without_crashing() -> None:
    """The lint executes over the real canonical corpus (warn-only)."""
    results = check_portability(
        _REPO_ROOT / ".claude" / "skills",
        _REPO_ROOT / ".claude" / "agents",
    )
    assert isinstance(results, list)
    for _path, result in results:
        assert result.reason.isascii()


def test_rejects_bad_severity() -> None:
    from skill_lint.checks.portability import RubricResult

    with pytest.raises(ValueError):
        RubricResult("portability", "FATAL", "bogus")
