"""spec-187 W1 (T-6/T-7) — token-budget lint tests.

RED-first: ``check_token_budget`` flags a ``description`` over 1024 chars,
a ``name`` over 64 chars, and reserved words (``claude`` / ``anthropic``)
in a name, across canonical skills + agents; stays clean on a compliant
fixture; and emits pure-ASCII findings on a raw stream (D-187-10).
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from skill_lint.checks.token_budget import check_token_budget, write_findings

_REPO_ROOT = Path(__file__).resolve().parents[3]


def _write_skill(root: Path, name: str, description: str) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True)
    md = skill_dir / "SKILL.md"
    md.write_text(
        f'---\nname: {name}\ndescription: "{description}"\n---\n\n# Title\n\nBody.\n',
        encoding="utf-8",
    )
    return md


def test_flags_overlong_description(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-long", "x" * 1200)

    results = check_token_budget(skills, agents)
    reasons = [r.reason for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert any("1024" in reason or "description" in reason.lower() for reason in reasons), reasons


def test_flags_reserved_word_in_name(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-claude-helper", "A short compliant description.")

    results = check_token_budget(skills, agents)
    reasons = [r.reason for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert any("reserved" in reason.lower() or "claude" in reason.lower() for reason in reasons), (
        reasons
    )


def test_flags_overlong_name(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    long_name = "ai-" + ("a" * 70)
    _write_skill(skills, long_name, "A short compliant description.")

    results = check_token_budget(skills, agents)
    reasons = [r.reason for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert any("64" in reason or "name" in reason.lower() for reason in reasons), reasons


def test_compliant_fixture_is_clean(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-clean", "A short, third-person, compliant description.")

    results = check_token_budget(skills, agents)
    flagged = [r for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert not flagged, [r.reason for r in flagged]


def test_output_is_pure_ascii_on_non_tty(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-claude-x", "x" * 1200)

    results = check_token_budget(skills, agents)
    buf = io.StringIO()
    write_findings(results, buf)
    out = buf.getvalue()
    assert out.isascii()
    out.encode("cp1252")  # must not raise


def test_live_corpus_runs_without_crashing() -> None:
    results = check_token_budget(
        _REPO_ROOT / ".claude" / "skills",
        _REPO_ROOT / ".claude" / "agents",
    )
    assert isinstance(results, list)
    for _path, result in results:
        assert result.reason.isascii()


def test_rejects_bad_severity() -> None:
    from skill_lint.checks.token_budget import RubricResult

    with pytest.raises(ValueError):
        RubricResult("token_budget", "FATAL", "bogus")
