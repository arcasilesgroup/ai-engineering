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


def test_no_receipt_means_no_trailer(repository: Path):
    """The starting state of every clone, and the one the whole design rests on: silence."""

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


def test_a_receipt_that_is_not_json_is_a_refusal_and_not_a_crash(repository: Path):
    """It runs on the commit path, so its failure mode is somebody's commit. A malformed
    receipt is exactly as much evidence as no receipt, and has to behave the same way."""

    receipt = _receipt(repository)
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text("{not json", encoding="utf-8")

    done = _run("trailer", cwd=repository)

    assert done.returncode == 1
    assert done.stdout == ""


def test_the_script_refuses_an_argument_shape_it_does_not_know(repository: Path):
    """Exit 2, distinct from the 1 that means "no trailer to write". A hook that cannot tell
    "nothing ran" from "you called me wrong" reports the second as the first forever."""

    assert _run("record", cwd=repository).returncode == 2
    assert _run("trailer", "extra", cwd=repository).returncode == 2
