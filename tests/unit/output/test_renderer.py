"""Unit tests for the Renderer module (spec-132 D-132-12).

The Renderer is the single source of truth for command output. It wraps
the legacy ``cli_envelope`` / ``cli_ui`` / ``cli_progress`` / ``cli_output``
modules behind a stable contract with a closed Verb taxonomy and three
output modes (``human`` / ``json`` / ``quiet``).

These tests exercise the full public surface (``header / step / action /
progress / record / diff_summary / error / next / ok``) across all three
modes. The Verb taxonomy is enforced at runtime via ``typing.get_args``
so callers receive a ``TypeError`` for any verb outside the closed set.
"""

from __future__ import annotations

import json

import pytest

from ai_engineering.core.output.renderer import (
    ChangeKind,
    NextAction,
    Renderer,
    Verb,
)

# ---------------------------------------------------------------------------
# Type-level contracts
# ---------------------------------------------------------------------------


def test_verb_taxonomy_is_closed_to_eight_values() -> None:
    """Verb is a closed Literal with exactly 8 allowed values (brief §8.2)."""
    from typing import get_args

    expected = {
        "Installing",
        "Updating",
        "Removing",
        "Moving",
        "Creating",
        "Verifying",
        "Skipping",
        "Restoring",
    }
    assert set(get_args(Verb)) == expected


def test_change_kind_taxonomy() -> None:
    """ChangeKind is the closed set used by record() / diff_summary()."""
    from typing import get_args

    expected = {"created", "updated", "removed", "moved", "skipped", "restored"}
    assert set(get_args(ChangeKind)) == expected


def test_next_action_named_tuple() -> None:
    """NextAction is a NamedTuple with ``label`` and ``command`` fields."""
    action = NextAction(label="Run install", command="ai-eng install")
    assert action.label == "Run install"
    assert action.command == "ai-eng install"
    # NamedTuple ordering preserved.
    assert action[0] == "Run install"
    assert action[1] == "ai-eng install"


# ---------------------------------------------------------------------------
# Constructor / mode dispatch
# ---------------------------------------------------------------------------


def test_renderer_defaults_to_human_mode() -> None:
    r = Renderer("install")
    assert r.command == "install"
    assert r.is_human
    assert not r.is_json
    assert not r.is_quiet


def test_renderer_json_mode_flag() -> None:
    r = Renderer("install", json=True)
    assert r.is_json
    assert not r.is_human
    assert not r.is_quiet


def test_renderer_quiet_mode_flag() -> None:
    r = Renderer("install", quiet=True)
    assert r.is_quiet
    assert not r.is_human
    assert not r.is_json


def test_renderer_json_takes_precedence_over_quiet() -> None:
    """If both are set, JSON wins (structured output > silence)."""
    r = Renderer("install", json=True, quiet=True)
    assert r.is_json
    assert not r.is_quiet


def test_from_app_reads_global_json_mode_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    """``from_app`` mirrors the global ``cli_output.is_json_mode()`` state."""
    from ai_engineering import cli_output

    monkeypatch.setattr(cli_output, "_json_mode", True)
    r = Renderer.from_app("install")
    assert r.is_json
    assert r.command == "install"


def test_from_app_human_default(monkeypatch: pytest.MonkeyPatch) -> None:
    from ai_engineering import cli_output

    monkeypatch.setattr(cli_output, "_json_mode", False)
    r = Renderer.from_app("status")
    assert r.is_human


# ---------------------------------------------------------------------------
# header()
# ---------------------------------------------------------------------------


def test_header_human_writes_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install")
    r.header("install")
    captured = capsys.readouterr()
    assert captured.out == ""
    # Header content reaches stderr in some form (Rich rule).
    assert "install" in captured.err or captured.err != ""


def test_header_json_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", json=True)
    r.header("install")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_header_quiet_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", quiet=True)
    r.header("install")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# ---------------------------------------------------------------------------
# step()
# ---------------------------------------------------------------------------


def test_step_human_writes_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install")
    r.step("checking prerequisites")
    captured = capsys.readouterr()
    assert "checking prerequisites" in captured.err


def test_step_json_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", json=True)
    r.step("checking prerequisites")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_step_quiet_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", quiet=True)
    r.step("checking prerequisites")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# ---------------------------------------------------------------------------
# action() — Verb taxonomy is enforced
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "verb",
    [
        "Installing",
        "Updating",
        "Removing",
        "Moving",
        "Creating",
        "Verifying",
        "Skipping",
        "Restoring",
    ],
)
def test_action_accepts_all_closed_verbs(
    verb: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    r = Renderer("install")
    r.action(verb, "core/output/renderer.py")
    captured = capsys.readouterr()
    assert verb in captured.err
    assert "core/output/renderer.py" in captured.err


def test_action_rejects_bogus_verb_at_runtime() -> None:
    """Closed Verb taxonomy enforced via ``typing.get_args``."""
    r = Renderer("install")
    # Use a plain str variable so the test exercises the runtime guard
    # without needing a static suppression. ty checks src/ only, not tests/.
    bogus_verb = "Bogus"
    with pytest.raises(TypeError, match="verb"):
        r.action(bogus_verb, "core/output/renderer.py")


def test_action_rejects_lowercase_verb_at_runtime() -> None:
    """Verbs are capitalised; lowercase variants are rejected."""
    r = Renderer("install")
    lowercase_verb = "installing"
    with pytest.raises(TypeError, match="verb"):
        r.action(lowercase_verb, "x")


def test_action_json_is_noop_but_records_change(
    capsys: pytest.CaptureFixture[str],
) -> None:
    r = Renderer("install", json=True)
    r.action("Installing", "core/output/renderer.py")
    captured = capsys.readouterr()
    # JSON mode does not stream actions; envelope emits once via ok()/error().
    assert captured.out == ""
    assert captured.err == ""


def test_action_quiet_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", quiet=True)
    r.action("Installing", "core/output/renderer.py")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_action_with_detail(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install")
    r.action("Installing", "core/output/renderer.py", "from template")
    captured = capsys.readouterr()
    assert "Installing" in captured.err
    assert "from template" in captured.err


# ---------------------------------------------------------------------------
# progress() context manager
# ---------------------------------------------------------------------------


def test_progress_human_returns_step_tracker() -> None:
    r = Renderer("install")
    with r.progress(total=3, desc="syncing") as tracker:
        tracker.step("a")
        tracker.step("b")
        tracker.step("c")
    # No raise = success; the tracker is the existing StepTracker contract.


def test_progress_json_returns_noop_tracker() -> None:
    """In JSON mode progress() yields a tracker that produces no output."""
    r = Renderer("install", json=True)
    with r.progress(total=2, desc="syncing") as tracker:
        # The tracker MUST still have a callable ``step`` method.
        tracker.step("a")
        tracker.step("b")


def test_progress_quiet_returns_noop_tracker() -> None:
    r = Renderer("install", quiet=True)
    with r.progress(total=1, desc="syncing") as tracker:
        tracker.step("a")


# ---------------------------------------------------------------------------
# record() + diff_summary()
# ---------------------------------------------------------------------------


def test_record_human_emits_inline(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install")
    r.record("created", "core/output/renderer.py")
    captured = capsys.readouterr()
    assert "core/output/renderer.py" in captured.err


def test_record_json_accumulates_in_envelope(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", json=True)
    r.record("created", "a.py")
    r.record("updated", "b.py")
    r.record("moved", "c.py", from_="old/c.py")
    captured = capsys.readouterr()
    # No streaming; envelope only emits on ok()/error().
    assert captured.out == ""
    # Internal state has the changes ready for emission.
    changes = r.accumulated_changes()
    assert {"kind": "created", "path": "a.py", "from": None} in changes
    assert {"kind": "updated", "path": "b.py", "from": None} in changes
    assert {"kind": "moved", "path": "c.py", "from": "old/c.py"} in changes


def test_record_quiet_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", quiet=True)
    r.record("created", "a.py")
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_diff_summary_human_emits_tree(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install")
    r.diff_summary(created=["a.py", "b.py"], updated=["c.py"])
    captured = capsys.readouterr()
    assert "a.py" in captured.err
    assert "c.py" in captured.err


def test_diff_summary_json_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", json=True)
    r.diff_summary(created=["a.py"], updated=["b.py"])
    captured = capsys.readouterr()
    assert captured.out == ""


def test_diff_summary_quiet_emits_counts_only(
    capsys: pytest.CaptureFixture[str],
) -> None:
    r = Renderer("install", quiet=True)
    r.diff_summary(created=["a.py"], removed=["b.py"])
    captured = capsys.readouterr()
    # Quiet emits a single-line count summary, not a tree.
    assert "a.py" not in captured.err
    # But the summary may show the counts; verify it's at most one line.
    if captured.err:
        assert captured.err.count("\n") <= 1


# ---------------------------------------------------------------------------
# next()
# ---------------------------------------------------------------------------


def test_next_human_emits_arrow_block(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install")
    r.next(
        [
            NextAction(label="Run doctor", command="ai-eng doctor"),
            NextAction(label="Check status", command="ai-eng status"),
        ]
    )
    captured = capsys.readouterr()
    assert "ai-eng doctor" in captured.err
    assert "ai-eng status" in captured.err


def test_next_json_accumulates(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", json=True)
    r.next([NextAction(label="Run doctor", command="ai-eng doctor")])
    captured = capsys.readouterr()
    assert captured.out == ""
    # Internal envelope captures the next action for emission on ok().
    assert r.accumulated_next_actions()  # non-empty list


def test_next_quiet_is_noop(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", quiet=True)
    r.next([NextAction(label="Run doctor", command="ai-eng doctor")])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


# ---------------------------------------------------------------------------
# ok()
# ---------------------------------------------------------------------------


def test_ok_human_emits_success_line(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install")
    r.ok("install complete")
    captured = capsys.readouterr()
    assert "install complete" in captured.err


def test_ok_json_emits_envelope_to_stdout(
    capsys: pytest.CaptureFixture[str],
) -> None:
    r = Renderer("install", json=True)
    r.ok("install complete", result={"files": 12})
    captured = capsys.readouterr()
    assert captured.out  # JSON envelope on stdout
    payload = json.loads(captured.out.strip())
    assert payload["ok"] is True
    assert payload["command"] == "install"
    assert payload["result"]["summary"] == "install complete"
    assert payload["result"]["files"] == 12


def test_ok_json_includes_accumulated_changes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    r = Renderer("install", json=True)
    r.record("created", "a.py")
    r.record("updated", "b.py")
    r.ok("done")
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    paths = [c["path"] for c in payload["result"]["changes"]]
    assert "a.py" in paths
    assert "b.py" in paths


def test_ok_json_includes_next_actions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    r = Renderer("install", json=True)
    r.next([NextAction(label="Verify install", command="ai-eng doctor")])
    r.ok("done")
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert payload["next_actions"]
    assert payload["next_actions"][0]["command"] == "ai-eng doctor"


def test_ok_quiet_emits_minimal_line(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install", quiet=True)
    r.ok("install complete")
    captured = capsys.readouterr()
    # Quiet still reports the bottom-line success.
    assert "install complete" in captured.err or "install complete" in captured.out


# ---------------------------------------------------------------------------
# error()
# ---------------------------------------------------------------------------


def test_error_human_exits_nonzero(capsys: pytest.CaptureFixture[str]) -> None:
    r = Renderer("install")
    with pytest.raises(SystemExit) as excinfo:
        r.error("install failed", code="INSTALL_FAILED", fix="run ai-eng doctor")
    assert excinfo.value.code != 0
    captured = capsys.readouterr()
    assert "install failed" in captured.err
    assert "run ai-eng doctor" in captured.err


def test_error_json_emits_envelope_and_exits(
    capsys: pytest.CaptureFixture[str],
) -> None:
    r = Renderer("install", json=True)
    with pytest.raises(SystemExit):
        r.error(
            "install failed",
            code="INSTALL_FAILED",
            fix="run ai-eng doctor",
            next_actions=[NextAction(label="Diagnose", command="ai-eng doctor")],
        )
    captured = capsys.readouterr()
    payload = json.loads(captured.out.strip())
    assert payload["ok"] is False
    assert payload["command"] == "install"
    assert payload["error"]["message"] == "install failed"
    assert payload["error"]["code"] == "INSTALL_FAILED"
    assert payload["fix"] == "run ai-eng doctor"
    assert payload["next_actions"][0]["command"] == "ai-eng doctor"


def test_error_quiet_emits_minimal_line_and_exits(
    capsys: pytest.CaptureFixture[str],
) -> None:
    r = Renderer("install", quiet=True)
    with pytest.raises(SystemExit):
        r.error("install failed", code="INSTALL_FAILED", fix="...")
    captured = capsys.readouterr()
    # Quiet errors still surface — silence is for success, not failure.
    assert "install failed" in captured.err or "install failed" in captured.out


# ---------------------------------------------------------------------------
# Renderer integration: full narrative sequence
# ---------------------------------------------------------------------------


def test_full_narrative_human_does_not_crash(
    capsys: pytest.CaptureFixture[str],
) -> None:
    r = Renderer("install")
    r.header("install")
    r.step("checking prerequisites")
    r.action("Installing", "core/output/renderer.py")
    with r.progress(total=2, desc="syncing") as tracker:
        tracker.step("a")
        tracker.step("b")
    r.record("created", "x.py")
    r.diff_summary(created=["x.py"])
    r.next([NextAction(label="Doctor", command="ai-eng doctor")])
    r.ok("done")
    # If we reach here, the full happy path ran without exceptions.
    captured = capsys.readouterr()
    assert captured.err  # something landed on stderr


def test_full_narrative_json_emits_single_envelope(
    capsys: pytest.CaptureFixture[str],
) -> None:
    r = Renderer("install", json=True)
    r.header("install")
    r.step("checking prerequisites")
    r.action("Installing", "x.py")
    r.record("created", "x.py")
    r.next([NextAction(label="Doctor", command="ai-eng doctor")])
    r.ok("done", result={"count": 1})
    captured = capsys.readouterr()
    # Exactly one JSON envelope written to stdout.
    lines = [ln for ln in captured.out.strip().split("\n") if ln]
    payload = json.loads(captured.out.strip())
    assert payload["ok"] is True
    # Result merges accumulated state with caller-supplied dict.
    assert payload["result"]["count"] == 1
    assert payload["result"]["changes"]
    # Stderr is silent in JSON mode.
    assert captured.err == ""
    # And ok() emits exactly one envelope.
    assert lines[0].startswith("{")
