"""The contracts, as tests that fail.

Everything here is a rule this repository states about itself somewhere in prose. A rule
that exists only as a sentence is the failure family this rebuild exists to kill, so each
one appears once more here, where it has an exit code.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from ai_engineering import contract, paths, text

ROOT = Path(__file__).resolve().parents[1]

CEILING = contract.REPO_CEILING
DOCTRINE_CEILING = 150


def test_every_hook_is_classified_and_blocking_events_are_guards():
    """Registering telemetry as a gate turns this red with a message that names it."""
    import chain

    blocking = {"PreToolUse", "PostToolUse"}
    for event, rows in chain.TABLE.items():
        for name, _ in rows:
            module = __import__(name)
            kind = getattr(module.run, "hook_class", None)
            assert kind in ("guard", "telemetry"), f"{name} declares no class"
            if event in blocking and name not in chain.TELEMETRY:
                assert kind == "guard", (
                    f"{name} runs on {event}, which can block, and it is not a guard. "
                    f"A control that fails open on a blocking event is not a control."
                )
            if name in chain.TELEMETRY:
                assert kind == "telemetry", f"{name} is listed as telemetry and is a guard"


def test_no_guard_exits_zero_without_deciding():
    """Moved here from a semgrep rule, which meant it only ran where semgrep was installed:
    a guard that exits zero reports "no objection, go ahead", and that is the root pattern."""
    for path in paths.hooks().glob("*.py"):
        body = path.read_text()
        if "@guard(" in body:
            assert "sys.exit(0)" not in body, f"{path.name}: a guard exits zero somewhere"


def test_no_hook_exists_outside_the_dispatcher_table():
    """You cannot add an entry point without instrumentation, because the entry point
    does not exist until it is in that table, and that table is what emits."""
    import chain

    registered = {name for rows in chain.TABLE.values() for name, _ in rows}
    on_disk = {
        p.stem
        for p in paths.hooks().glob("*.py")
        if not p.stem.startswith("_") and p.stem != "chain"
    }
    assert on_disk == registered, (
        f"these files are hooks and are not in the table: {sorted(on_disk - registered)}; "
        f"these are in the table and do not exist: {sorted(registered - on_disk)}"
    )


def test_every_skill_meets_the_contract():
    block = 'name: a\ndescription: >-\n  one\n  two\nlicense: "MIT"\n'
    assert text.flat_yaml(block) == {"name": "a", "description": "one two", "license": "MIT"}
    problems = contract.audit(ROOT / ".agents" / "skills")
    assert not problems, "\n".join(problems)


def test_the_doctrine_is_short_and_filled_in():
    agents = (ROOT / "AGENTS.md").read_text().splitlines()
    assert len(agents) <= DOCTRINE_CEILING, (
        f"AGENTS.md is {len(agents)} lines. It is loaded in every session, in every "
        f"repository, forever. Everything that is not true in every session is a skill."
    )
    identity = (ROOT / "CONSTITUTION.md").read_text()
    assert "TODO:" not in identity, "our own CONSTITUTION.md still has TODO: markers"
    assert (ROOT / "CLAUDE.md").read_text().strip() == "@./AGENTS.md"


def test_the_line_ceiling_holds(tmp_path):
    with pytest.raises(ValueError):
        contract.repo_lines(tmp_path)  # a count over zero files is not a pass
    total = contract.repo_lines(ROOT)
    assert total <= CEILING, (
        f"{total} lines against a ceiling of {CEILING}. Raise it in a commit whose message "
        f"says why — that commit is the conversation you would otherwise never have had."
    )


def test_the_tests_do_not_outgrow_what_they_test(tmp_path):
    """A suite twice the size of the product is a suite being written to move a number.
    This exists because a sentence in contract.py claimed the ratio was three to one; it
    was written from no measurement and the real answer was 1.68, so the sentence became
    this."""
    with pytest.raises(ValueError):
        contract.test_ratio(tmp_path)  # a ratio over zero product lines is not a pass
    tests, product = contract.test_ratio(ROOT)
    assert tests / product <= contract.TEST_RATIO_MAX, (
        f"{tests} lines of test against {product} of product — {tests / product:.2f}x, over "
        f"{contract.TEST_RATIO_MAX}x. Either the product lost lines or the suite is being "
        f"padded; `just mutate` names the tests that kill nothing."
    )


def test_the_ioc_catalogue_leaves_ordinary_technical_prose_alone():
    """This shipped once and denied 61 of 73 files here: a double-quoted scalar read as if it
    were single-quoted became a top-level alternation, so the guard blocked every file holding
    the word "bash". Fragments below, so this file does not hold the words it tests with."""
    import injection_guard

    corpus = [
        "run ba" + "sh to build the image",
        "use s" + "h here, not zsh",
        "cu" + "rl the api and inspect the json",
        "base" + "64 encode the payload before storing it",
        "a gate CSS class controls the banner",
        "rotate credentials quarterly, per the runbook",
    ]
    firing = {text: injection_guard.hit(text) for text in corpus if injection_guard.hit(text)}
    assert not firing, (
        f"the catalogue fired on ordinary prose: {firing}. Every false positive here is a "
        f"person told they may not read their own file."
    )


def test_the_event_classes_are_a_closed_set():
    import _emit

    assert _emit.CLASSES == ("blocked", "allowed", "bypassed", "command", "error", "session")
    with pytest.raises(ValueError):
        _emit.emit("test", "heartbeat")


def test_nothing_free_text_leaves_the_machine():
    """Checked with a synthetic event carrying a canary, because an allow-list you did
    not test is a deny-list you did not notice."""
    import _otlp

    canary = "correct-horse-battery-staple"
    body = _otlp.as_logs(
        [
            {
                "cls": "blocked",
                "name": "injection_guard",
                "seq": 1,
                "ts": "now",
                "session": "s",
                "repo": "r",
                "machine": "m",
                "hash": "h",
                "data": {"reason": canary, "command": f"git push {canary}"},
            }
        ],
        "strict",
    )
    assert canary not in json.dumps(body), "a free-text field left the machine unhashed"


def test_the_guards_start_fast_enough_to_be_guards():
    """p95 under 200 ms. On the surfaces that time out and carry on, a slow guard is a
    disabled guard: here latency is a security property."""
    import time

    payload = json.dumps(
        {"tool_name": "Read", "tool_input": {"file_path": str(ROOT / "README.md")}}
    )
    timings = []
    for _ in range(5):
        started = time.perf_counter()
        subprocess.run(
            [sys.executable, str(paths.hooks() / "chain.py"), "PreToolUse"],
            input=payload,
            text=True,
            capture_output=True,
        )
        timings.append(time.perf_counter() - started)
    assert sorted(timings)[len(timings) // 2] < 0.2, f"the dispatcher took {timings}"


def test_a_denial_hands_back_the_bypass_that_unblocks_the_guard_that_denied(capsys):
    """Nothing asserted any denial message's content before this, which is how a wrong flag
    shipped: a loop_guard denial handed back the command that unblocks design_gate."""
    import _wrap

    with pytest.raises(SystemExit):
        _wrap.deny("loop_guard", "denied")
    assert "--guard loop_guard" in capsys.readouterr().err
