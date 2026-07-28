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


def test_widened_corpus_includes_handlers_and_references(tmp_path: Path) -> None:
    """Discovery walks every ``*.md`` under the skills root, not just SKILL.md.

    spec-201 D-201-15 / sub-007 T-7.5: the pre-widening walk took only
    ``<skill-dir>/SKILL.md``, so 58 handler files and 18 reference files
    were invisible to a blocking gate. Both must now surface.
    """
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    skill_md = _write_skill(skills, "ai-deep", "Nothing to see here.\n")
    handler = skill_md.parent / "handlers" / "h.md"
    handler.parent.mkdir()
    handler.write_text("Run the Grep tool over the repo.\n", encoding="utf-8")
    reference = skill_md.parent / "references" / "r.md"
    reference.parent.mkdir()
    reference.write_text("Run the Grep tool over the repo.\n", encoding="utf-8")

    by_path = dict(check_portability(skills, agents))
    assert handler in by_path, sorted(str(p) for p in by_path)
    assert reference in by_path, sorted(str(p) for p in by_path)
    assert by_path[handler].severity == "MAJOR"
    assert by_path[reference].severity == "MAJOR"


def test_widened_corpus_size_is_pinned() -> None:
    """Every canonical ``*.md`` is linted — computed, never hardcoded.

    Closes sub-007 spec R-7: no CI workflow runs ``skill_lint``, so
    ``test_live_corpus_runs_without_crashing`` is the sole enforcement
    point. A regression of discovery back to ``iterdir()``/``SKILL.md``
    would leave that zero-MAJOR assertion trivially green over a subset of
    the tree with no failure anywhere.
    """
    skills_root = _REPO_ROOT / ".claude" / "skills"
    agents_root = _REPO_ROOT / ".claude" / "agents"
    expected = len(list(skills_root.rglob("*.md"))) + len(list(agents_root.glob("*.md")))

    results = check_portability(skills_root, agents_root)

    assert len(results) == expected
    assert len(results) == len({path for path, _r in results}), "duplicate corpus entry"


def test_dispatch_literal_flags_on_explicit_tool_signal(tmp_path: Path) -> None:
    """``Agent``/``Task`` flag when a genuine tool signal is present.

    spec-201 D-201-15 requires the dispatch literals to be evaluated. They
    participate in ``_LITERAL_RE`` and ``_SLASH_PAIR_RE``, so a
    "tool"-qualified mention and a call form both surface.
    """
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    qualified = _write_skill(
        skills,
        "ai-dispatch-tool",
        "4. Dispatch the specialist via the Agent tool with the shared context.\n",
    )
    call_form = _write_skill(skills, "ai-dispatch-call", "- Delegate to Agent(Build).\n")

    by_path = dict(check_portability(skills, agents))
    assert by_path[qualified].severity == "MAJOR"
    assert "Agent" in by_path[qualified].reason
    assert by_path[call_form].severity == "MAJOR"
    assert "Agent" in by_path[call_form].reason


def test_dispatch_literal_does_not_flag_clause_leading_domain_prose(tmp_path: Path) -> None:
    """Clause-leading ``Agent``/``Task`` stays domain vocabulary, not a finding.

    ``portability.py`` module docstring (D-187-07, W5) dropped these two
    literals because clause-leading prose produced ~47 false positives.
    sub-007 spec V-6 re-measured it: a blunt re-add reinstates 6 findings
    over 3 files that are ordinary domain vocabulary. ``_DISPATCH_LITERALS``
    therefore stays OUT of ``_CLAUSE_START_RE``.
    """
    skills = tmp_path / "skills"
    agents = tmp_path / "agents"
    agents.mkdir()
    _write_skill(
        skills,
        "ai-domain-prose",
        (
            "Task statuses (all consumers honor the same vocabulary):\n"
            "\n"
            "- Agent files live in the agents directory.\n"
        ),
    )

    results = check_portability(skills, agents)
    flagged = [r for _p, r in results if r.severity in ("MINOR", "MAJOR")]
    assert not flagged, [r.reason for _p, r in results if r.severity != "OK"]


def test_live_corpus_runs_without_crashing() -> None:
    """The lint executes over the real widened corpus (blocking-green).

    Post sub-007 T-7.5 the corpus is every ``*.md`` under
    ``.claude/skills`` (135: 54 SKILL.md + 58 handlers + 18 references + 5
    other) plus every ``.claude/agents/*.md`` (19) = 154 files, not the 73
    SKILL.md + agent files the pre-widening walk saw.
    """
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
