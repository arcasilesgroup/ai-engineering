"""Executable contracts for spec 041 / B-041-1: the `[X]` promotion marker.

A decision is born inside its spec; the `[X]` marker under `## Decisions` is the author's
own claim that the decision constrains specs that do not exist yet, and `ai-eng decide`
promotes only marked entries. The parser reads the record; the verb refuses everything
else before anything is written.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

from ai_engineering import decide, outcome, paths, spec

MARKED = """## Decisions

- [X] **D-041-01 — the first decision**
- **D-041-00 — an unmarked decision**
- [x] **D-041-02 : the second decision**

**Rationale:** whatever.
"""


def test_marked_decisions_returns_only_marked_entries_under_the_decisions_section():
    found = spec.marked_decisions("## Decision\n\n- [X] **D-041-09 — elsewhere**\n" + MARKED)
    assert found == [
        ("D-041-01", "the first decision"),
        ("D-041-02", "the second decision"),
    ]


def test_marked_decisions_stops_at_the_next_heading():
    body = MARKED + "\n## Later section\n\n- [X] **D-041-03 — outside**\n"
    assert spec.marked_decisions(body) == [
        ("D-041-01", "the first decision"),
        ("D-041-02", "the second decision"),
    ]


def test_marked_decisions_is_empty_without_a_section_or_without_marks():
    assert spec.marked_decisions("# No decisions here\n") == []
    assert spec.marked_decisions(MARKED.replace("[X]", "[ ]").replace("[x]", "[ ]")) == []


def _repository_with_marked_spec(root: Path) -> None:
    spec_path = root / "specs" / "041-governed" / "spec.md"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(
        '---\nid: "041"\nstatus: draft\n---\n\n# Governed\n\n'
        "## Decisions\n\n- [X] **D-041-01 — the earned decision**\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "--quiet", "-b", "main"], cwd=root, check=True)
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": "role",
        "GIT_AUTHOR_EMAIL": "role@example.invalid",
        "GIT_COMMITTER_NAME": "role",
        "GIT_COMMITTER_EMAIL": "role@example.invalid",
    }
    subprocess.run(
        ["git", "commit", "--quiet", "--allow-empty", "-m", "baseline"],
        cwd=root,
        check=True,
        env=environment,
    )


def test_decide_refuses_an_unmarked_title_with_nothing_written(tmp_path, monkeypatch, capsys):
    root = tmp_path / "refused"
    _repository_with_marked_spec(root)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)

    result = decide.main(["a decision nobody marked"])
    assert type(result) is outcome.Result
    assert result.outcome == "INCOMPLETE"
    printed = capsys.readouterr().out
    assert "not marked `[X]`" in printed
    assert not (root / "docs").exists()


def test_decide_promotes_a_title_the_spec_marks(tmp_path, monkeypatch):
    root = tmp_path / "promoted"
    _repository_with_marked_spec(root)
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)

    result = decide.main(["the earned decision"])
    assert type(result) is outcome.Result
    assert result.outcome == "PASS"
    assert (root / "docs" / "adr" / "0001-the-earned-decision.md").is_file()
    assert next((root / "docs" / "adr").glob("0002-*"), None) is None
