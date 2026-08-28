"""`report recap`'s promises, pinned where the renderer could quietly break them.

Specification 046 sells the recap as the page a reviewer trusts: its file-tree and every
excerpt are facts from `git diff`, its budgets are the contract's, and its narrative is
the only part a human authored. Each test below names one way the command could report a
change it did not measure — a file list that drifted from the range, a secret that reached
the page, an empty range dressed as a summary — and refuses it on a real temporary
repository.
"""

from __future__ import annotations

import subprocess
from argparse import Namespace
from pathlib import Path

import pytest

from ai_engineering import contract, report


def _git(root: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True, check=True)
    return out.stdout


@pytest.fixture
def changed_repo(tmp_path: Path) -> tuple[Path, str]:
    """A repository with one commit of work over a named base, as the real flow leaves it."""

    root = tmp_path / "work"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t.test")
    _git(root, "config", "user.name", "t")
    (root / "a.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
    home = root / "specs" / "001-sample"
    home.mkdir(parents=True)
    (home / "spec.md").write_text("# Sample\n\nBody.\n", encoding="utf-8")
    (root / ".ai").mkdir()
    (root / ".ai" / ".gitignore").write_text("*\n!.gitignore\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "base")
    base = _git(root, "rev-parse", "HEAD").strip()
    # The real flow: the build commits its work, and the recap runs over that range.
    (root / "a.py").write_text("one\nTWO changed\nthree\nfour added\n", encoding="utf-8")
    (root / "b.md").write_text("new file\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "work")
    return root, base


def _recap(root: Path, base: str, summary: str = "Narrative sentence."):
    return report.render_recap(root, Namespace(spec="001", base=base, summary=summary))


def test_the_page_lists_exactly_the_files_the_range_changed(changed_repo, capsys):
    root, base = changed_repo
    assert _recap(root, base).outcome == "PASS"
    printed = capsys.readouterr().out
    page = next(root.glob(".ai/reports/*-recap-*.html"), None)
    assert page is not None, "no recap page was written"
    body = page.read_text(encoding="utf-8")
    for path in _git(root, "diff", "--name-only", base).splitlines():
        assert path in body, f"the range changed {path} and the page does not list it"
    assert "file://" in printed, "the link duty was not printed"


def test_a_recap_of_an_empty_range_refuses_instead_of_writing_a_page(changed_repo):
    root, base = changed_repo
    assert _recap(root, "HEAD").outcome == "INCOMPLETE"
    assert not list(root.glob(".ai/reports/*-recap-*.html")), (
        "an empty range still wrote a page: a recap of nothing is a page of lies"
    )


def test_a_secret_in_a_diff_excerpt_never_reaches_the_page(changed_repo):
    root, base = changed_repo
    (root / "c.env").write_text("API_KEY = supersecretvalue123\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "config")
    assert _recap(root, base, summary="Added config.").outcome == "PASS"
    body = next(root.glob(".ai/reports/*-recap-*.html")).read_text(encoding="utf-8")
    assert "supersecretvalue123" not in body, "a secret crossed from the diff into the page"
    assert "redacted" in body


def test_excerpt_budgets_come_from_the_contract(changed_repo):
    """A recap that ignored the budget would be a dump wearing a summary's clothes."""

    root, base = changed_repo
    big = "\n".join(f"line {n} changed" for n in range(contract.RECAP_EXCERPT_LINES_MAX + 40))
    (root / "a.py").write_text(big + "\n", encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "-qm", "big")
    assert _recap(root, base, summary="Big change.").outcome == "PASS"
    body = next(root.glob(".ai/reports/*-recap-*.html")).read_text(encoding="utf-8")
    for block in body.split("<pre class='diff'>")[1:]:
        excerpt = block.split("</pre>")[0]
        assert excerpt.count("\n") <= contract.RECAP_EXCERPT_LINES_MAX, (
            "a diff excerpt ran past the budget the contract names"
        )


def test_a_missing_spec_refuses_and_writes_no_page(changed_repo):
    root, base = changed_repo
    result = report.render_recap(
        root, Namespace(spec="999", base=base, summary="Nothing to recap.")
    )
    assert result.outcome == "INCOMPLETE"
    assert not list(root.glob(".ai/reports/*-recap-*.html"))


def test_a_base_that_is_an_option_is_refused_before_git_sees_it(changed_repo):
    """S8705, closed by refusing the class rather than by trusting the probe.

    `--base=--output=<path>` reaches `git rev-parse` as an argument, and a scanner —
    or a reviewer — cannot tell whether the probe catches it; the guard must. The
    written-file check is the point: a refusal that still wrote the payload is no
    refusal. The last row proves the refusal is about the shape and not the fixture:
    the same well-formed base the other tests recap passes the guard.
    """
    root, base = changed_repo
    # The path git would write is relative to its cwd, which is `root` — checking
    # tmp_path instead would pass even if the guard leaked.
    evil = root / "evil"
    assert _recap(root, f"--output={evil}").outcome == "INCOMPLETE"
    assert not evil.exists(), "git wrote the option's file despite the refusal"
    assert _recap(root, "HEAD --output=x").outcome == "INCOMPLETE"
    assert _recap(root, base).outcome == "PASS", "a well-formed rev still passes the guard"
