"""The run receipt, and the four ways it has to be absent.

The value of this trailer is entirely in when it does *not* appear. A trailer written on
every commit says nothing; one written only when a suite has run over exactly these bytes
turns `git log` into the answer to `PO-10` and `PO-14`, which had no answer at all because a
gate run left nothing behind that survived into the tree.

So the cases that matter here are the refusals: no receipt, a receipt for other content, a
receipt naming no suite, and a working tree edited after the run. Each one is a way somebody
could get a trailer they had not earned, which is this repository's defining defect.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tests" / "ran_receipt.py"


# `mutmut` copies the tree under a directory called `mutants` and installs an import shim, so
# a child process started from a temporary directory that imports `ai_engineering` gets
# mutmut's own error about not knowing where the code to mutate is — not a receipt, and not
# anything about this script. Four mutation runs died on that tonight, each on a different
# cause and none of them the code under measurement.
UNDER_MUTATION = "mutants" in Path(__file__).resolve().parts


def _run(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args], capture_output=True, text=True, cwd=str(cwd)
    )


@pytest.fixture
def repository(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A real git repository, because the digest is taken over what git says is tracked.

    A fake would have to reimplement `ls-files --cached --others --exclude-standard`, and the
    exclusion is half of what makes the digest stable — a fixture that skipped it would leave
    the ignore behaviour untested and the test would pass on a script that hashed `.venv`.
    """

    if UNDER_MUTATION:
        pytest.skip("the mutant tree's import shim answers for the package, not this script")
    for command in (
        ("git", "init", "-q"),
        ("git", "config", "user.email", "t@example.invalid"),
        ("git", "config", "user.name", "t"),
    ):
        subprocess.run(command, cwd=tmp_path, check=True, capture_output=True)
    (tmp_path / "kept.txt").write_text("one\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("ignored/\n", encoding="utf-8")
    (tmp_path / "ignored").mkdir()
    (tmp_path / "ignored" / "noise.txt").write_text("noise\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", [str(SCRIPT)])
    return tmp_path


def _receipt(where: Path) -> Path:
    return where / ".ai" / "receipts" / "ran.json"


@pytest.mark.parametrize("body", [None, "{not json", '{"suite": "check"}'])
def test_a_receipt_that_cannot_be_used_produces_silence(repository: Path, body):
    """Three ways to have no usable receipt, and one answer to all three: nothing written,
    exit 1. No receipt at all is the starting state of every clone and the state the whole
    design rests on. A malformed one is exactly as much evidence as none. One naming a suite
    but no content digest cannot say which bytes were run, which is the only thing that makes
    the trailer worth writing.

    It runs on the commit path, so a crash here is somebody's commit — which is why the
    malformed case is a refusal and not a traceback."""

    if body is not None:
        receipt = _receipt(repository)
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(body, encoding="utf-8")

    done = _run("trailer", cwd=repository)

    assert done.returncode == 1
    assert done.stdout == ""


def test_a_recorded_run_names_its_suite_and_its_content(repository: Path):
    """The only case that produces a trailer, and both fields have to survive to the line."""

    assert _run("record", "check", cwd=repository).returncode == 0
    done = _run("trailer", cwd=repository)

    assert done.returncode == 0
    assert done.stdout.startswith("Ai-Eng-Ran: check content=")
    written = json.loads(_receipt(repository).read_text(encoding="utf-8"))
    assert done.stdout.strip().endswith(written["content"][:12])
    assert len(done.stdout.strip().split("content=")[1]) == 12


def test_editing_a_file_after_the_run_withdraws_the_trailer(repository: Path):
    """The case the whole thing exists for. Run the gate, change the code, commit anyway:
    without this, the commit carries a trailer for a run that never saw what it ships."""

    assert _run("record", "check", cwd=repository).returncode == 0
    (repository / "kept.txt").write_text("two\n", encoding="utf-8")

    done = _run("trailer", cwd=repository)

    assert done.returncode == 1
    assert done.stdout == ""


def test_a_new_file_withdraws_it_too(repository: Path):
    """An addition is a change, and `--others` is what makes this visible: a file added
    after the run is in the digest's set before it is ever staged."""

    assert _run("record", "check", cwd=repository).returncode == 0
    (repository / "added.txt").write_text("new\n", encoding="utf-8")

    assert _run("trailer", cwd=repository).returncode == 1


def test_an_ignored_file_does_not_move_it(repository: Path):
    """The other half. A build directory, a virtualenv or a receipt changing under the run
    would withdraw every trailer and the mechanism would be useless within a day, so the
    exclusion is load-bearing rather than tidiness."""

    assert _run("record", "check", cwd=repository).returncode == 0
    (repository / "ignored" / "noise.txt").write_text("different noise\n", encoding="utf-8")

    assert _run("trailer", cwd=repository).returncode == 0


def test_a_receipt_naming_no_suite_proves_nothing(repository: Path):
    """A digest with no suite beside it says these bytes were seen by something unnamed.
    That is not what `PO-14` asks — it asks *which* suite ran — so it is a refusal."""

    assert _run("record", "check", cwd=repository).returncode == 0
    receipt = _receipt(repository)
    body = json.loads(receipt.read_text(encoding="utf-8"))
    body["suite"] = "   "
    receipt.write_text(json.dumps(body), encoding="utf-8")

    assert _run("trailer", cwd=repository).returncode == 1


def test_the_script_refuses_an_argument_shape_it_does_not_know(repository: Path):
    """Exit 2, distinct from the 1 that means "no trailer to write". A hook that cannot tell
    "nothing ran" from "you called me wrong" reports the second as the first forever."""

    assert _run("record", cwd=repository).returncode == 2
    assert _run("trailer", "extra", cwd=repository).returncode == 2


def test_the_cheap_recipe_records_only_after_the_suite_passes():
    """`PO-14` asks for the module's own suite, and `just quick` is the only thing that
    records one. The order in that recipe is the whole safety property: a receipt written
    after a red suite says these bytes were run and passed, which is a false green with a
    digest on it — the exact shape this repository exists to prevent.

    Read from the justfile rather than by running a failing suite, because the recipe's two
    lines are what encodes it and a run would prove only that today's `just` honours them.
    Both readings are worth having; this is the one a gate can afford."""

    recipes = (ROOT / "justfile").read_text(encoding="utf-8").splitlines()
    start = next(n for n, one in enumerate(recipes) if one.startswith("quick "))
    body = []
    for line in recipes[start + 1 :]:
        # Stop at the first line that is not part of this recipe. The first version took
        # every indented line in the rest of the file, so it read two only because `quick`
        # happened to be last; adding one recipe below it made the same assertion fail with
        # a number about a different recipe entirely.
        if not line.startswith(("    ", "\t")):
            break
        body.append(line.strip())

    assert len(body) == 2, f"the recipe is {len(body)} lines and the order below reads two"
    assert "pytest" in body[0], "the suite does not run first, so nothing is being recorded"
    assert "ran_receipt.py record" in body[1], "nothing records the pass"
    assert "||" not in body[1] and body[1][:1] != "-", (
        "the record line is written so it survives the line above failing, which makes the "
        "receipt a claim about a suite that did not pass"
    )


def test_the_digest_the_receipt_carries_comes_from_the_package(repository: Path):
    """One home for the algorithm, because the checkpoint needs to read it too.

    The digest lived in this script, which `commit-msg` and two build recipes run by path.
    Nothing under `src/` can import a file in `tests/`, so a checkpoint that wanted to prefer
    the one receipt bound to the tree's content had two options: copy the algorithm into a
    second file, or go without. A hash computed in two places is a hash that drifts, and this
    repository has a paragraph about every other pair of files that held one number.
    """

    import importlib.util

    from ai_engineering import evidence

    spec = importlib.util.spec_from_file_location("ran_receipt_probe", SCRIPT)
    assert spec and spec.loader
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)

    assert script.content_digest is evidence.content_digest

    # And it still answers about the repository it is asked from, not the one it lives in.
    (repository / "one.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=str(repository), check=True)
    before = evidence.content_digest(repository)
    (repository / "one.txt").write_text("two\n", encoding="utf-8")
    assert evidence.content_digest(repository) != before


def test_a_present_trailer_does_not_split_the_line_it_is_read_from():
    """The inversion this shape invites, and it is silent.

    `git log --format` expands `%(trailers:...)` with a trailing newline unless a separator is
    given. Without one, every commit that *has* a receipt splits into two lines and parses as
    malformed, while every commit that has none parses cleanly — so the report would name the
    commits that ran and exonerate the ones that did not. Exactly backwards, and green.
    """

    import subprocess

    body = (ROOT / "tests" / "ran_receipt.py").read_text(encoding="utf-8")

    assert "separator=" in body, "the log format lets a present trailer break its own line"

    listed = subprocess.run(
        [
            "git",
            "log",
            "--format=%H%x1f%(trailers:key=Ai-Eng-Ran,valueonly,separator=%x00)%x1f%s",
            "-20",
        ],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        check=False,
    ).stdout
    rows = [line for line in listed.splitlines() if line.strip()]
    assert rows, "no commit was listed, so this proved nothing"
    assert all(len(row.split("\x1f")) == 3 for row in rows), (
        "a row split into something other than sha, trailer and subject, which is how the "
        "commits that ran come to read as the broken ones"
    )
