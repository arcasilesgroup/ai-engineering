"""spec-187 W1 (T-4/T-5) — structure/procedure lint tests.

RED-first: ``check_structure`` scores the ``## Workflow`` procedure-ratio
(numbered / checklist / table vs free prose), flags bodies over 500 lines
and references deeper than one level, stays clean on a well-structured
fixture, and emits pure-ASCII findings on a raw stream (D-187-10).
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from skill_lint.checks.structure import check_structure, write_findings

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


_PROSE_WORKFLOW = (
    "## Workflow\n\n"
    "First you should carefully read the failing input and the spec gates "
    "before you touch any code because that is the only way to be sure.\n"
    "Then you write the implementation, taking care to keep things simple "
    "and to prefer deletion over abstraction wherever it is reasonable.\n"
    "Finally you run the tests and review your own diff for elegance and "
    "clarity, escalating to the user if anything looks off. (§10.5 TDD)\n"
)

_PROCEDURE_WORKFLOW = (
    "## Workflow\n\n"
    "1. Read the failing input and spec gates. (§10.5 TDD)\n"
    "2. Write the minimal implementation.\n"
    "3. Run the tests and self-review the diff.\n"
    "4. Escalate after two failed attempts.\n"
)


def test_flags_prose_heavy_workflow(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-prose", _PROSE_WORKFLOW)

    results = check_structure(skills, agents)
    reasons = [r.reason for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert any("prose" in reason.lower() for reason in reasons), reasons


def test_flags_oversized_body(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    big = _PROCEDURE_WORKFLOW + ("\nfiller line\n" * 600)
    _write_skill(skills, "ai-big", big)

    results = check_structure(skills, agents)
    reasons = [r.reason for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert any("500" in reason for reason in reasons), reasons


def test_flags_deep_reference(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    body = _PROCEDURE_WORKFLOW + "\nSee [details](references/nested/deep/detail.md).\n"
    _write_skill(skills, "ai-deepref", body)

    results = check_structure(skills, agents)
    reasons = [r.reason for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert any("level" in reason.lower() or "deep" in reason.lower() for reason in reasons), reasons


def test_well_structured_fixture_is_clean(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    body = _PROCEDURE_WORKFLOW + "\nSee [details](references/detail.md).\n"
    _write_skill(skills, "ai-clean", body)

    results = check_structure(skills, agents)
    flagged = [r for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert not flagged, [r.reason for r in flagged]


def test_output_is_pure_ascii_on_non_tty(tmp_path: Path) -> None:
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(skills, "ai-prose2", _PROSE_WORKFLOW)

    results = check_structure(skills, agents)
    buf = io.StringIO()
    write_findings(results, buf)
    out = buf.getvalue()
    assert out.isascii()
    out.encode("cp1252")  # must not raise


def test_live_corpus_runs_without_crashing() -> None:
    results = check_structure(
        _REPO_ROOT / ".claude" / "skills",
        _REPO_ROOT / ".claude" / "agents",
    )
    assert isinstance(results, list)
    for _path, result in results:
        assert result.reason.isascii()


def test_rejects_bad_severity() -> None:
    from skill_lint.checks.structure import RubricResult

    with pytest.raises(ValueError):
        RubricResult("structure", "FATAL", "bogus")
