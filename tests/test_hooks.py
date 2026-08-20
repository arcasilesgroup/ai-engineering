"""The library the guards stand on.

The guards themselves are attacked by the adversarial suite. What is not attacked there is
everything underneath them: the two decorators that decide what a crash means, the record
they write into, the payload normaliser every surface depends on, and the exporter that
must never let free text off the machine. A silent failure in any of these takes all five
guards with it at once, and no guard test would notice.

Every test here writes inside tmp_path. Nothing reads the real home or the real chain.
"""

from __future__ import annotations

import ast
import io
import json
import os
import subprocess
import sys
import threading
import time
import tomllib
import uuid
from pathlib import Path

import _emit
import _otlp
import _wrap
import autoformat
import chain
import loop_guard
import no_verify_guard
import pytest
import self_protect
import session


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A throwaway clone and a throwaway framework home, so no test can write into the
    real record or the real repository."""
    root = tmp_path / "clone"
    (root / ".git").mkdir(parents=True)
    (root / ".git" / "ai-eng-repo-id").write_text("r0\n")  # skips the git subprocess
    house = tmp_path / "house"
    house.mkdir()
    (house / "machine.json").write_text(json.dumps({"machine_id": "m0"}))
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(house))
    monkeypatch.setenv("AI_ENG_SESSION", "s0")
    monkeypatch.chdir(root)
    return root


def grant(house, name, seconds=60):
    path = house / "cache" / "bypass.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"guard": name, "expires": time.time() + seconds, "reason": "why"}))
    return path


def links(root=None):
    return [json.loads(line) for line in _emit.chain_path(root).read_text().splitlines() if line]


# --- the central contract: what a failure means -------------------------------------


@pytest.mark.parametrize("blow_up", [ValueError, KeyboardInterrupt, MemoryError, SystemError])
def test_a_guard_that_crashes_denies_rather_than_waving_the_call_through(repo, capsys, blow_up):
    """The previous framework exited zero after catching an exception, so a guard that
    crashed reported "no objection, go ahead". A crash must read as a denial, including
    for the failures that are not ordinary Exceptions."""

    @_wrap.guard("loop_guard")
    def run(payload):
        raise blow_up("boom")

    with pytest.raises(SystemExit) as stop:
        run({})
    assert stop.value.code == 2
    assert "BLOCKED" in capsys.readouterr().err
    recorded = links()[-1]
    assert recorded["cls"] == "error" and recorded["data"]["outcome"] == "blocked"


@pytest.mark.parametrize("blow_up", [ValueError, TypeError, OSError, AttributeError])
def test_a_telemetry_hook_that_crashes_lets_the_action_stand_and_says_nothing(
    repo, capsys, blow_up
):
    """The mirror image: an observer that starts blocking work when it breaks is worse
    than no observer. It must exit quietly and put its own failure in the record instead
    of on the user's screen."""

    @_wrap.telemetry("autoformat")
    def run(payload):
        raise blow_up("boom")

    assert run({}) is None
    assert capsys.readouterr().err == ""
    assert links()[-1]["data"]["outcome"] == "ignored"


def test_a_guard_that_allows_writes_nothing_at_all(repo, capsys):
    """A clean pass is the common case, thousands of times a day. If it recorded an event
    the chain would be noise, and the blocks nobody can find are blocks nobody reads."""

    @_wrap.guard("loop_guard")
    def run(payload):
        return None

    assert run({}) is None
    assert capsys.readouterr().err == ""
    assert not _emit.chain_path().exists()


def test_a_guard_that_returns_a_reason_denies_with_that_reason(repo, capsys):
    """The model is shown this text verbatim and acts on it, so the reason the guard gave
    has to survive to the screen instead of being replaced by a generic refusal."""

    @_wrap.guard("loop_guard")
    def run(payload):
        return "the same edit, four times"

    with pytest.raises(SystemExit) as stop:
        run({"_dedup": True, "_fp": "ff"})
    assert stop.value.code == 2
    err = capsys.readouterr().err
    assert "BLOCKED: the same edit, four times" in err
    recorded = links()[-1]
    assert recorded["cls"] == "blocked"
    assert recorded["data"] == {"reason": "the same edit, four times", "fp": "ff"}


@pytest.mark.parametrize(
    ("name", "recipe"),
    [
        ("injection_guard", False),
        ("no_verify_guard", False),
        ("self_protect", False),
        ("loop_guard", True),
    ],
)
def test_only_flow_guards_hand_back_the_recipe_that_unblocks_them(capsys, name, recipe):
    """A model that is already obeying text injected into a file it read must not be
    handed the command that turns the security guard off. Flow guards may say it, because
    a person at a keyboard is the one who has to type it."""
    with pytest.raises(SystemExit):
        _wrap.deny(name, "denied")
    err = capsys.readouterr().err
    assert (f"--guard {name}" in err) is recipe
    assert f"[{name}] denied" in err


def test_every_blocking_guard_is_declared_security_or_flow():
    """The defect this closes shipped, and it bricked repositories.

    `_wrap.deny` prints the bypass recipe for any guard not in `SECURITY`, and
    `_wrap.take_bypass` honours a grant only for a guard in `FLOW`. A guard in neither set
    therefore printed `ai-eng exception --skip ... --guard <name>` on every denial while no
    grant it produced could ever be consumed — a remedy that cannot be run, handed to the
    person the denial just stopped. `claim_scope_guard` was that guard, and because it also
    failed closed on an *unreadable* `.ai/claim.json`, a corrupt file denied every edit in
    the repository including the edit that would repair it, with an impossible fix printed
    beside each denial.

    The guard is gone. This is what stops the next one: the two sets must partition every
    blocking row in the dispatcher, so a hook added to neither is red here rather than
    discovered by somebody who cannot get their repository back."""

    blocking = {
        name for event in ("PreToolUse", "PostToolUse") for name, _ in chain.TABLE[event]
    } - chain.TELEMETRY

    undeclared = sorted(blocking - _wrap.SECURITY - _wrap.FLOW)
    assert not undeclared, (
        f"{undeclared} can deny and is in neither SECURITY nor FLOW, so each denial prints a "
        "bypass recipe that take_bypass will never honour. Put it in one set or the other."
    )
    both = sorted(_wrap.SECURITY & _wrap.FLOW)
    assert not both, f"{both} is declared as having no bypass and as having one"
    stale = sorted((_wrap.SECURITY | _wrap.FLOW) - blocking)
    assert not stale, f"{stale} is classified and no longer blocks anything"


def test_a_denial_is_spelled_both_ways_so_the_surfaces_that_read_json_see_it(capsys):
    """Cursor reads a JSON reply instead of the exit code, and spells its fields
    snake_case where VS Code spells them camelCase. Drop either and one whole surface
    silently stops blocking."""
    with pytest.raises(SystemExit):
        _wrap.deny("loop_guard", "denied")
    reply = json.loads(capsys.readouterr().out)
    assert reply["permission"] == "deny" and reply["continue"] is False
    assert reply["user_message"] == reply["userMessage"] == "[loop_guard] denied"
    assert reply["stop_reason"] == reply["stopReason"] == "[loop_guard] denied"


def test_claude_gets_its_own_denial_protocol_and_everything_else_keeps_the_status(
    repo, monkeypatch, capsys
):
    """A denial used to be a JSON reply and exit 2 mixed together. Claude Code ignores the
    JSON on that exit path and reads stderr, and the model can then treat an automated gate
    the way it treats a person refusing permission and simply stop — observed twice in one
    session, each time with the turn-duration record three milliseconds after the denied
    tool result and no assistant message at all.

    So Claude gets the answer its own PreToolUse protocol documents: exit 0, the decision in
    JSON, the reason it is shown. No universal `continue: false` goes with it, because that
    is the field that ends the turn. Every other surface enforces by process status and
    still exits 2 naming the guard. The surface is decided by a field it sends — Claude's
    `transcript_path` — and never by where the tool was installed."""
    monkeypatch.setitem(chain.TABLE, "PreToolUse", [("loop_guard", r".*")])
    monkeypatch.setattr("loop_guard.run", _wrap.guard("loop_guard")(lambda payload: "go away"))
    call = {"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_use_id": "t1"}

    with pytest.raises(SystemExit) as stop:
        dispatch(monkeypatch, "PreToolUse", json.dumps({**call, "transcript_path": "/t.jsonl"}))
    assert stop.value.code == 0
    said = json.loads(capsys.readouterr().out)
    assert said["hookSpecificOutput"] == {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "[loop_guard] BLOCKED: go away",
    }
    assert "continue" not in said

    with pytest.raises(SystemExit) as stop:
        dispatch(monkeypatch, "PreToolUse", json.dumps({**call, "tool_use_id": "t2"}))
    assert stop.value.code == 2
    out = capsys.readouterr()
    assert json.loads(out.out)["continue"] is False
    assert "[loop_guard] BLOCKED: go away" in out.err


def test_a_denial_on_either_protocol_is_remembered_for_the_second_delivery(repo, monkeypatch):
    """The verdict cache keyed off exit 2, and Claude's denial exits 0. Without this the
    second delivery of a call two surfaces both report asks every guard again."""
    monkeypatch.setitem(chain.TABLE, "PreToolUse", [("loop_guard", r".*")])
    monkeypatch.setattr("loop_guard.run", _wrap.guard("loop_guard")(lambda payload: "go away"))
    call = {
        "tool_name": "Bash",
        "tool_input": {"command": "ls"},
        "tool_use_id": "t1",
        "transcript_path": "/t.jsonl",
    }
    with pytest.raises(SystemExit):
        dispatch(monkeypatch, "PreToolUse", json.dumps(call))
    assert chain.cached(chain.fingerprint(chain.normalise(call))) == {
        "deny": True,
        "by": "loop_guard",
        "message": "BLOCKED: go away",
    }


def test_a_bypass_is_single_use_and_only_for_the_guard_it_names(repo):
    """One grant from a person is one pass. If the file survived being read, one moment of
    consent would silently become a standing exemption."""
    house = _emit.home()
    grant(house, "loop_guard")
    assert _wrap.take_bypass("self_protect") is None  # not this guard's grant
    assert _wrap.take_bypass("loop_guard") == "why"
    assert _wrap.take_bypass("loop_guard") is None  # consumed
    grant(house, "loop_guard", seconds=-1)
    assert _wrap.take_bypass("loop_guard") is None  # expired
    (house / "cache" / "bypass.json").write_text('{"guard": "loop_guard", "reason": "forever"}')
    assert _wrap.take_bypass("loop_guard") is None  # no expiry is not a standing exemption
    (house / "cache" / "bypass.json").write_text("not json")
    assert _wrap.take_bypass("loop_guard") is None


@pytest.mark.parametrize(
    ("name", "denies"),
    [("loop_guard", False), ("injection_guard", True)],
)
def test_a_bypass_cannot_be_forged_for_a_security_guard(repo, name, denies):
    """A grant file naming a security guard must do nothing. If it worked, writing one file
    would be enough to switch off the guards that exist to stop exactly that."""
    grant(_emit.home(), name)

    @_wrap.guard(name)
    def run(payload):
        return "no"

    # the dispatcher fingerprints every call but marks only the ones that carry an id as
    # deduplicable, and only those are recorded with their fingerprint
    payload = {"_fp": "ff"}
    if denies:
        with pytest.raises(SystemExit):
            run(payload)
    else:
        assert run(payload) is None
        assert links()[-1]["cls"] == "bypassed"
        assert links()[-1]["data"]["fp"] == ""


# --- the record ---------------------------------------------------------------------


def test_emit_is_stdlib_only_and_assigns_opaque_operation_and_trace_ids(repo):
    """The hot path cannot pay for a package import, and correlation identifiers cannot
    encode the person, machine or clone that produced them. Each emitted record therefore
    carries two newly generated UUIDs, and its on-disk JSON has one canonical spelling."""
    source = _emit.Path(_emit.__file__).read_text()
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and not node.level:
            imports.add((node.module or "").partition(".")[0])
    assert imports <= sys.stdlib_module_names

    _emit.emit("loop_guard", "blocked", reason="first")
    _emit.emit("loop_guard", "blocked", reason="second")
    raw = [line for line in _emit.chain_path().read_text().splitlines() if line]
    events = [json.loads(line) for line in raw]
    identifiers = [event[field] for event in events for field in ("operation_id", "trace_id")]

    assert len(set(identifiers)) == 4
    assert all(uuid.UUID(identifier).version == 4 for identifier in identifiers)
    assert raw == [json.dumps(event, sort_keys=True, separators=(",", ":")) for event in events]


def test_id_generation_failure_never_becomes_authority(repo, monkeypatch, capsys):
    """Randomness is telemetry infrastructure too. If the OS cannot mint an ID, a guard
    must still reach its already-decided allow or deny result rather than acquire a new
    blocking opinion from the observer that tried to describe it."""

    def unavailable():
        raise OSError("randomness unavailable")

    monkeypatch.setattr(_emit.uuid, "uuid4", unavailable)
    assert _emit.emit("loop_guard", "blocked", reason="record only") is None
    assert not _emit.chain_path().exists()
    assert "could not record loop_guard/blocked" in capsys.readouterr().err


def test_append_rejects_chain_gaps_but_emit_remains_fail_open(repo, capsys):
    """A corrupt predecessor is not an empty chain: accepting that fallback silently
    restarts numbering and turns an observable gap into a genuine-looking branch. The
    integrity boundary refuses the append, while emit still cannot decide the caller's
    action and so reports its own failure without raising or changing the corrupt file."""
    path = _emit.chain_path()
    _emit.append(path, [{"cls": "session", "name": "first"}])
    first = links()[0]
    gap = {**first, "seq": 3, "prev": first["hash"]}
    gap["hash"] = _emit.digest(gap)
    path.write_text("\n".join(json.dumps(event) for event in (first, gap)) + "\n")
    before = path.read_bytes()

    with pytest.raises(ValueError, match="sequence"):
        _emit.append(path, [{"cls": "session", "name": "third"}])
    assert path.read_bytes() == before
    assert _emit.emit("session", "error", error="record only") is None
    assert path.read_bytes() == before
    assert "could not record session/error" in capsys.readouterr().err


def test_concurrent_appends_have_one_unbroken_sequence(repo):
    """Separate hook processes can finish together. Reading the head before opening the
    append handle lets all of them claim the same next sequence, so the writer must hold
    one inter-process lock across both operations rather than repair duplicates later."""
    writers = 16
    start = threading.Barrier(writers)
    failures = []

    def write(index):
        try:
            start.wait()
            _emit.append(_emit.chain_path(), [{"cls": "session", "index": index}])
        except BaseException as exc:
            failures.append(exc)

    threads = [threading.Thread(target=write, args=(index,)) for index in range(writers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert failures == []
    assert [event["seq"] for event in links()] == list(range(1, writers + 1))
    assert _emit.head(_emit.chain_path())[0] == writers


def test_append_never_follows_a_chain_symlink(repo):
    """The append boundary owns one exact file. Following a replacement symlink would
    turn telemetry into an arbitrary file write and validate one target before appending
    to another, so the target must remain byte-for-byte untouched."""
    path = _emit.chain_path()
    path.parent.mkdir(parents=True)
    target = repo.parent / "not-the-chain.jsonl"
    target.write_text("")
    try:
        path.symlink_to(target)
    except OSError:
        pytest.skip("this filesystem cannot create symlinks")

    with pytest.raises(OSError):
        _emit.append(path, [{"cls": "session"}])
    assert target.read_text() == ""


def test_a_failed_flush_keeps_a_partial_chain_and_its_sealed_buffer(repo):
    """Invalid durable JSON is an integrity failure, not an empty predecessor. Refusing
    it must also leave the already stamped in-clone buffer in place for diagnosis or a
    later repair; truncating either side would destroy the only observable evidence."""
    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text("[pin]\nversion='1'\n")
    _emit.emit("loop_guard", "blocked", reason="keep me")
    buffer = _emit.buffer_path(repo)
    buffered_before = buffer.read_bytes()
    path = _emit.chain_path(repo)
    path.parent.mkdir(parents=True)
    path.write_text('{"seq":1')

    with pytest.raises(ValueError, match="invalid JSON"):
        _emit.flush(repo)
    assert path.read_text() == '{"seq":1'
    assert buffer.read_bytes() == buffered_before


def test_a_line_from_another_machine_is_sealed_as_foreign_and_never_as_tampering(repo):
    """The failure this closes was found on the operator's own machine, not imagined.

    `stamp()` keys off `home()/buffer.key`, which `AI_ENGINEERING_HOME` redirects, while
    `buffer_path()` is repository-local and it does not. So any process with its own home —
    every test in this suite that isolates one — writes into the operator's real buffer with
    a key their machine cannot verify, and the next honest flush seals those lines as
    `outcome: "edited"`, which is the literal tamper marker.

    Measured consequence: 22 permanently BROKEN links, `ai-eng audit verify` failing for
    good, and `audit --anchor` refusing a footer, so no commit on that machine can ever be
    anchored again. The chain accused itself of an edit it never suffered.

    A line naming another machine cannot be stamped by this one's key and that is not
    evidence of tampering — it is evidence that somebody else's record arrived here. It is
    sealed as exactly that, and the chain still holds."""

    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text("[pin]\n version='1'\n")
    _emit.emit("loop_guard", "blocked", reason="ours")
    buffer = _emit.buffer_path(repo)

    # What a differently-homed process leaves behind: a well-formed event naming its own
    # machine, stamped with a key this one has never seen.
    theirs = {
        "ts": _emit.now(),
        "cls": "error",
        "name": "uninstall",
        "session": "ffffffffffff",
        "repo": _emit.repo_id(repo),
        "machine": "8b19b2341ada",
        "operation_id": "x",
        "trace_id": "y",
        "data": {"verb": "uninstall", "exit": 2},
        "stamp": "00" * 32,
    }
    with buffer.open("a", encoding="utf-8") as fh:
        fh.write(_emit.stable_json(theirs) + "\n")

    _emit.flush(repo)
    sealed = [json.loads(line) for line in _emit.chain_path(repo).read_text().splitlines()]
    assert len(sealed) == 2, sealed
    assert sealed[0]["data"]["reason"] == "ours"
    outcome = sealed[1]["data"]["outcome"]
    assert outcome == "foreign", f"a line from another machine was sealed as {outcome!r}"
    assert sealed[1]["data"]["machine"] == "8b19b2341ada"

    # And the chain still verifies: nothing here is an edit, so nothing may report one.
    from ai_engineering import audit

    assert not [why for kind, why in audit._chain_findings(sealed) if kind == "BROKEN"]


def test_the_digest_covers_the_body_and_only_the_body():
    """The hash has to change when anything in the event changes, and must not depend on
    the hash field itself or on key order — otherwise an edit is either undetectable or
    every honest link looks tampered with."""
    body = {"cls": "blocked", "name": "loop_guard", "data": {"reason": "a"}}
    assert _emit.digest(body) == _emit.digest({"name": "loop_guard", "cls": "blocked", **body})
    assert _emit.digest(body) == _emit.digest({**body, "hash": "anything"})
    assert _emit.digest(body) != _emit.digest({**body, "data": {"reason": "b"}})


def test_each_link_extends_the_one_before_it_across_separate_appends(repo):
    """Appends happen in different processes minutes apart. If a later one restarted the
    numbering or forgot the previous hash, the chain would break at every session boundary
    and the tamper evidence would mean nothing."""
    path = _emit.chain_path()
    assert _emit.head(path) == (0, "")
    _emit.append(path, [{"cls": "session", "n": 1}, {"cls": "session", "n": 2}])
    assert _emit.append(path, [{"cls": "session", "n": 3}]) == 3
    events = links()
    assert [e["seq"] for e in events] == [1, 2, 3]
    assert [e["prev"] for e in events] == ["", events[0]["hash"], events[1]["hash"]]
    assert all(_emit.digest(e) == e["hash"] for e in events)
    assert _emit.head(path) == (3, events[2]["hash"])


@pytest.mark.parametrize("tail", ["", "\n\n", '{"seq": 1}\n', "not json\n"])
def test_a_chain_whose_last_line_cannot_be_read_reports_an_empty_head(repo, tail):
    """head() must never raise. It runs inside the guard that is about to write, and a
    crash there is a denial of a call that had nothing wrong with it."""
    path = _emit.chain_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(tail)
    assert _emit.head(path) == (0, "")


def test_the_chain_lives_outside_every_clone_and_is_per_repository_and_machine(repo, monkeypatch):
    """The record has to survive `git clean`, a fresh clone and a deleted branch. Inside
    the working tree it would be deletable by the agent it is a record of."""
    path = _emit.chain_path()
    assert repo not in path.parents, "the record is inside the clone it records"
    assert path.parents[1] == _emit.home() / "state"
    assert (path.parent.name, path.name) == ("r0", "m0.jsonl")
    (repo / ".git" / "ai-eng-repo-id").write_text("r1\n")
    assert _emit.chain_path().parent.name == "r1"  # a different repository, a different chain
    (_emit.home() / "machine.json").write_text(json.dumps({"machine_id": "m1"}))
    assert _emit.chain_path().name == "m1.jsonl"  # a different machine, a different chain


def test_an_unpinned_repository_writes_straight_to_the_chain(repo):
    """Without a pin there is no `.ai/` to buffer into, so the event must go to the durable
    file immediately rather than being dropped on the floor."""
    _emit.emit("loop_guard", "blocked", reason="x")
    assert _emit.buffer_path() is None
    assert links()[-1]["data"] == {"reason": "x"}


def test_a_pinned_repository_buffers_and_the_flush_moves_the_buffer_into_the_chain(repo):
    """Flush is a move, not a discard. If it emptied the buffer without appending, every
    event of the session would be gone at the moment the session ended."""
    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text("[pin]\nversion='1'\n")
    _emit.emit("loop_guard", "blocked", reason="x")
    buf = _emit.buffer_path()
    assert buf == repo / ".ai" / "events.jsonl" and not _emit.chain_path().exists()
    assert _emit.flush(repo) == 1
    assert buf.read_text() == ""
    assert links()[-1]["data"] == {"reason": "x"} and links()[-1]["seq"] == 1
    assert _emit.flush(repo) == 0  # an empty buffer moves nothing


def test_an_event_class_outside_the_closed_set_is_refused_rather_than_recorded(repo):
    """The six classes are the vocabulary the whole record is read by. A typo must fail
    loudly at the call — silently dropping the event would lose exactly the decision the
    caller thought it had written down."""
    with pytest.raises(ValueError):
        _emit.emit("loop_guard", "recorded", reason="x")
    assert not _emit.chain_path().exists()


def test_a_record_that_cannot_be_written_does_not_change_what_the_caller_does(repo, capsys):
    """A full disk must not turn into a denied tool call. The failure is announced and the
    caller carries on."""
    monkey = pytest.MonkeyPatch()
    monkey.setattr(_emit, "append", lambda *a, **k: (_ for _ in ()).throw(OSError("full")))
    try:
        assert _emit.emit("loop_guard", "blocked", reason="x") is None
    finally:
        monkey.undo()
    assert "could not record loop_guard/blocked" in capsys.readouterr().err


def test_an_edited_buffer_is_sealed_as_the_error_that_says_it_was_edited(repo):
    """The event a guard has just written sits in a file inside the clone until the session
    ends. Someone who is blocked, edits `.ai/events.jsonl` to say the action was allowed and
    ends the session must not get that line back as a decision: it arrives without the stamp
    only this machine's key can make, so it is sealed as an error saying so, with what it
    claimed kept beside it rather than dropped, and `ai-eng audit verify` names the link.

    This was a strict xfail for as long as the buffer was written unhashed: the edit was
    hashed as genuine at the seal, and the marker was the alarm on it."""
    from ai_engineering import audit

    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text("[pin]\nversion='1'\n")
    _emit.emit("no_verify_guard", "blocked", reason="the truth")
    buf = _emit.buffer_path()
    buf.write_text(buf.read_text().replace("the truth", "a lie!!!"))
    assert _emit.flush(repo) == 1  # sealed, not dropped: dropping it destroys the evidence
    sealed = links()[-1]
    assert (sealed["cls"], sealed["data"]["outcome"]) == ("error", "edited")
    assert sealed["data"]["claimed"]["reason"] == "a lie!!!"  # kept, and no longer a decision
    assert "arrived edited" in " ".join(audit.verify(repo, anchors=False))

    key = _emit.home() / "buffer.key"
    assert repo not in key.parents and (key.stat().st_mode & 0o077) == 0
    assert _emit.stamp(sealed) != _emit.digest(sealed)  # a mark anything can make is a checksum


# --- the payload every surface is read through ---------------------------------------


# Read from the same function the dispatcher reads, so a spelling declared in an adapter
# is covered by this the day it is declared — and a spelling deleted from the floor is
# not quietly dropped from the parametrisation with it.
@pytest.mark.parametrize(("camel", "snake"), sorted(chain.adapter_aliases().items()))
def test_both_spellings_of_every_alias_arrive_in_one_shape(camel, snake):
    """VS Code and Cursor send camelCase where Claude Code sends snake_case. A guard that
    reads only one spelling sees an empty payload on the other surface and allows
    everything, which is how a surface is silently unguarded."""
    assert chain.normalise({camel: "v"})[snake] == "v"
    assert chain.normalise({snake: "v"})[snake] == "v"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ({}, {"tool_name": "", "tool_input": {"file_path": ""}}),
        ({"tool": "Bash"}, {"tool_name": "Bash", "tool_input": {"file_path": ""}}),
        ({"input": {"filePath": "a.py"}}, {"tool_input": {"file_path": "a.py"}}),
        ({"tool_input": "a string"}, {"tool_input": "a string"}),
        ({"tool_input": ["a", "list"]}, {"tool_input": ["a", "list"]}),
        (
            {"toolInput": {"notebook_path": "n.ipynb"}},
            {"tool_input": {"notebook_path": "n.ipynb", "file_path": "n.ipynb"}},
        ),
        (
            {"tool_input": {"file_path": "a.py", "notebook_path": "n.ipynb"}},
            {"tool_input": {"file_path": "a.py", "notebook_path": "n.ipynb"}},
        ),
    ],
)
def test_normalise_survives_every_shape_a_surface_sends(raw, expected):
    """A payload shape it did not expect makes a guard crash, and a crashing guard denies:
    that is how installing on a new surface denies the whole surface. The notebook tools
    send notebook_path and nothing else, so the two guards on those rows read an empty
    file_path and passed everything."""
    out = chain.normalise(raw)
    for key, value in expected.items():
        assert out[key] == value


@pytest.mark.parametrize(
    ("event", "tool", "expected"),
    [
        ("PreToolUse", "Read", ["injection_guard", "loop_guard"]),
        ("PreToolUse", "Bash", ["self_protect", "no_verify_guard", "loop_guard"]),
        ("PreToolUse", "BashOutput", ["loop_guard"]),
        ("PreToolUse", "", ["loop_guard"]),
        (
            "PreToolUse",
            "NotebookEdit",
            ["self_protect", "loop_guard"],
        ),
        ("PostToolUse", "mcp__linear__issue", ["injection_guard", "loop_guard"]),
        ("PostToolUse", "WebFetchExtra", ["loop_guard"]),
        ("SessionStart", "", ["session"]),
        ("Nonsense", "Read", []),
    ],
)
def test_the_matcher_picks_the_rows_it_claims_and_no_others(event, tool, expected):
    """The dispatcher does its own matching because VS Code parses Claude's matchers and
    then ignores them. Match too widely and a guard runs on tools it was never written
    for; too narrowly and a row in the table is coverage nobody has."""
    assert chain.selected(event, tool) == expected


def test_two_deliveries_of_one_call_share_a_fingerprint_and_a_retry_does_not(repo):
    """VS Code Copilot legitimately reads Claude's settings file, so the same call arrives
    twice and must be answered once. A genuine repeat has no shared call id, and treating
    it as a duplicate would blind the guard that watches for loops."""
    call = {"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_use_id": "t1"}
    assert chain.fingerprint(call) == chain.fingerprint(dict(call))
    assert chain.fingerprint(call) != chain.fingerprint({**call, "tool_use_id": "t2"})
    assert chain.fingerprint(call) != chain.fingerprint({**call, "tool_input": {"command": "rm"}})
    assert chain.deduplicable(call) is True
    assert chain.deduplicable({**call, "tool_use_id": ""}) is False
    assert chain.deduplicable({"tool_name": "Bash"}) is False


def dispatch(monkeypatch, event, raw):
    monkeypatch.setattr(sys, "stdin", io.StringIO(raw))
    monkeypatch.setattr(sys, "argv", ["chain.py", event])
    return chain.main()


@pytest.mark.parametrize("raw", ["", "   ", "\n"])
def test_an_empty_delivery_is_not_a_decision(repo, monkeypatch, raw):
    """Surfaces poll the hook with nothing in it. Denying on empty would block work that
    nobody asked about."""
    assert dispatch(monkeypatch, "PreToolUse", raw) == 0


@pytest.mark.parametrize("raw", ["not json", '{"tool_name": ', "}{"])
def test_a_payload_that_cannot_be_read_blocks(repo, monkeypatch, capsys, raw):
    """If the dispatcher cannot understand the call, no guard downstream can judge it, so
    the only honest answer is no."""
    with pytest.raises(SystemExit) as stop:
        dispatch(monkeypatch, "PreToolUse", raw)
    assert stop.value.code == 2
    assert "could not be read" in capsys.readouterr().err


@pytest.mark.parametrize("raw", ["[1, 2]", '"a string"', "17", "null"])
def test_a_payload_that_is_not_an_object_blocks_too(repo, monkeypatch, raw):
    """Valid JSON that is not an object still cannot be judged, so it has to be refused the
    same way an unreadable one is, rather than crashing the dispatcher out of the way."""
    with pytest.raises(SystemExit) as stop:
        dispatch(monkeypatch, "PreToolUse", raw)
    assert stop.value.code == 2


def test_a_guard_that_cannot_even_be_imported_blocks_but_a_broken_observer_does_not(
    repo, monkeypatch, capsys
):
    """A typo in a guard file, or a half-finished edit, must not quietly remove that guard
    from the line. The same breakage in a telemetry hook is skipped, because an observer
    that cannot load has no opinion to lose."""
    monkeypatch.setitem(chain.TABLE, "PreToolUse", [("no_such_hook", r".*")])
    with pytest.raises(SystemExit) as stop:
        dispatch(monkeypatch, "PreToolUse", '{"tool_name": "Bash"}')
    assert stop.value.code == 2
    assert "could not even be loaded" in capsys.readouterr().err
    monkeypatch.setattr(chain, "TELEMETRY", {"no_such_hook"})
    assert dispatch(monkeypatch, "PreToolUse", '{"tool_name": "Bash"}') == 0


def test_a_call_denied_once_stays_denied_and_only_a_call_with_an_id_is_remembered(
    repo, monkeypatch, capsys
):
    """The same tool call is delivered twice when two surfaces read the same settings file.
    The second delivery must get the first answer without asking again — and a repeat that
    carries no call id must not, or a genuine retry loop reads as a duplicate and the guard
    watching for loops goes blind."""
    monkeypatch.setitem(chain.TABLE, "PreToolUse", [])
    verdict = {"deny": True, "by": "loop_guard", "message": "no"}
    twice = {"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_use_id": "t1"}
    chain.remember(chain.fingerprint(chain.normalise(twice)), verdict)
    with pytest.raises(SystemExit):
        dispatch(monkeypatch, "PreToolUse", json.dumps(twice))
    assert "[loop_guard] no" in capsys.readouterr().err

    anonymous = {"tool_name": "Bash", "tool_input": {"command": "ls"}}
    chain.remember(chain.fingerprint(chain.normalise(anonymous)), verdict)
    assert dispatch(monkeypatch, "PreToolUse", json.dumps(anonymous)) == 0

    # the allow is written down too, or the second delivery re-asks every guard and the
    # dedup this module exists for only ever works for denials
    fresh = {"tool_name": "Bash", "tool_input": {"command": "pwd"}, "tool_use_id": "t9"}
    assert dispatch(monkeypatch, "PreToolUse", json.dumps(fresh)) == 0
    assert chain.cached(chain.fingerprint(chain.normalise(fresh))) == {"deny": False}


@pytest.mark.parametrize("sent", ["abc123", ""])
def test_the_session_the_surface_sent_is_the_session_everything_underneath_uses(
    repo, monkeypatch, sent
):
    """`session_id()` mints an identifier per process, so before this the state one call
    wrote lived in a file the next call never opened — 358 of them on one machine, each 48
    bytes and one entry long, and the guard that counts repeats could never reach three.
    Two dispatcher runs carrying the same session leave one cache file, not two. An empty
    string is not a session: one surface sends the field that way rather than omitting it,
    and adopting it would put every call on this machine into one bucket."""
    monkeypatch.setitem(chain.TABLE, "PreToolUse", [])
    for use_id in ("t1", "t2"):
        monkeypatch.setenv("AI_ENG_SESSION", "s0")
        call = {
            "sessionId": sent,
            "tool_name": "Bash",
            "tool_input": {"command": "ls"},
            "tool_use_id": use_id,
        }
        assert dispatch(monkeypatch, "PreToolUse", json.dumps(call)) == 0
    books = sorted(p.name for p in (repo.parent / "house" / "cache" / "verdicts").iterdir())
    assert books == [f"{sent or 's0'}.json"]


def test_a_denial_the_dispatcher_caches_carries_the_words_the_guard_used(repo, monkeypatch):
    """The cached verdict is what the second delivery of a call is shown. Writing a
    placeholder there tells the model it was blocked and never why, which is the same
    silence this product exists to cure."""
    monkeypatch.setitem(chain.TABLE, "PreToolUse", [("loop_guard", r".*")])
    monkeypatch.setattr("loop_guard.run", _wrap.guard("loop_guard")(lambda payload: "go away"))
    call = {"tool_name": "Bash", "tool_input": {"command": "ls"}, "tool_use_id": "t1"}
    with pytest.raises(SystemExit):
        dispatch(monkeypatch, "PreToolUse", json.dumps(call))
    assert chain.cached(chain.fingerprint(chain.normalise(call))) == {
        "deny": True,
        "by": "loop_guard",
        "message": "BLOCKED: go away",
    }


# --- self_protect: what is a write, and whose write it is ----------------------------


DENIED = [
    "cp /tmp/x ~/.claude/settings.json",
    "install -m 644 /tmp/x ~/.claude/settings.json",
    "truncate -s0 ~/.claude/settings.json",
    "dd if=/dev/null of=~/.claude/settings.json",
    "python -c \"open('~/.claude/settings.json', 'w').write('')\"",
    "python3 - <<'EOF'\nopen('~/.claude/settings.json', 'w')\nEOF",
    "echo x > ~/.claude/settings.json",
    "echo x >> .ai/config.toml",
    "rm ~/.agents/skills/ai-spec/SKILL.md",
    "sed -i '' .git/hooks/pre-commit",
    "echo x > ~/.config/opencode/skills/a",
    "echo x > ~/.pi/agent/skills/a",
]

ALLOWED = [
    "cat ~/.claude/skills/ai-spec/SKILL.md 2>/dev/null; ls ~/.claude/skills/ai-spec",
    "ls .git/hooks/\ngitleaks version 2>&1 | head -1",
    "git add .ai/config.toml",
    "git diff .ai/config.toml",
    "git show HEAD:.ai/config.toml",
    "git restore .ai/config.toml",
    "git stash push .ai/config.toml",
    "sed -n 1p .git/hooks/pre-commit",
    "echo hi > /tmp/ok.txt",
]


@pytest.mark.parametrize("command", DENIED)
def test_every_measured_way_of_writing_to_a_governed_path_is_denied(repo, command):
    """Six of these exited zero against the real dispatcher: a copy, an install, a
    truncate, a dd, a one-line Python program, and a redirection written with the home
    directory left as a tilde, which the protected list stores only in its expanded form.
    A guard that enumerates write verbs is a list nobody can finish; what it can do is fail
    towards denying too much, which is the direction a guard is allowed to fail in."""
    with pytest.raises(SystemExit) as stop:
        self_protect.run({"tool_input": {"command": command}})
    assert stop.value.code == 2


@pytest.mark.parametrize("command", ALLOWED)
def test_a_read_in_one_command_is_not_a_write_because_another_one_redirects(repo, command):
    """Both of these were denied in real sessions. The guard found a protected path
    anywhere in the command and a `>` anywhere else, joined two unrelated facts and
    reported a write that never happened — the first time from a `2>/dev/null` on the same
    line, the second from a redirect on a later, independent line. Staging, diffing,
    showing, restoring and stashing the pin are the same verb as the ones that write, so a
    rule that denied by mention would have to carve all of them out one at a time."""
    assert self_protect.run({"tool_input": {"command": command}}) is None


def test_the_protected_list_is_derived_from_the_table_the_installer_wires_from(repo):
    """The docstring claimed this could not fall behind the wiring, and it had: two skills
    roots the installer writes into were in no entry at all. Nothing derived may be empty
    either — the test is a substring test, and an empty string is a substring of every
    command on this machine, so one blank cell in the table would deny everything."""
    found = self_protect.protected()
    assert all(found)
    table = tomllib.loads(self_protect.POLICY.read_text())
    for surface in table["surface"]:
        if surface.get("skills"):
            assert any(surface["skills"].removeprefix("~/") in path for path in found), surface[
                "id"
            ]
        if surface.get("settings"):
            assert any(surface["settings"].rsplit("/", 1)[0].removeprefix("~/") in p for p in found)


# --- no_verify_guard: the configuration form, decided on its value -------------------


@pytest.mark.parametrize(
    "command, denies",
    [
        ("git config core.hooksPath /tmp/other", True),
        ("git config --global core.hooksPath /tmp/other", True),
        ("git config --local core.hooksPath ../elsewhere", True),
        ("git config --unset core.hooksPath", True),
        ("git config --unset-all core.hooksPath", True),
        ("git config --add core.hooksPath /tmp/other", True),
        ("git -c core.hooksPath=/tmp/other commit -m x", True),
        ("git config core.hooksPath ./git-hooks", False),
        ("git config --get core.hooksPath", False),
        ("git config --list", False),
    ],
    ids=[
        "pointed elsewhere",
        "pointed elsewhere globally",
        "pointed elsewhere with a relative path",
        "unset",
        "unset every one of them",
        "added rather than replaced",
        "overridden for one command",
        "pointed at the directory this install wires, written relatively",
        "read, not written",
        "not about the hooks path at all",
    ],
)
def test_the_hooks_path_is_judged_by_the_value_it_would_be_left_at(
    repo, monkeypatch, command, denies
):
    """`--no-verify` is one spelling of skipping the hooks; `git config core.hooksPath`
    is the durable one, and the guard did not read it at all — it denied the `-c` form on
    the verb and let every configuration form through. It is decided on the value now, and
    the value is resolved against the repository root first, because this repository's own
    bootstrap writes the relative form and a string comparison would deny the command that
    installs the hooks. Unset is a denial: it stops every hook and says nothing."""
    monkeypatch.setattr(no_verify_guard, "OURS", repo / "git-hooks")
    monkeypatch.setattr(no_verify_guard, "repo_root", lambda start=None: repo)
    if denies:
        with pytest.raises(SystemExit) as stop:
            no_verify_guard.run({"tool_input": {"command": command}})
        assert stop.value.code == 2
    else:
        assert no_verify_guard.run({"tool_input": {"command": command}}) is None


@pytest.mark.parametrize(
    "verb",
    ["commit", "push", "merge", "rebase", "am"],
    ids=["commit", "push", "merge", "rebase", "am"],
)
def test_no_verify_is_denied_on_every_verb_that_accepts_it(repo, monkeypatch, verb):
    """Found by a mutant, not by a reader. Narrowing the pattern from the five verbs to
    `commit` alone survived the whole suite: every test here spelled `git commit
    --no-verify`, so four of the five spellings were unasserted and the guard could have
    lost them silently. `git push --no-verify` skips `pre-push`, which is the hook that
    refuses a protected branch and scans the commits actually going to the server — the
    one denial in this repository with a recorded count behind it."""
    monkeypatch.setattr(no_verify_guard, "OURS", repo / "git-hooks")
    monkeypatch.setattr(no_verify_guard, "repo_root", lambda start=None: repo)

    with pytest.raises(SystemExit) as stop:
        no_verify_guard.run({"tool_input": {"command": f"git {verb} --no-verify"}})
    assert stop.value.code == 2


# --- loop_guard: what counts as the same call, and what counts as the same failure ---


def _loop(command: str, use_id: str = "", **extra) -> dict:
    return {
        "tool_name": "Bash",
        "tool_input": {"command": command},
        "tool_use_id": use_id,
        "_event": "PreToolUse",
        **extra,
    }


def test_three_identical_calls_in_one_session_deny_on_the_third(repo):
    """A real surface sends a distinct call id every time, so the repeat arm cannot key on
    anything carrying it. Three deliveries of the same command are one call repeated, and
    the third is where the guard says so."""
    loop_guard.run(_loop("git status", "t1"))
    loop_guard.run(_loop("git status", "t2"))
    with pytest.raises(SystemExit) as stop:
        loop_guard.run(_loop("git status", "t3"))
    assert stop.value.code == 2


def test_three_different_commands_in_one_session_are_not_a_loop(repo):
    """The failure arm keys on a deliberately coarse signature — the tool and the first
    token — so it can watch one tool failing with its arguments tweaked. Counting repeats
    by that same signature makes every git command in a session one key, and the third
    ordinary command of a session is denied. Measured, before this was split in two."""
    for index, command in enumerate(("git status", "git diff", "git log")):
        loop_guard.run(_loop(command, f"t{index}"))


def test_a_path_is_discriminated_by_its_tail_and_never_by_its_head(repo):
    """`signature` truncates to the last sixty characters, and that end is the rule: two
    files under one long temporary directory share every leading character, so truncating
    from the left makes them the same signature and five failures spread across two files
    become one wall. The repeat arm no longer uses this function, which is what left the
    rule with nothing behind it — `[-60:]` could be flipped to `[:60]` with the suite
    green."""
    prefix = "/" + "p" * 70 + "/"
    for name in ("aaa.py", "bbb.py"):
        for _ in range(3 if name == "aaa.py" else 2):
            loop_guard.run(
                {
                    "tool_name": "Edit",
                    "tool_input": {"file_path": prefix + name},
                    "_event": "PostToolUse",
                    "tool_response": {"is_error": True},
                }
            )
    failures = loop_guard.load()["failures"]
    assert len(failures) == 2, "two files under one long directory read as one signature"
    assert sorted(failures.values()) == [2, 3]
    # Five failures, and none of them a wall: the wall is five of ONE signature. Read from
    # the head they are one, and this call is denied.
    assert (
        loop_guard.run(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": prefix + "aaa.py"},
                "tool_use_id": "t1",
                "_event": "PreToolUse",
            }
        )
        is None
    )


def test_the_failure_map_is_bounded_by_signatures_not_by_the_window(repo):
    """Five failures of one signature has to survive anything else failing in between: a
    bound expressed in calls is a threshold the failure arm can never reach once a session
    is doing more than one thing. What the map may not do is grow without limit, so it
    keeps the most recently touched few and a signature still failing stays among them."""

    def fails(command: str) -> None:
        loop_guard.run(
            _loop(command, _event="PostToolUse", tool_response={"is_error": True}),
        )

    for index in range(loop_guard.FAILURES):
        fails("flaky-tool --run")
        fails(f"unrelated-{index}")
    with pytest.raises(SystemExit) as stop:
        loop_guard.run(_loop("flaky-tool --run", "t9"))
    assert stop.value.code == 2

    for index in range(loop_guard.SIGNATURES + 5):
        fails(f"spent-{index}")
    assert len(loop_guard.load()["failures"]) == loop_guard.SIGNATURES


def test_a_verdict_book_that_cannot_be_read_is_no_verdict_at_all(repo):
    """A corrupt cache must mean "ask the guards again", never "allowed". Failing the other
    way would make one bad file a permanent pass for every call in the session."""
    assert chain.cached("ff") is None  # no book at all
    chain.cache_file().parent.mkdir(parents=True, exist_ok=True)
    chain.cache_file().write_text("{ truncated")
    assert chain.cached("ff") is None
    chain.remember("ff", {"deny": False})  # writing over a corrupt book must not raise either
    chain.cache_file().unlink()
    chain.remember("ff", {"deny": False})
    assert chain.cached("ff") == {"deny": False}


# --- what leaves the machine ---------------------------------------------------------


@pytest.mark.parametrize("field", ["reason", "prompt", "path", "user", "note", "diff", "message"])
def test_a_field_nobody_thought_of_still_leaves_as_a_hash(repo, field):
    """The canary test only proves the fields it knew about. Any data key added to an event
    later — by us or by a guard — must leave as a hash and a length, or the first person to
    add one ships their user's file contents to a collector."""
    canary = "correct-horse-battery-staple"
    body = _otlp.as_logs([{"cls": "blocked", "data": {field: canary}}], "strict")
    text = json.dumps(body)
    assert canary not in text
    assert _otlp.opaque(canary)["sha256"] in text


# The last four are EP-277's: which surface an event came from, which version of it, which
# adapter translated it, and how a denial was expressed there. Written out here for the same
# reason as the rest — a list read from the module lets a deleted field delete its own test.
IN_THE_CLEAR = (
    "outcome",
    "phase",
    "verb",
    "exit",
    "guard",
    "fp",
    "archived",
    "ms",
    "id",
    "surface_id",
    "surface_version",
    "adapter_version",
    "deny_protocol",
)


@pytest.mark.parametrize("field", IN_THE_CLEAR)
def test_the_allow_list_is_exactly_what_passes_through_in_the_clear(field):
    """These fields are the ones the record is read by. The list is written out here
    rather than read from the module: parametrising over KEEP_DATA itself would let a
    deleted field quietly delete its own test, and `fp` and `id` are the two the record
    is correlated by — lose either and the digest still renders and says nothing."""
    assert _otlp.KEEP_DATA == IN_THE_CLEAR
    out = _otlp.redact({"cls": "blocked", "data": {field: "plain"}}, "strict")
    assert out["data"][field] == "plain"


def test_no_field_that_names_a_person_or_a_place_is_in_the_clear():
    """The allow-list grew, and the reason it may is that every name on it is software. A
    field naming a person, a host or a path would leave verbatim from every machine that
    exports, which is the one mistake this list cannot survive making once."""
    for named in ("user", "host", "hostname", "path", "email", "ip", "client", "repo_name"):
        assert named not in _otlp.KEEP_DATA, named


def test_only_the_first_two_words_of_a_command_leave():
    """A command line is where the secrets are: a token in an argument, a private path, a
    branch name that names a customer. The verb and its subcommand are enough to read the
    record by."""
    out = _otlp.redact({"data": {"command": "git push origin secret-customer-branch"}}, "strict")
    assert out["data"]["command"] == "git"


def test_redaction_cannot_be_turned_off_by_configuration():
    """`redact = "none"` sent every unlisted field verbatim, and it was a supported value in
    the pin. A configuration that disables a privacy control is a control whoever runs the
    exporter can switch off, and nothing downstream could tell a machine that had redacted
    from one that had been told not to.

    This pinned the escape hatch before spec 014 D-014-08 approved deleting it. Rule 4: hard
    delete, no shim — an unknown value redacts like every other, because the safe reading of
    a word nobody recognises is the strict one."""

    event = {"cls": "blocked", "data": {"reason": "plain"}}
    for mode in ("none", "off", "strict", "", "anything at all"):
        assert _otlp.redact(event, mode)["data"]["reason"] != "plain", mode


def test_an_event_carries_its_severity_and_its_five_attributes(repo):
    """A collector routes on severity and filters on attributes. Send everything as INFO
    and the errors are in the pile nobody alerts on."""
    records = _otlp.as_logs(
        [{"cls": "error", "name": "chain", "session": "s", "repo": "r", "machine": "m"}], "strict"
    )["resourceLogs"][0]["scopeLogs"][0]["logRecords"]
    assert (records[0]["severityText"], records[0]["severityNumber"]) == ("ERROR", 17)
    assert [a["key"] for a in records[0]["attributes"]] == [
        "aieng.cls",
        "aieng.name",
        "aieng.session",
        "aieng.repo",
        "aieng.machine",
    ]
    info = _otlp.as_logs([{"cls": "allowed"}], "strict")["resourceLogs"][0]["scopeLogs"][0]
    assert info["logRecords"][0]["severityText"] == "INFO"


class Reply:
    """The smallest thing urlopen's context manager can be."""

    def __init__(self, status, payload):
        self.status, self.payload = status, payload

    def read(self):
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.mark.parametrize(
    ("payload", "delivered"),
    [
        ({}, True),
        ({"partialSuccess": {}}, True),
        ({"partialSuccess": {"rejectedLogRecords": 3, "errorMessage": "schema"}}, False),
        ({"partialSuccess": {"rejectedLogRecords": "1"}}, False),
    ],
)
def test_a_two_hundred_is_not_a_delivery(repo, monkeypatch, payload, delivered):
    """The protocol returns the number of records it threw away inside a successful
    response. Read only the status code and the doctor reports a working destination while
    everything sent is being dropped — observability nobody has."""
    (_emit.home() / "config.toml").write_text(
        '[observability]\nendpoint = "http://collector.invalid:4318/"\nretention_days = 30\n'
    )
    monkeypatch.setattr(_otlp.urllib.request, "urlopen", lambda r, timeout=0: Reply(200, payload))
    assert _otlp.probe()[0] is delivered


def test_nothing_is_sent_anywhere_until_a_destination_is_configured(repo, monkeypatch):
    """Out of the box there is no endpoint. If a request went out regardless, every install
    would be phoning somewhere on every session end, and the probe must say plainly that
    there is nothing there rather than pass by default."""

    def refuse(*a, **k):
        raise AssertionError("a request left the machine with no endpoint configured")

    monkeypatch.setattr(_otlp.urllib.request, "urlopen", refuse)
    assert _otlp.post("logs", {}) == (0, 0, "no endpoint configured")
    assert _otlp.send_tail(5) == (0, 0, "logs not in the configured signals")
    assert _otlp.probe() == (False, "no response, 0 rejected no endpoint configured")


# --- the two that must never deny ----------------------------------------------------


@pytest.mark.parametrize("hook", [session, autoformat])
@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"_event": "SessionStart"},
        {"_event": "SessionEnd"},
        {"hook_event_name": "Stop"},
        {"tool_input": "not a dict"},
        {"tool_input": {"file_path": 12345}},
        {"tool_input": {"file_path": "/does/not/exist.py"}},
        {"tool_input": None, "_event": None},
    ],
)
def test_neither_telemetry_hook_can_deny_whatever_it_is_fed(repo, hook, payload):
    """These two run on the same blocking events as the guards. Whatever arrives, they must
    return rather than exit: an observer that can stop work is a guard nobody classified,
    and it would fail open the moment it mattered."""
    assert hook.run(payload) is None


def buffered(root):
    return [json.loads(line) for line in (root / ".ai" / "events.jsonl").read_text().splitlines()]


def test_the_session_hook_opens_the_trace_and_the_end_seals_the_buffer_into_the_chain(repo):
    """Returning None is not the same as working: this hook is what turns a session's
    events from a file inside the clone into links outside it, and because it is telemetry
    a crash on the way there is swallowed. So the record itself is asserted, and the two
    phases are asserted apart — the end that does not flush loses the whole session."""
    (repo / ".ai").mkdir()
    (repo / ".ai" / "config.toml").write_text("[pin]\nversion='1'\n")

    session.run({"_event": "SessionStart"})
    assert buffered(repo)[-1]["data"] == {"phase": "start", "id": "s0"}
    assert not _emit.chain_path().exists()  # nothing is durable until the session ends

    session.run({"_event": "SessionEnd"})
    assert [(e["cls"], e["data"]["phase"]) for e in links()] == [
        ("session", "start"),
        ("session", "end"),
    ]
    assert (repo / ".ai" / "events.jsonl").read_text() == ""


def test_the_formatter_runs_on_the_file_it_was_handed_and_on_nothing_else(repo, monkeypatch):
    """Also not something `is None` can see. A formatter that never fires is a hook that
    is only pretending, and one that fires on a path that does not exist spawns a process
    per edit to be told so."""
    ran = []
    monkeypatch.setattr(autoformat.shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setattr(autoformat.subprocess, "run", lambda cmd, **kw: ran.append(cmd))
    edited = repo / "a.py"
    edited.write_text("x=1\n")
    (repo / "notes.txt").write_text("hello\n")

    autoformat.run({"tool_input": {"file_path": str(edited)}})
    assert ran == [["ruff", "format", "--quiet", str(edited)]]

    autoformat.run({"tool_input": {"file_path": str(repo / "notes.txt")}})  # no formatter
    autoformat.run({"tool_input": {"file_path": str(repo / "gone.py")}})  # never written
    assert len(ran) == 1


def test_every_blocking_guard_carries_a_deliberate_defect():
    """A guard nothing is aimed at is a guard nobody has proven fires.

    `tests/mutation.py` breaks the product on purpose and fails if nothing notices, and its
    own recipe says it "points at the guards and nowhere else". It did not: of the four
    names on a blocking event, one had rows and three — the three that decide whether an
    action is allowed at all — had none between them. That is the fault the whole-tree
    apparatus was deleted for, at 1-in-4 instead of 0-in-6, and the sentence claiming
    otherwise had never been executed against the table it describes.

    So the sentence becomes this. A hook added to a blocking event with no row against it is
    red here, naming itself, rather than a gap somebody notices a year later.
    """

    import chain
    import mutation

    blocking = {
        name for event in ("PreToolUse", "PostToolUse") for name, _ in chain.TABLE[event]
    } - chain.TELEMETRY
    aimed = {row[0] for row in mutation.MUTANTS}
    unaimed = sorted(one for one in blocking if f"hooks/{one}.py" not in aimed)
    assert not unaimed, (
        f"{unaimed} can stop a call and no row of mutation.MUTANTS breaks it on purpose, so "
        "nothing in this repository would notice its rule being wrong. Write a row naming a "
        "boundary or a constant in each, or take the hook off the blocking event."
    )


def test_dispatcher_table_marks_blocking_hooks_as_guards_and_rejects_gaps(repo, monkeypatch):
    """The dispatcher reads the class, and reads it at dispatch time.

    A contract test can prove every hook in the tree declares itself. It cannot prove the
    dispatcher would refuse one that stopped declaring — a decorator lost in a refactor, a
    module swapped on disk between install and call. On an event where a call can be
    stopped, undeclared is refused; on telemetry it is skipped and recorded, because
    telemetry that fails closed would block Git.
    """

    import chain

    blocking = {"PreToolUse", "PostToolUse"}
    for event, rows in chain.TABLE.items():
        for name, _pattern in rows:
            module = __import__(name)
            declared = getattr(module.run, "hook_class", None)
            assert declared in ("guard", "telemetry"), name
            if event in blocking and name not in chain.TELEMETRY:
                assert declared == "guard", name
            # Both directions. The dispatcher now skips a hook whose name is in TELEMETRY,
            # so a guard added to that set would stop running instead of being refused.
            assert (name in chain.TELEMETRY) == (declared == "telemetry"), name

    class Undeclared:
        @staticmethod
        def run(payload):
            raise AssertionError("a hook with no class must never be run")

    monkeypatch.setattr(chain, "TABLE", {"PreToolUse": [("undeclared", r".*")]})
    monkeypatch.setattr(chain.importlib, "import_module", lambda name: Undeclared)
    monkeypatch.setattr(
        chain.sys, "stdin", io.StringIO(json.dumps({"tool_name": "Bash", "command": "ls"}))
    )
    monkeypatch.setattr(chain.sys, "argv", ["chain.py", "PreToolUse"])
    with pytest.raises(SystemExit) as blocked:
        chain.main()
    assert blocked.value.code != 0

    # A remembered verdict that is not exactly one well-formed verdict is not a verdict.
    # `{"deny": "no"}` used to read as "not a denial", which is how a malformed cache line
    # let a call past every guard in the table.
    for forged in ({"deny": "no"}, {"deny": None}, ["deny"], {}, {"deny": True}, 17):
        path = chain.cache_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"abc": forged}), encoding="utf-8")
        assert chain.cached("abc") is None, forged
    path.write_text(
        json.dumps({"abc": {"deny": True, "by": "loop_guard", "message": "BLOCKED: enough"}}),
        encoding="utf-8",
    )
    assert chain.cached("abc")["by"] == "loop_guard"
    path.write_text(json.dumps({"abc": {"deny": False}}), encoding="utf-8")
    assert chain.cached("abc") == {"deny": False}


def test_wrap_cures_plan_exception_naming_and_preserves_fail_closed_guard(
    repo, monkeypatch, capsys
):
    """Two things the wrapper owes, and the second is the one that had rotted.

    A flow guard's denial offers a person a way to grant one bypass. That line named
    `ai-eng plan`, a verb hard-renamed to `exception` — so the remedy printed under every
    flow denial was a command the product refuses. A remedy nobody can run is worse than
    none: they type it, it fails, and the next thing they look for is the way around.

    And the grant is now read the way it is written: one component at a time, nothing
    linked. A guard that honours a redirected grant passes where it should block, which is
    the failure contract this file exists to keep.
    """

    import _wrap

    # The recipe names the verb that exists, and no line anywhere still names the old one.
    with pytest.raises(SystemExit):
        _wrap.deny("loop_guard", "BLOCKED: enough")
    offered = capsys.readouterr().err
    assert 'ai-eng exception --skip "<reason>" --guard loop_guard' in offered
    assert "ai-eng plan" not in offered
    wrapper = Path(__file__).resolve().parents[1] / "hooks" / "_wrap.py"
    assert "ai-eng plan" not in wrapper.read_text(encoding="utf-8")

    # A security guard is still offered nothing at all.
    with pytest.raises(SystemExit):
        _wrap.deny("injection_guard", "BLOCKED: no")
    assert "can grant one bypass" not in capsys.readouterr().err

    # The grant, written and then read back through the same rules.
    store = _wrap.home() / "cache" / "bypass.json"
    store.parent.mkdir(parents=True, exist_ok=True)
    grant = {"guard": "loop_guard", "reason": "a person said so", "expires": time.time() + 900}
    store.write_text(json.dumps(grant), encoding="utf-8")
    assert _wrap.take_bypass("loop_guard") == "a person said so"
    assert not store.exists()  # consumed, so it is one bypass and not a standing one

    # Redirected at the leaf: nothing is honoured, and the file it pointed at is untouched.
    elsewhere = _wrap.home() / "somebody-elses-grant.json"
    elsewhere.write_text(json.dumps(grant), encoding="utf-8")
    store.symlink_to(elsewhere)
    assert _wrap.take_bypass("loop_guard") is None
    assert json.loads(elsewhere.read_text(encoding="utf-8")) == grant
    store.unlink()

    # Redirected at the directory above it: the same answer.
    outside = _wrap.home() / "somebody-elses-cache"
    outside.mkdir()
    (outside / "bypass.json").write_text(json.dumps(grant), encoding="utf-8")
    store.parent.rmdir()
    store.parent.symlink_to(outside, target_is_directory=True)
    assert _wrap.take_bypass("loop_guard") is None
    assert (outside / "bypass.json").exists()

    # And the two failure contracts are unchanged: a crashing guard denies, a crashing
    # telemetry hook does not.
    @_wrap.guard("crasher")
    def crashes(payload):
        raise RuntimeError("boom")

    @_wrap.telemetry("watcher")
    def watches(payload):
        raise RuntimeError("boom")

    assert crashes.hook_class == "guard" and watches.hook_class == "telemetry"
    with pytest.raises(SystemExit) as denied:
        crashes({})
    assert denied.value.code != 0
    assert watches({}) is None


def test_an_export_the_collector_rejected_is_recorded_and_not_treated_as_delivery(
    repo, monkeypatch
):
    """`_otlp.probe` already decides the hard part: a 2xx carrying rejected records is not
    a delivery, and it says so in its own return value. `session.py` called `send_tail` and
    threw the tuple away, so the one place that actually exports never read the answer.

    Silent partial loss is the worst shape this can take: the collector says 200, the
    operator's dashboard is missing events, and nothing anywhere in the record says a
    single line failed to land. Telemetry may not decide, and it may not stay quiet about
    its own failure either — that is what the `error` class is for."""

    import session as session_hook

    (repo / ".ai").mkdir(exist_ok=True)
    (repo / ".ai" / "config.toml").write_text("[pin]\nversion='1'\n")
    _emit.emit("loop_guard", "blocked", reason="something to send")

    monkeypatch.setattr(
        session_hook, "config", lambda root=None: {"observability": {"endpoint": "http://x"}}
    )
    otlp = paths_load_otlp()
    monkeypatch.setattr(otlp, "send_tail", lambda count: (200, 3, "3 rejected"))

    session_hook.run({"hook_event_name": "SessionEnd"})

    # In the buffer, not the chain: `flush` has already run, so the event describing the
    # export cannot be inside the batch it describes. It seals with the next session, which
    # is why the operator is also told now, on stderr.
    buffered = [
        json.loads(line)
        for line in _emit.buffer_path(repo).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    rejected = [row for row in buffered if row.get("data", {}).get("rejected")]
    assert rejected, "an export the collector rejected left no trace in the record"
    assert rejected[-1]["cls"] == "error", rejected[-1]


def paths_load_otlp():
    import _otlp

    return _otlp


def test_a_spelling_declared_only_in_an_adapter_reaches_the_guards(tmp_path, monkeypatch):
    """EP-081. `policy/adapters/*.json` described a translation table that nothing in the
    product read: the tests read it, the dispatcher normalised from its own hardcoded dict,
    and the two were free to disagree for as long as nobody looked. A contract with no
    consumer is a document, and a document is not a control.

    Planted first, then found — the shape every scan in this repository owes. A spelling
    that exists only in a data file has to arrive in the shape the guards read, or the file
    is decoration."""

    adapters = tmp_path / "adapters"
    adapters.mkdir()
    (adapters / "invented.adapter.json").write_text(
        json.dumps(
            {
                "schema": "urn:ai-engineering:surface-adapter:1",
                "schema_version": "1",
                "surface_id": "invented",
                "adapter_version": "1",
                # Our canonical name is the key and the surface's spelling is the value,
                # which is what the schema declares and what `adapter_aliases` inverts. This
                # fixture had it the other way round and passed, because the only adapter
                # shipping at the time mapped every name to itself.
                "translations": {"payload_field": {"tool_name": "toolNameInSomeOtherDialect"}},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(chain, "ADAPTERS", adapters)

    assert chain.normalise({"toolNameInSomeOtherDialect": "Bash"})["tool_name"] == "Bash"
    # And the floor survives beside it: an adapter adds spellings and can never remove one.
    assert chain.normalise({"toolName": "Edit"})["tool_name"] == "Edit"


def test_an_adapter_nobody_can_parse_costs_its_own_surface_and_no_other(tmp_path, monkeypatch):
    """The one thing normalisation must never do is fail. A guard that crashes is a guard
    that denies, and denying every call is how a whole surface is disabled by installing on
    it — so a broken data file loses its own spellings and nothing else."""

    adapters = tmp_path / "adapters"
    adapters.mkdir()
    (adapters / "broken.adapter.json").write_text("{not json", encoding="utf-8")
    (adapters / "fine.adapter.json").write_text(
        json.dumps({"translations": {"payload_field": {"tool_name": "aDialect"}}}), encoding="utf-8"
    )
    monkeypatch.setattr(chain, "ADAPTERS", adapters)

    assert chain.normalise({"aDialect": "Bash"})["tool_name"] == "Bash"
    assert chain.normalise({"toolName": "Edit"})["tool_name"] == "Edit"

    monkeypatch.setattr(chain, "ADAPTERS", tmp_path / "not-here")
    assert chain.normalise({"toolName": "Edit"})["tool_name"] == "Edit"


def test_every_event_says_which_surface_it_came_through_or_that_it_could_not_tell(monkeypatch):
    """EP-084 and D-016-03. The event body carried no surface and no adapter, while
    `_otlp.KEEP_DATA` kept `surface_id`, `surface_version`, `adapter_version` and
    `deny_protocol` in the clear — an export allow-list for four fields nothing produced.
    Every event in the chain was silent about where the decision was taken.

    `undetermined` is a value and not an absent key. A missing field reads as "this build is
    older"; this reads as "this run could not say", and the second is the true one on every
    surface that does not identify itself in what it sends."""

    monkeypatch.delenv("AI_ENG_SURFACE", raising=False)
    monkeypatch.delenv("AI_ENG_ADAPTER", raising=False)
    assert _emit.surface() == _emit.UNDETERMINED
    assert _emit.adapter() == _emit.UNDETERMINED

    monkeypatch.setenv("AI_ENG_SURFACE", "claude-code")
    monkeypatch.setenv("AI_ENG_ADAPTER", "1")
    assert _emit.surface() == "claude-code"
    assert _emit.adapter() == "1"


def test_the_adapter_version_is_read_from_the_file_that_did_the_translating():
    """One directory, two readers. An adapter that translates a payload and an adapter that
    stamps the record have to be the same file, or the record names a version that
    translated nothing."""

    assert chain.adapter_version("claude-code") == "1"
    assert chain.adapter_version("a-surface-with-no-adapter") == "undetermined"


def test_only_a_surface_that_identifies_itself_is_named_in_the_record(monkeypatch, tmp_path):
    """`policy/surfaces.toml` detects by an install path, which says a surface exists on this
    machine and not that this call came through it. `transcript_path` is the one thing a
    surface sends about itself, so it is the only thing allowed to name one — anything more
    would be a guess written into the chain as a fact, and the chain is the artefact that has
    to be trustworthy when everything else is in doubt."""

    monkeypatch.delenv("AI_ENG_SURFACE", raising=False)
    monkeypatch.setenv("AI_ENG_SESSION", "fixed")
    monkeypatch.setattr(chain.sys, "argv", ["chain.py", "PreToolUse"])
    monkeypatch.setattr(chain.sys, "stdin", io.StringIO(json.dumps({"toolName": "Read"})))
    monkeypatch.setattr(chain, "selected", lambda event, tool: [])
    chain.main()
    assert os.environ.get("AI_ENG_SURFACE") is None

    monkeypatch.setattr(
        chain.sys,
        "stdin",
        io.StringIO(json.dumps({"tool_name": "Read", "transcript_path": "/somewhere"})),
    )
    chain.main()
    assert os.environ["AI_ENG_SURFACE"] == "claude-code"
    assert os.environ["AI_ENG_ADAPTER"] == "1"


def test_an_endpoint_with_no_stated_retention_receives_nothing(tmp_path, monkeypatch):
    """EP-048's remaining half, and the shape it had to take.

    This exporter can say exactly what leaves — two allow-lists, and everything else a hash
    and a length. It cannot say how long the far end keeps it, because that is somebody
    else's system. What it can refuse is to send anything at all to a destination nobody has
    written a retention down for: the decision is made deliberately, in the file where the
    endpoint is chosen, and until it is made nothing is exported.

    `retention_days` is not validated against the destination and is not meant to be. It is
    the record that a person decided, which is the thing that was missing — `retention`
    appeared in no file in this repository."""

    home = tmp_path / "home"
    (home / ".ai").mkdir(parents=True)
    monkeypatch.setenv("AI_ENGINEERING_HOME", str(home / ".ai-engineering"))
    (home / ".ai-engineering").mkdir(parents=True, exist_ok=True)

    def configured(body: str) -> None:
        (home / ".ai-engineering" / "config.toml").write_text(body, encoding="utf-8")

    monkeypatch.setattr(
        _otlp,
        "config",
        lambda: __import__("tomllib").loads(
            (home / ".ai-engineering" / "config.toml").read_text(encoding="utf-8")
        ),
    )

    configured('[observability]\nendpoint = "http://collector.invalid:4318"\n')
    status, rejected, detail = _otlp.post("logs", {})
    assert (status, rejected) == (0, 0)
    assert "nobody has decided how long this is kept" in detail

    for bad in ("0", "-1", "true", '"thirty"'):
        configured(
            f'[observability]\nendpoint = "http://collector.invalid:4318"\nretention_days = {bad}\n'
        )
        assert "nobody has decided" in _otlp.post("logs", {})[2], bad

    # And with the decision made it gets past this gate and fails on the network instead,
    # which is the honest next answer for a host that does not exist.
    configured('[observability]\nendpoint = "http://collector.invalid:4318"\nretention_days = 30\n')
    assert "nobody has decided" not in _otlp.post("logs", {})[2]


def test_a_dispatcher_that_cannot_read_a_call_denies_it(tmp_path):
    """Measured before it was written: a `tool_name` that arrived as a number died outside
    every handler and the process exited 1.

    One is not a denial. Every surface reads a non-zero that is not two as an error in the
    hook and lets the call through, so the action passed without a guard having seen it —
    while `chain.py`'s own docstring promised a dispatcher that fails closed. The repair is
    a clause at the entry point, and its order is the whole of it: `deny` leaves through
    `SystemExit`, so a broader clause first would swallow every legitimate denial and print
    it back as a crash.
    """

    def ran(payload: str) -> int:
        done = subprocess.run(
            [sys.executable, str(Path(chain.__file__)), "PreToolUse"],
            input=payload,
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": str(Path(chain.__file__).parent)},
        )
        return done.returncode

    unreadable = '{"tool_name": 17, "tool_input": {}, "hook_event_name": "PreToolUse"}'
    assert ran(unreadable) == 2, "a call the dispatcher cannot read is denied, not allowed"

    # And the clause did not eat the ordinary answers on the way past.
    allowed = '{"tool_name": "Bash", "tool_input": {"command": "echo hello"}, ' '"hook_event_name": "PreToolUse"}'
    assert ran(allowed) == 0


def test_a_structured_denial_that_cannot_be_written_leaves_as_a_denial():
    """The structured protocol carries the whole decision in the text and exits 0, so a
    denial whose text never arrives is not a weaker denial — it is a success code with
    nothing beside it, and the surface allows the call.

    Measured against the unfixed file: with standard output closed, `deny(..., structured=
    True)` exited **0**, silently. The plain protocol was fine at 2 on this machine, and an
    earlier note that claimed 120 for both did not reproduce — the number that matters is
    the zero, because zero is the success code.

    So the write is taken where it can be answered, and the answer is `os._exit(2)`:
    `sys.exit` would hand control back to the interpreter's shutdown flush, which is the
    thing that already failed."""

    hooks = str(Path(_wrap.__file__).parent)

    def leaving(structured: bool, closed: bool) -> subprocess.CompletedProcess:
        call = f"import _wrap; _wrap.deny('probe', 'no', structured={structured})"
        if closed:
            return subprocess.run(
                ["bash", "-c", 'exec "$1" -c "$2" >&- 2>/dev/null', "_", sys.executable, call],
                capture_output=True,
                text=True,
                env={**os.environ, "PYTHONPATH": hooks},
            )
        return subprocess.run(
            [sys.executable, "-c", call],
            capture_output=True,
            text=True,
            env={**os.environ, "PYTHONPATH": hooks},
        )

    assert leaving(True, closed=True).returncode == 2, (
        "a structured denial nobody can read left with a success code, so the call was allowed"
    )
    assert leaving(False, closed=True).returncode == 2

    # And with somewhere to write, both protocols are exactly what they were.
    kept = leaving(True, closed=False)
    assert kept.returncode == 0 and '"permissionDecision": "deny"' in kept.stdout
    plain = leaving(False, closed=False)
    assert plain.returncode == 2 and '"permission": "deny"' in plain.stdout


def test_an_argument_of_only_whitespace_does_not_deny_in_the_guards_own_name():
    """`signature` truncates the first token of an argument, and an argument made only of
    whitespace splits to nothing — so it raised `IndexError` on `[0]`.

    `@guard` fails closed, so the crash became a denial, and the denial said this guard had
    crashed. That is correct behaviour on top of a defect, and it is the worst shape it
    could take: the guard that sees every call denying an ordinary one in its own name,
    reachable by the model, on a call that did nothing wrong. Guards that block ordinary
    work are how people learn to route around the layer."""

    for spelling in ("   ", "\t", "\n ", " \t\n"):
        assert loop_guard.signature(
            {"tool_name": "Bash", "tool_input": {"command": spelling}}
        ) == "Bash:", spelling

    # The truncation it is there for is unchanged: the last sixty characters of the first
    # token, so two files under one long temporary directory stay two calls.
    long = "/tmp/" + "d" * 80 + "/thing.py"
    assert loop_guard.signature({"tool_name": "Read", "tool_input": {"file_path": long}}) == (
        "Read:" + long[-60:]
    )
