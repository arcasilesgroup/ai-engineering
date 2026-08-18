"""Drafting a report: the order of the three steps, and why nothing is ever sent.

`report.report_issue` carried 53 surviving mutants. It builds one governed report from an
allow-list of fields, scans the exact bytes it built, and only then writes them — and the
order is the whole control rather than a tidiness preference.

Build first, because a report assembled from whatever a caller passed is a report that can
carry a field nobody reviewed. Scan the bytes that were built, not the arguments that went
in, because the scan has to see what would actually leave the machine. Write last, because
the artefact a person can still send is the one that matters: a refusal that leaves a file
behind has already put the thing it refused within reach.

Two refusals sit either side of the write and they are not the same refusal. A scan finding
means these bytes may not leave. A security kind asked to submit means these bytes may not
leave *this way* — and that one is checked before the draft is written, because a control
that asks first and refuses second has already put the wrong route in front of somebody at
the end of a long day.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_engineering import issue, report


def _asked(**overrides) -> argparse.Namespace:
    fields = {
        "kind": "bug",
        "title": "the gate reports a stage it did not reach",
        "what_happened": "it printed four of four after stopping at three",
        "expected": "the index where the run actually reached",
        "step": ["run the gate", "interrupt it"],
        "submit": False,
    }
    fields.update(overrides)
    return argparse.Namespace(**fields)


def _drafted(root: Path) -> bool:
    return issue.draft_path(root).is_file()


def test_outside_a_repository_there_is_nowhere_to_keep_a_draft(capsys):
    assert report.report_issue(None, _asked()).outcome == "INCOMPLETE"
    assert "nowhere to keep a draft" in capsys.readouterr().out


def test_an_ordinary_report_is_written_locally_and_says_nothing_was_sent(tmp_path: Path, capsys):
    """The clean control, and its last line is the point. Sending is a separate action a
    person confirms, so a draft that did not say so would leave somebody assuming it had
    gone."""

    done = report.report_issue(tmp_path, _asked())
    capsys.readouterr()

    assert done.result.outcome == "PASS"
    assert _drafted(tmp_path)
    assert any("Nothing has been sent" in line for line in done.remaining)


def test_the_draft_carries_the_digest_of_what_was_built(tmp_path: Path, capsys):
    """A digest over the payload rather than over the file, because the file is the thing
    that gets edited before somebody pastes it and the payload is what was scanned. Bare
    hexadecimal and no `sha256:` prefix, unlike the receipts — this one is printed beside
    the bytes for a person to compare, not read back by a schema."""

    done = report.report_issue(tmp_path, _asked())
    capsys.readouterr()

    digests = [fact.detail for fact in done.checks if fact.id == "digest"]
    assert digests and len(digests[0]) == 64 and int(digests[0], 16) >= 0


def test_a_finding_in_the_bytes_stops_the_report_and_leaves_no_file(tmp_path: Path, capsys):
    """The refusal names the class it found and writes nothing, because the artefact a
    person can still send is the one that matters."""

    leaking = _asked(what_happened=f"it printed {Path.home()}/.ssh/id_rsa in the log")

    done = report.report_issue(tmp_path, leaking)
    capsys.readouterr()

    assert done.result.outcome == "INCOMPLETE"
    assert done.remaining
    assert not _drafted(tmp_path)


def test_every_finding_carries_the_same_cure_and_the_cure_is_not_delete_the_file(
    tmp_path: Path, capsys
):
    """There is no file. What a person can act on is the field, so the cure names the field
    rather than an artefact that was never written."""

    leaking = _asked(what_happened=f"it printed {Path.home()}/.ssh/id_rsa in the log")

    done = report.report_issue(tmp_path, leaking)
    capsys.readouterr()

    assert done.checks
    for fact in done.checks:
        assert "rewrite the field" in (fact.cure or "")


def test_a_vulnerability_asked_to_submit_is_refused_before_the_draft_is_written(
    tmp_path: Path, capsys
):
    """Before the terminal, not after. A control that asks first and refuses second has
    already put the wrong route in front of somebody at the end of a long day — and here
    that route is a public issue carrying a vulnerability."""

    done = report.report_issue(tmp_path, _asked(kind="security", submit=True))
    printed = capsys.readouterr().out

    assert done.result.outcome == "INCOMPLETE"
    assert issue.PRIVATE_ROUTE in printed
    assert not _drafted(tmp_path)


def test_a_vulnerability_that_is_not_being_submitted_may_still_be_drafted(tmp_path: Path, capsys):
    """The refusal is about the route, not about the subject. Somebody writing down what
    they found, locally, is exactly what should happen next — and refusing that would leave
    them with nothing to disclose privately from."""

    done = report.report_issue(tmp_path, _asked(kind="security", submit=False))
    capsys.readouterr()

    assert done.result.outcome == "PASS"
    assert _drafted(tmp_path)


def test_a_scan_finding_outranks_the_security_route_because_it_is_checked_first(
    tmp_path: Path, capsys
):
    """Both refusals apply and only one can be reported. The scan comes first because it is
    the stronger statement: these bytes may not leave at all, by any route."""

    both = _asked(
        kind="security",
        submit=True,
        what_happened=f"it printed {Path.home()}/.ssh/id_rsa in the log",
    )

    done = report.report_issue(tmp_path, both)
    printed = capsys.readouterr().out

    assert done.result.outcome == "INCOMPLETE"
    assert issue.PRIVATE_ROUTE not in printed
    assert not _drafted(tmp_path)
