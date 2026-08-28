"""The adapter contract, before any adapter exists to satisfy it.

A surface adapter translates between one editor's payload and this product's guards. That
makes it the place a fail-open bug hides best: a value nobody recognised, mapped to a
default, becomes an allow. So the contract is closed on both sides — every translation
table lists what it accepts and nothing else — and this file is what says so.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "policy" / "surface-adapter-v1.schema.json"

# The eight, frozen by spec 010 and not this wave's to change. `pi` and `zed` are
# instruction-only until a native hook exists, which the contract has to be able to say.
SURFACES = (
    "claude-code",
    "opencode",
    "codex-cli",
    "cursor",
    "copilot-cli",
    "vscode-copilot",
    "pi",
    "zed",
)


def _objects(node: Any) -> list[dict[str, Any]]:
    """Every schema object with properties, wherever it sits."""

    found = []
    if isinstance(node, dict):
        if node.get("type") == "object" and "properties" in node:
            found.append(node)
        for value in node.values():
            found.extend(_objects(value))
    elif isinstance(node, list):
        for value in node:
            found.extend(_objects(value))
    return found


def test_adapter_schema_is_closed_and_versioned():
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))

    assert schema["$id"] == "urn:ai-engineering:surface-adapter:1"
    assert schema["properties"]["schema_version"]["const"] == "1"
    assert schema["type"] == "object"

    # Closed everywhere, not only at the top. An open nested object is the same hole one
    # level down, and it is the level a reviewer stops reading at.
    for node in _objects(schema):
        assert node.get("additionalProperties") is False, node.get("title") or list(
            node["properties"]
        )

    required = set(schema["required"])
    assert required == {
        "schema",
        "schema_version",
        "surface_id",
        "adapter_version",
        "detection",
        "translations",
        "trust",
        # Task 16's field. Required and not optional: an adapter that declares no proof
        # requirement is one whose receipts prove only that something ran.
        "proof",
        # `EP-147`'s reachable half. The deny protocol had a sentence in
        # `translations.reply.deny` and no name, so nothing could compare one receipt's
        # protocol to another's — and the check-evidence schema's `protocol_id` slot is an
        # identifier and is forbidden on an automated receipt anyway. Required rather than
        # optional: an adapter that does not say how it denies is one whose denial nobody
        # can attribute to a mechanism.
        "deny_protocol",
    }
    assert schema["properties"]["surface_id"]["enum"] == list(SURFACES)

    # Detection is a native signal this product did not write. The contract records which,
    # and records inability to detect as an explicit answer rather than an absent one.
    detection = schema["properties"]["detection"]["properties"]
    assert set(detection) == {"signal", "written_by_us", "undetectable_reason"}
    assert detection["written_by_us"]["const"] is False

    # Four translation tables, each closed on both sides, so an unknown value has nowhere
    # to land. A default here is an allow nobody chose.
    tables = schema["properties"]["translations"]["properties"]
    assert set(tables) == {"payload_field", "lifecycle_event", "exit_meaning", "reply"}
    for name, table in tables.items():
        assert table["type"] == "object", name
        assert table["additionalProperties"] is False, name
        assert table["properties"], name

    # No heartbeat here. It is read from the discovery and invocation receipts, because an
    # adapter that could declare "I am loaded" is the deleted `proven` flag under a longer
    # name — and this contract is the file that wave wrote to stop exactly that.
    assert "heartbeat" not in schema["properties"]
    assert "heartbeat_is_not_declared" in schema["x-adapter-policy"]
    assert set(schema["properties"]["trust"]["properties"]) == {"required", "ceremony"}

    # The policy the reader must obey, declared beside the shape it applies to, so a reader
    # written later cannot quietly choose a friendlier rule.
    assert schema["x-adapter-policy"] | {"heartbeat_is_not_declared": ""} == {
        "heartbeat_is_not_declared": "",
        "unknown_value": "deny",
        "missing_translation": "INCOMPLETE",
        "undetectable_is_absent": False,
        "states": ["discovery", "invocation", "enforcement"],
        "state_never_implies_another": True,
        "t3_enforcement": "not_applicable",
    }


def _validator():
    """The shared reader, told about this contract's one extra keyword.

    Built on the same `_Schema` every other policy in this repository is read with, so an
    adapter cannot be accepted by a validator written to be kind to it."""

    from ai_engineering import intent

    class _AdapterSchema(intent._Schema):
        _KEYWORDS = intent._Schema._KEYWORDS | {"x-adapter-policy"}

    return _AdapterSchema(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_every_invalid_adapter_fixture_is_refused():
    """Invalid first, and refused before any adapter exists to satisfy them.

    Each case names the hole it opens rather than a number, because a fixture called
    `invalid_7` tells the next reader nothing about what stopped being true."""

    cases = json.loads((ROOT / "tests" / "fixtures" / "surface-adapter-v1.json").read_text("utf-8"))
    schema = _validator()

    assert len(cases["invalid"]) >= len(SURFACES), "fewer holes named than there are surfaces"

    # Each invalid case must fail for the reason it names and not for an accident, so every
    # one of them still carries all eight required keys. A fixture that is refused because
    # it forgot something unrelated proves the schema rejects malformed JSON, which nobody
    # doubted, and proves nothing about the field it was written for.
    required = set(json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["required"])
    for case in cases["invalid"]:
        assert required <= set(case["record"]), case["why"]
    for case in cases["valid"]:
        assert schema.valid(case["record"]), case["why"]
    for case in cases["invalid"]:
        assert not schema.valid(case["record"]), case["why"]

    # Every closed field has at least one case that breaks it, so adding a field without a
    # fixture is a field nobody proved closed.
    closed = (
        "surface_id",
        "detection",
        "payload_field",
        "lifecycle_event",
        "exit_meaning",
        "reply",
        "trust",
        "adapter_version",
        "schema",
        "proof",
        "deny_protocol",
    )
    reasons = " ".join(case["why"] for case in cases["invalid"]).lower()
    named = {
        "surface_id": "ninth surface",
        "detection": "detection",
        "payload_field": "payload field",
        "lifecycle_event": "lifecycle event",
        "exit_meaning": "exit code",
        "reply": "reply shape",
        "trust": "trust",
        "adapter_version": "no version",
        "schema": "another schema",
        "proof": "proof requirement is blank",
        "deny_protocol": "deny protocol written as the sentence",
    }
    for field in closed:
        assert named[field] in reasons, field


def _receipt(surface: str, state: str, *, finished: str, outcome: str = "PASS") -> dict[str, Any]:
    return {
        "schema": "urn:ai-engineering:check-evidence:1",
        "schema_version": "1",
        "kind": "automated",
        "id": f"{surface}.{state}",
        "applicability": "applicable",
        "command": f"just prove-{state}",
        "tool_version": "1.0.0",
        "input_digest": "sha256:" + "0" * 64,
        "artifact_digest": "sha256:" + "1" * 64,
        "started_at": finished,
        "finished_at": finished,
        "max_age_seconds": 86_400,
        "outcome": outcome,
    }


def test_discovery_invocation_and_enforcement_are_separate_receipts(tmp_path):
    """The defect this wave exists for: one word answering three questions.

    A surface can list the skills and be unable to run them. It can run them and never be
    able to stop anything. So each state is read from its own receipt, a missing one is
    unproven for that state alone, and no state is ever allowed to speak for another."""

    from datetime import UTC, datetime, timedelta

    from ai_engineering import surface

    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
    fresh = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    root = tmp_path / "repository"
    (root / surface.RECEIPTS).mkdir(parents=True)

    def write(name: str, record: dict[str, Any] | None) -> None:
        path = root / surface.RECEIPTS / f"{name}.json"
        if record is None:
            path.unlink(missing_ok=True)
        else:
            path.write_text(json.dumps(record), encoding="utf-8")

    assert surface.STATES == ("discovery", "invocation", "enforcement")

    # Nothing written: every state is unproven, with exactly one exception — the two
    # instruction-only surfaces cannot deny, so their enforcement is answered rather than
    # waiting to be proved. An answer is not a gap.
    empty = surface.read(root, now=now)
    assert len(empty.rows) == len(SURFACES) * len(surface.STATES)
    answered = {
        (row.surface, row.state) for row in empty.rows if row.code == surface.NOT_APPLICABLE
    }
    assert answered == {("pi", "enforcement"), ("zed", "enforcement")}
    assert {row.outcome for row in empty.rows if row.code != surface.NOT_APPLICABLE} == {
        "INCOMPLETE"
    }
    assert empty.result.outcome == "INCOMPLETE"

    # Discovery proved, and it proves only itself. This is the whole point of the wave:
    # visibility never proves invocation, and invocation never proves denial.
    write("claude-code.discovery", _receipt("claude-code", "discovery", finished=fresh))
    seen = surface.read(root, now=now)
    # Both halves of each verdict. A status with no code beside it leaves the reason free to
    # be anything, and the reason is what tells a proved surface from an unproven one — the
    # measured lever here is 2.0 mutants for each assertion made whole, and no new case.
    assert seen.state("claude-code", "discovery").outcome == "PASS"
    assert seen.state("claude-code", "discovery").code == surface.PROVEN
    assert seen.state("claude-code", "invocation").outcome == "INCOMPLETE"
    assert seen.state("claude-code", "invocation").code == surface.RECEIPT_MISSING
    assert seen.state("claude-code", "enforcement").outcome == "INCOMPLETE"
    assert seen.state("claude-code", "enforcement").code == surface.RECEIPT_MISSING

    # A receipt that names another surface's state does not tick this one.
    write("opencode.invocation", _receipt("claude-code", "invocation", finished=fresh))
    borrowed = surface.read(root, now=now)
    assert borrowed.state("opencode", "invocation").outcome == "INCOMPLETE"
    assert borrowed.state("opencode", "invocation").code == surface.RECEIPT_MISMATCH
    assert borrowed.state("claude-code", "invocation").outcome == "INCOMPLETE"

    # A check that ran and failed is decided, and says so rather than reading as unproven.
    write(
        "cursor.enforcement",
        _receipt("cursor", "enforcement", finished=fresh, outcome="FAIL"),
    )
    failed = surface.read(root, now=now)
    assert failed.state("cursor", "enforcement").outcome == "FAIL"
    assert failed.state("cursor", "enforcement").code == surface.EXECUTED_FAIL
    assert failed.result.outcome == "FAIL"

    # A stale receipt is unproven, not passed: a denial that executed a year ago says
    # nothing about the surface as it is now.
    old = (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    write("codex-cli.discovery", _receipt("codex-cli", "discovery", finished=old))
    stale = surface.read(root, now=now)
    assert stale.state("codex-cli", "discovery").outcome == "INCOMPLETE"
    assert stale.state("codex-cli", "discovery").code == surface.RECEIPT_STALE

    # T3 surfaces cannot deny, so enforcement is not applicable rather than unproven — and
    # a denial receipt for one is refused rather than believed.
    for instruction_only in ("pi", "zed"):
        assert surface.read(root, now=now).state(instruction_only, "enforcement").code == (
            surface.NOT_APPLICABLE
        )
        write(
            f"{instruction_only}.enforcement",
            _receipt(instruction_only, "enforcement", finished=fresh),
        )
        claimed = surface.read(root, now=now).state(instruction_only, "enforcement")
        assert claimed.outcome == "FAIL", instruction_only
        assert claimed.code == surface.CANNOT_ENFORCE, instruction_only


def test_coverage_prints_three_states_and_never_one_word_for_three_questions(tmp_path):
    """One word per surface answered three questions. Doctor now prints the three, and a
    state without a receipt prints as unproven rather than as nothing at all — an omitted
    row reads, to anyone counting, like a question that was not worth asking."""

    from datetime import UTC, datetime, timedelta

    from ai_engineering import doctor, surface

    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
    fresh = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    root = tmp_path / "repository"
    (root / surface.RECEIPTS).mkdir(parents=True)
    (root / surface.RECEIPTS / "claude-code.enforcement.json").write_text(
        json.dumps(_receipt("claude-code", "enforcement", finished=fresh)), encoding="utf-8"
    )

    facts = {fact.id: fact for fact in doctor.surface_states(root, now=now)}
    assert len(facts) == len(SURFACES) * len(surface.STATES)

    proved = facts["surface-claude-code-enforcement"]
    assert proved.status == "PASS"
    assert proved.summary == "claude-code · enforcement"
    assert "a denial has executed here" in (proved.detail or "")

    # Two questions nobody answered about the same surface, each unproven on its own.
    for state in ("discovery", "invocation"):
        assert facts[f"surface-claude-code-{state}"].status == "INCOMPLETE"

    # And the surfaces that cannot deny say so instead of waiting to be proved.
    for instruction_only in ("pi", "zed"):
        row = facts[f"surface-{instruction_only}-enforcement"]
        assert row.status == "PASS"
        assert "cannot deny" in (row.detail or "")

    # The legend defines each of the three, in the vocabulary the block already uses.
    legend = "\n".join(doctor.STATE_LEGEND)
    for state in surface.STATES:
        assert state in legend, state

    # And doctor carries them into the JSON envelope beside everything else it reports.
    import ai_engineering.paths as paths_module

    class _Fixed:
        def __init__(self, where):
            self.where = where

        def __call__(self, start=None):
            return self.where

    original = paths_module.repo_root
    checks = doctor.CHECKS
    coverage = doctor.coverage
    try:
        paths_module.repo_root = _Fixed(root)
        doctor.CHECKS = set()
        doctor.coverage = lambda where, **_: []
        published = {fact.id for fact in doctor.main([]).checks}
    finally:
        paths_module.repo_root = original
        doctor.CHECKS = checks
        doctor.coverage = coverage
    assert "surface-claude-code-enforcement" in published
    assert "surface-zed-enforcement" in published


def test_surface_proof_reports_three_states_and_invents_none(tmp_path, monkeypatch, capsys):
    """The command the proposal's exit criteria name, and the count it must not change.

    It answers per surface, prints the age of each proof beside it, and says INCOMPLETE for
    anything unreceipted rather than inventing a state. And it is a subcommand, not an
    eleventh verb: the two exact-ten assertions and the installed-wheel count are the
    evidence that nothing was added to the surface a person types."""

    from datetime import UTC, datetime, timedelta

    from ai_engineering import paths, report, surface

    now = datetime.now(UTC).replace(microsecond=0)
    fresh = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    root = tmp_path / "repository"
    (root / surface.RECEIPTS).mkdir(parents=True)
    (root / surface.RECEIPTS / "claude-code.discovery.json").write_text(
        json.dumps(_receipt("claude-code", "discovery", finished=fresh)), encoding="utf-8"
    )
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)

    # The clock is frozen for the read as well as the write. The receipt stamp is
    # second-truncated, so a real `now` taken later can cross a boundary and print
    # 7201s beside a proof written for exactly 7200 — the age is asserted, not sampled.
    class _Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now if tz is not None else now.replace(tzinfo=None)

    monkeypatch.setattr(report, "datetime", _Clock)

    result = report.main(["surfaces"])
    printed = capsys.readouterr().out

    # Unproven anywhere means unproven overall. One receipt does not make a surface proved.
    assert result.outcome == "INCOMPLETE"
    assert "claude-code" in printed
    assert "discovery" in printed
    assert "7200s" in printed, "the age of the proof is printed beside it"
    for state in surface.STATES:
        assert state in printed, state
    assert printed.count("INCOMPLETE") >= 2

    # No eleventh verb: the two counts this repository states about itself are untouched.
    verbs = (ROOT / "src" / "ai_engineering" / "cli.py").read_text(encoding="utf-8")
    assert verbs.count('": (\n        "') == 10
    matrix = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    assert 'test "$listed" = "10"' in matrix
    assert "surface" not in matrix.split("for verb in ")[1].split("; do")[0]


def test_the_coverage_word_is_earned_and_never_declared(tmp_path, monkeypatch):
    """The measured defect this wave exists for, closed at its source.

    OpenCode's row read BLOCKS because a field in a table said `proven = true`, and no
    denial had ever executed there. A flag we set cannot contradict us. The word now comes
    from the enforcement receipt, so the one-word block and the three-state block agree by
    construction — they read the same file — and a surface with no receipt reads UNPROVEN
    however confident the table is."""

    from datetime import UTC, datetime, timedelta

    from ai_engineering import doctor, surface, wiring

    now = datetime.now(UTC)
    fresh = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    root = tmp_path / "repository"
    (root / surface.RECEIPTS).mkdir(parents=True)

    rows = {row["id"]: row for row in wiring.table()["surface"]}
    every = set(rows)
    tier_two = [name for name, row in rows.items() if row["tier"] != "T3"]

    # Nothing receipted: not one row may say a denial has executed, whatever the table says.
    for name in tier_two:
        word, why = doctor.standing(rows[name], every, "", every, proved=frozenset())
        assert word == "UNPROVEN", name
        assert "no denial has ever run here" in why, name

    # One receipt, and only that surface's word changes.
    (root / surface.RECEIPTS / "opencode.enforcement.json").write_text(
        json.dumps(_receipt("opencode", "enforcement", finished=fresh)), encoding="utf-8"
    )
    proved = doctor.enforced(root, now=now)
    assert proved == frozenset({"opencode"})
    assert doctor.standing(rows["opencode"], every, "", every, proved=proved)[0] == "BLOCKS"
    for name in tier_two:
        if name != "opencode":
            assert doctor.standing(rows[name], every, "", every, proved=proved)[0] == "UNPROVEN"

    # The two blocks cannot disagree, because there is nothing left for them to disagree
    # about: both are the same receipt read twice.
    monkeypatch.setattr(doctor.paths, "repo_root", lambda start=None: root)
    words = {
        line.split()[1]: line.split()[2] for line in doctor.coverage(root) if line.startswith("  T")
    }
    states = {
        row.surface: row.outcome
        for row in surface.read(root, now=now).rows
        if row.state == "enforcement"
    }
    # One direction, and it is the one that matters. The word can never over-claim: no row
    # says a denial executed unless the receipt says so. The converse does not hold and
    # should not — the one-word block also folds in whether the surface is installed and
    # wired here, which the state block deliberately says nothing about.
    for name in tier_two:
        if words[name] == "BLOCKS":
            assert states[name] == "PASS", name


def test_no_surface_flag_can_assert_a_state_a_receipt_has_not_earned():
    """The field is deleted, not deprecated and not defaulted.

    A deprecated field is one somebody still reads, and a defaulted one is a claim with a
    quieter voice. The only way a surface can be said to have denied anything is a receipt,
    so the table has no way to say it — and this fails if it comes back under any spelling."""

    table = (ROOT / "policy" / "surfaces.toml").read_text(encoding="utf-8")
    rows = [line.strip() for line in table.splitlines() if not line.strip().startswith("#")]
    for spelling in ("proven", "is_proven", "denial_proven", "blocks", "covered"):
        assert not [row for row in rows if row.startswith(f"{spelling} ")], spelling

    # Nor may any schema declare the same claim, at any depth, under any container name.
    # The first version of this guard read only the top-level `properties` and matched four
    # words: a re-review showed that nesting the identical block one level down, or calling
    # it `liveness`, walked straight past. The claim is the field names, not the wrapper.
    claims = {"proven", "heartbeat", "blocks", "covered", "installed", "loaded", "observed_at"}

    def declared(node: Any) -> set[str]:
        found: set[str] = set()
        if isinstance(node, dict):
            found |= set(node.get("properties", {}))
            for value in node.values():
                found |= declared(value)
        elif isinstance(node, list):
            for value in node:
                found |= declared(value)
        return found

    for schema in sorted((ROOT / "policy").glob("*.schema.json")):
        named = declared(json.loads(schema.read_text(encoding="utf-8"))) & claims
        assert not named, f"{schema.name} declares {sorted(named)}"

    # And nothing reads one. A reader with no field is the half that would otherwise sit
    # there defaulting quietly to False and looking like it works.
    for module in ("doctor.py", "wiring.py", "init.py", "uninstall.py"):
        source = (ROOT / "src" / "ai_engineering" / module).read_text(encoding="utf-8")
        assert '["proven"]' not in source, module
        assert '"proven"' not in source, module


def test_a_file_somebody_typed_is_not_a_receipt(tmp_path):
    """Everything a review demonstrated reading as proven, and the honest case it refused.

    The flag this wave deleted could have walked back in as a filename: four keys in a
    file nobody reviews, and the coverage screen printed "a denial has executed here" over
    it. A receipt has to be a receipt before anything it says is worth reading."""

    from datetime import UTC, datetime, timedelta

    from ai_engineering import surface

    now = datetime(2026, 8, 15, 12, 0, 0, tzinfo=UTC)
    fresh = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    root = tmp_path / "repository"
    (root / surface.RECEIPTS).mkdir(parents=True)

    def standing(name: str, body: str) -> tuple[str, str]:
        (root / surface.RECEIPTS / f"{name}.json").write_text(body, encoding="utf-8")
        row = surface.read(root, now=now).state(*name.split("."))
        (root / surface.RECEIPTS / f"{name}.json").unlink()
        return row.outcome, row.code

    junk = json.dumps(
        {
            "id": "opencode.enforcement",
            "finished_at": fresh,
            "max_age_seconds": 86_400,
            "outcome": "PASS",
        }
    )
    assert standing("opencode.enforcement", junk) == ("INCOMPLETE", surface.RECEIPT_MALFORMED)

    # A receipt that says the check did not apply is a receipt saying it did not run.
    excused = _receipt("cursor", "enforcement", finished=fresh) | {
        "applicability": "not_applicable",
        "reason": "there is nothing to deny in this configuration",
    }
    assert standing("cursor.enforcement", json.dumps(excused)) == (
        "INCOMPLETE",
        surface.RECEIPT_MISMATCH,
    )

    # ...and on a surface that cannot deny, it is the honest thing to write, so it is taken.
    # With its reason, because the schema requires one — a record that says a check does
    # not apply and does not say why is not an excuse, it is a shrug.
    honest = _receipt("pi", "enforcement", finished=fresh) | {
        "applicability": "not_applicable",
        "reason": "pi is instruction-only and has no hook that can deny",
    }
    assert standing("pi.enforcement", json.dumps(honest)) == ("PASS", surface.NOT_APPLICABLE)

    # A human-attested receipt is not an automated one, whatever date it carries.
    attested = _receipt("codex-cli", "discovery", finished=fresh) | {"kind": "human"}
    assert standing("codex-cli.discovery", json.dumps(attested)) == (
        "INCOMPLETE",
        surface.RECEIPT_MALFORMED,
    )

    # Sixty kilobytes of nesting fits inside the size bound and used to take the whole
    # report down with it: doctor aborted mid-run and printed no terminal result at all.
    deep = '{"a":' * 9996 + "1" + "}" * 9996
    assert len(deep) < surface.MAX_BYTES if hasattr(surface, "MAX_BYTES") else True
    assert standing("vscode-copilot.discovery", deep) == (
        "INCOMPLETE",
        surface.RECEIPT_MALFORMED,
    )

    # WARN is a legal outcome, and calling it malformed taught the wrong vocabulary.
    warned = _receipt("cursor", "discovery", finished=fresh) | {"outcome": "WARN"}
    assert standing("cursor.discovery", json.dumps(warned)) == ("WARN", surface.WARNED)


def test_a_surface_state_that_ran_and_failed_makes_the_verdict_fail(tmp_path, monkeypatch):
    """It printed FAIL into the JSON envelope and returned PASS with exit 0.

    The production-ready block already makes this argument and is wired for it: a check
    that ran and failed is decided, so it counts. The surface block was wired the other
    way, which is a gate result this code did not observe."""

    from datetime import UTC, datetime, timedelta

    from ai_engineering import doctor, paths, surface

    now = datetime.now(UTC)
    fresh = (now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    root = tmp_path / "repository"
    (root / surface.RECEIPTS).mkdir(parents=True)
    (root / surface.RECEIPTS / "cursor.enforcement.json").write_text(
        json.dumps(_receipt("cursor", "enforcement", finished=fresh) | {"outcome": "FAIL"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)
    monkeypatch.setattr(doctor, "CHECKS", set())
    monkeypatch.setattr(doctor, "coverage", lambda where, **_: [])
    reported = doctor.main([])

    assert reported.result.outcome == "FAIL"
    assert reported.result.exit_code != 0
    failing = [fact.id for fact in reported.checks if fact.status == "FAIL"]
    assert failing == ["surface-cursor-enforcement"]
    assert "cursor · enforcement failed" in reported.remaining


def test_the_matrix_receipts_the_denial_it_already_executes():
    """The denial ran on three operating systems and fed nothing.

    That is why claude-code went from over-claiming on a flag to under-claiming despite
    real executed evidence — and it made the honest path harder than the dishonest one,
    which is the worst state to leave a control in. The step that denies now writes the
    receipt for what it just did, and the job reads it back through the product's own
    reader in the same run. Written, read, and never kept: the receipt is a runtime
    artifact, and the proof is that it was read, not that it survived."""

    matrix = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    step = matrix.split("a packaged guard actually denies, from the installed tree", 1)[1]
    step = step.split("      - name:", 1)[0]

    # The receipt is written only after the denial is proved, and it names what it ran.
    assert step.index("no_verify_guard") < step.index("claude-code.enforcement.json"), (
        "the receipt is written before the denial that earns it"
    )
    assert '"id": "claude-code.enforcement"' in step
    assert '"kind": "automated"' in step
    assert '"applicability": "applicable"' in step
    assert '"outcome": "PASS"' in step
    # The command as it was actually run, not prose wearing shell syntax. The first version
    # of this receipt said `python $guards/chain.py PreToolUse < a --no-verify payload`,
    # which parses as a redirect from a file called `a` — and this assertion passed over it,
    # because "chain.py PreToolUse" is inside both. The requirement binding that arrives
    # with each adapter compares this field; a value that cannot match is worse than none.
    ran = "uv run --no-project --python 3.12 python \\$guards/chain.py PreToolUse"
    assert f'"command": "{ran}"' in step

    # And it is read back by the product, not asserted by the workflow's own opinion —
    # reachably, which is the whole of the blocker this test did not catch. `report
    # surfaces` returns the worst of twenty-four rows and twenty-one are legitimately
    # unproven on a fresh machine, so under `set -eo pipefail` the read aborted the step and
    # every assertion after it was unreachable code.
    assert "ai-eng report surfaces | tee surfaces.txt || rc=$?" in step
    # With the trailing space, because SURFACE_PROVEN is a prefix of
    # SURFACE_PROVEN_WITH_WARNING — the same blindness this test was written to catch in
    # the workflow, left in the test that catches it.
    assert 'SURFACE_PROVEN "' in step

    # Nothing is kept. A receipt that survives the job is a claim about a machine that no
    # longer exists, which is the freshness defect this wave already met once.
    assert "upload-artifact" not in step
    # Grepped as commands rather than as text: the denial payload this step feeds the guard
    # is literally `git commit --no-verify -m x`, so a substring search finds the thing the
    # test exists to forbid inside the thing it exists to prove.
    run = [line.strip() for line in step.splitlines()]
    assert not [line for line in run if line.startswith(("git add", "git commit", "git push"))]

    # Pinned by digest, like the three steps P0 pinned and for the same reason: this step
    # is now the only executed evidence any surface has, and a later task that extends the
    # matrix must not edit what it extends. Moving it by a byte is a deliberate act.
    from hashlib import sha256

    assert sha256(step.encode()).hexdigest() == (
        "03aaf864af0d565b0755aa5c9a6aac7fa198037dd92338235c7fd5592d337bd3"
    )


def test_the_matrix_proves_discovery_and_invocation_separately():
    """What the job can prove, it receipts. What it cannot, it leaves unproven and says so.

    Nothing in CI runs Claude Code. We can place the skills where it looks and we can watch
    our own guard deny — we cannot watch the editor list a skill or invoke one, and a
    receipt for "the files are where they should be" would be a receipt for a weaker thing
    wearing the name of a stronger one. That is the substitution this whole wave exists to
    refuse, so the job asserts the two states stay unproven while the one it earned reads
    PASS. Three states, three answers, and two of them are `no`."""

    matrix = (ROOT / ".github" / "workflows" / "install-matrix.yml").read_text(encoding="utf-8")
    step = matrix.split("a packaged guard actually denies, from the installed tree", 1)[1]
    step = step.split("      - name:", 1)[0]

    # Exactly one receipt file is written, and it is the enforcement one.
    written = [line for line in step.splitlines() if ".ai/receipts/surface/" in line]
    assert len(written) == 1, written
    assert "claude-code.enforcement.json" in written[0]

    # And the job proves the other two did not follow it. A state that borrowed another's
    # answer would show here as PASS, which is the failure the three receipts exist for.
    assert "claude-code .*discovery .*SURFACE_RECEIPT_MISSING" in step
    assert "claude-code .*invocation .*SURFACE_RECEIPT_MISSING" in step


def test_an_inert_surface_still_reads_inert_when_another_one_is_unwired(monkeypatch, tmp_path):
    """`surfaces_alive` returns a *tuple* — message and cure — as soon as any surface has
    no entry of ours, and the coverage block does `inert = surfaces_alive(root) or ""`.
    A tuple is not a string, so `surface["name"] in inert` stops being a substring test and
    becomes an exact-element test, and it is never true.

    The consequence is the one its own comment forbids: the two surfaces that fail
    *silently* — Codex without its trust ceremony, OpenCode whose plugin was dropped with
    no error and no log — print as `installed and wired`, which reads healthier than
    UNPROVEN, on a machine where assertion 21 is telling the person they are dead.

    Nothing reached this. Every existing case has either all surfaces wired or none of
    them, and the bug needs one of each."""

    from ai_engineering import doctor, wiring

    rows = [
        {"id": "codex-cli", "name": "Codex CLI", "tier": "T2", "trust_required": True},
        {"id": "cursor", "name": "Cursor", "tier": "T2"},
    ]
    monkeypatch.setattr(wiring, "detect", lambda only=None: rows)
    monkeypatch.setattr(wiring, "wired", lambda: ([rows[0]], [rows[1]]))
    monkeypatch.setattr(doctor.paths, "home", lambda: tmp_path)

    said = doctor.surfaces_alive(None)
    message = said[0] if isinstance(said, tuple) else said
    assert "Cursor: no entry of ours" in message, said
    assert "Codex CLI: installed but INERT" in message, said

    # Through `coverage`, not through `standing` with a hand-made argument: the defect is
    # in what `coverage` passes down, so a test that unwraps the tuple itself reproduces
    # the bug instead of catching it.
    monkeypatch.setattr(wiring, "detect", lambda only=None: rows)
    monkeypatch.setattr(
        wiring,
        "table",
        lambda: {"surface": [{**row, "writer": "json_codex"} for row in rows]},
    )
    printed = "\n".join(doctor.coverage(None))
    codex = next(line for line in printed.splitlines() if "codex-cli" in line)
    assert "INERT" in codex, f"the coverage block called a silently dead surface: {codex}"


def test_the_surface_list_has_one_home_and_the_rest_derive_from_it():
    """The eight ids were written out four times: `policy/surfaces.toml`, the adapter
    schema's enum, `surface.SURFACES`, and this file's own copy. Only the schema and the
    test were bound to each other; nothing tied either to the wiring table that actually
    decides what gets installed.

    CONSTITUTION.md's Never list opens with "never create mirrors of guards, skills,
    templates or policy homes", and this is the product breaking that rule about itself.
    A ninth surface added to the table would have left three copies behind, and the one
    that reports coverage would have carried on reporting eight.

    The table is the datum. `surface.SURFACES` is derived from it, and the schema enum is
    checked against it rather than maintained beside it."""

    from ai_engineering import surface, wiring

    declared = tuple(row["id"] for row in wiring.table()["surface"])
    assert declared == surface.SURFACES, (
        "surface.SURFACES has drifted from policy/surfaces.toml, which is the one that "
        "decides what gets installed"
    )
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["properties"]["surface_id"]["enum"] == list(declared)


def test_the_first_adapter_instance_conforms_to_the_schema_it_was_frozen_against():
    """Task 7's deferral ends here: the schema was frozen in Block A with no instance, and
    the amendment said an adapter record lands when a reader needs one. Blocks D onward need
    one, so `claude-code` — the only surface whose denial an executed run has ever produced
    — gets the first.

    What it does not yet do is bind a receipt to a requirement, which is the hole this
    module's own docstring admits. Three bindings were tried and each fought a contract that
    already exists: `protocol_id` is forbidden on an automated receipt by the check-evidence
    schema, `input_digest` already means the payload that was checked, and `command` carries
    a machine path so no two runs can match. That binding needs a designed field and a plan
    amendment, not a fourth guess at the end of a long session, and it is written down in
    specs/011 rather than half-shipped."""

    from ai_engineering import paths

    adapter = json.loads(
        (paths.policy("adapters") / "claude-code.adapter.json").read_text(encoding="utf-8")
    )
    assert _validator().valid(adapter), adapter
    assert adapter["surface_id"] == "claude-code"
    assert adapter["detection"]["written_by_us"] is False
    assert adapter["translations"]["exit_meaning"]["2"] == "deny"


def test_a_receipt_that_names_no_adapter_proves_nothing(tmp_path, monkeypatch):
    """Specification 011's Task 16, deferred once because three bindings each fought a
    contract that already existed.

    `protocol_id` and `protocol_version` are forbidden on an automated receipt.
    `input_digest` already means the payload that was checked, and re-pointing it would
    change what every existing receipt claims. `command` carries an absolute path, so no two
    machines can write the same string. What is left is the receipt id: machine-independent,
    already required to match, and free for the adapter to declare instead of this module.

    So the adapter declares it, and a receipt that satisfies every other rule — shaped,
    automated, applicable, fresh, PASS — but names the id a superseded adapter required
    reads INCOMPLETE rather than proving a denial.
    """

    from datetime import UTC, datetime

    from ai_engineering import surface

    now = datetime.now(UTC)
    fresh = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    root = tmp_path / "repository"
    (root / surface.RECEIPTS).mkdir(parents=True)

    def write(receipt_id: str) -> None:
        (root / surface.RECEIPTS / "claude-code.enforcement.json").write_text(
            json.dumps(_receipt("claude-code", "enforcement", finished=fresh) | {"id": receipt_id}),
            encoding="utf-8",
        )

    surface.adapter_proof.cache_clear()
    required = surface.adapter_proof("claude-code")
    assert required, "the adapter declares no receipt id, so nothing is bound"

    write(required)
    proved = surface.read(root, now=now).state("claude-code", "enforcement")
    assert proved.outcome == "PASS", proved
    assert proved.code == surface.PROVEN, proved

    # The same receipt under the id a superseded adapter version would have required.
    write("claude-code.enforcement.v0")
    stale = surface.read(root, now=now).state("claude-code", "enforcement")
    assert stale.outcome == "INCOMPLETE"
    assert stale.code == surface.RECEIPT_MISMATCH


def test_a_surface_with_no_adapter_keeps_the_convention_and_says_which_claim_it_made():
    """The other half, and the one that keeps this honest: where no adapter exists there is
    no requirement the receipt did not write, and this module says so in its own docstring
    rather than printing the same word for both claims."""

    from ai_engineering import surface

    surface.adapter_proof.cache_clear()
    assert surface.adapter_proof("cursor") == ""
    body = (ROOT / "src" / "ai_engineering" / "surface.py").read_text(encoding="utf-8")
    assert "this ran the thing we require" in body
    assert "the weaker claim" in body


def test_every_adapter_puts_a_version_beyond_one_into_the_id_it_requires():
    """The rule that makes supersession mechanical rather than remembered. Version 1 uses the
    plain id, and anything after it carries the version — so a bump that forgets to move the
    id is a bump this test refuses."""

    from ai_engineering import paths

    for found in sorted((paths.policy("adapters")).glob("*.adapter.json")):
        declared = json.loads(found.read_text(encoding="utf-8"))
        version = str(declared["adapter_version"])
        required = declared["proof"]["receipt_id"]
        assert required.startswith(f"{declared['surface_id']}.enforcement"), required
        if version != "1":
            assert required.endswith(f".v{version}"), (
                f"{found.name} is at version {version} and requires {required}"
            )


def test_a_surface_this_framework_will_not_claim_says_so_where_a_command_can_read_it():
    """EP-207. The refusal existed as a non-goal line inside a draft specification, which is
    a refusal no command can read and the next person to add a row has nothing to argue
    with. It is data now, beside the rows it is an argument about.

    Three things are checked, and the third is the one that matters: an id cannot be both
    claimed and refused, so a row quietly added above turns this red rather than shadowing
    the refusal; and a refusal with no reopening condition is a permanent no, which is not a
    decision this framework is allowed to take on somebody's behalf.
    """

    from ai_engineering import wiring

    declared = wiring.table()
    refused = declared.get("refused", [])
    claimed = {surface["id"] for surface in declared["surface"]}

    assert refused, "the refusals are gone, so the argument they carried is gone with them"
    for row in refused:
        assert row["id"] not in claimed, f"{row['id']} is both claimed and refused"
        assert row.get("reason"), f"{row['id']} refuses with no reason, which is a preference"
        assert row.get("reopen_when"), f"{row['id']} refuses forever, which is not ours to do"

    assert "codex-app" in {row["id"] for row in refused}
    # And the reason names the thing that cannot be done, not a preference about doing it.
    reason = next(row["reason"] for row in refused if row["id"] == "codex-app")
    assert "read a receipt back" in reason


def test_an_adapter_past_its_first_version_carries_that_version_in_its_receipt_id():
    """EP-016, and the answer is narrower than the requirement asked for.

    The requirement wants an enforcement receipt bound to the adapter version and the denial
    protocol. The schema already decided how: not by adding two fields, which would be a
    second source of truth beside `receipt_id` and the EP-300 defect arriving again, but by
    making the id itself move — "when a superseding version of this adapter changes what a
    denial looks like, this id moves with it and every receipt written under the old one
    stops proving anything".

    That is a good rule and it was a sentence in a description. Nothing read it, so an
    adapter could go to version 2, keep `claude-code.enforcement`, and every receipt earned
    against version 1's denial would keep vouching for a protocol that had changed
    underneath it. It is vacuous today — every adapter is at version 1 — and it bites on the
    exact day it has to.
    """

    from ai_engineering import paths, surface

    adapters = sorted((paths.policy("adapters")).glob("*.adapter.json"))
    assert adapters, "there are no adapters, so this proves nothing"

    for found in adapters:
        declared = json.loads(found.read_text(encoding="utf-8"))
        assert surface.receipt_binds_version(declared) == "", found.name

    # Every adapter shipped here is at version 1, so the loop above cannot fail today. It was
    # the whole test, and the two lines that stood here in its place asserted a hand-written
    # dictionary against itself — `"2" not in "claude-code.enforcement"` is arithmetic about
    # a literal, and it would have gone on passing with the rule deleted.
    #
    # The rule lives in `surface.py` now, so it can be handed the shapes the tree does not
    # have. Six of them: the version that needs nothing, the version that needs something and
    # has it, three ways of having nothing, and the version that needs something and does not.
    for declared, expect in (
        ({"adapter_version": "1", "proof": {"receipt_id": "claude-code.enforcement"}}, ""),
        ({"adapter_version": "2", "proof": {"receipt_id": "claude-code.enforcement.v2"}}, ""),
        ({"adapter_version": "10", "proof": {"receipt_id": "cursor.enforcement.v10"}}, ""),
        ({"adapter_version": "2", "proof": {"receipt_id": "claude-code.enforcement"}}, "problem"),
        ({"adapter_version": "3", "proof": {"receipt_id": "opencode.enforcement.v2"}}, "problem"),
        ({"adapter_version": "2", "proof": {}}, "problem"),
        ({"proof": {"receipt_id": "claude-code.enforcement"}}, "problem"),
    ):
        answer = surface.receipt_binds_version(declared)
        assert bool(answer) == bool(expect), f"{declared} answered {answer!r}"

    # The refusal names the version and the id, because whoever reads it has to decide which
    # of the two to change and cannot do that from "invalid adapter".
    said = surface.receipt_binds_version(
        {"adapter_version": "2", "proof": {"receipt_id": "claude-code.enforcement"}}
    )
    assert "version 2" in said
    assert "claude-code.enforcement" in said
    assert "still proves this one" in said


def test_the_adapter_table_is_read_in_the_direction_its_schema_declares():
    """The defect two non-identity adapters exposed on their first run.

    `payload_field` is closed on our four canonical names, so the key is ours and the value
    is what that surface sends — a typo in a key is refused rather than quietly becoming a
    translation nobody asked for. `chain.adapter_aliases` needs the other direction and read
    the pair the wrong way round.

    Nothing could tell, because the only adapter that existed mapped every name to itself:
    both readings agreed, and two identity mappings are not a test of a translation. The
    first non-identity adapter would have renamed `tool_input` to `args` on every surface at
    once, emptying the payload that every write guard reads — which is how a whole fleet of
    surfaces is silently unguarded.
    """
    import json

    import chain

    aliases = chain.adapter_aliases()
    for path in sorted(chain.ADAPTERS.glob("*.adapter.json")):
        declared = json.loads(path.read_text(encoding="utf-8"))
        for ours, sent in declared["translations"]["payload_field"].items():
            assert aliases[sent] == ours, (
                f"{path.name}: the table turns {sent!r} into {aliases.get(sent)!r}, and the "
                f"adapter says that surface sends {sent!r} for our {ours!r}"
            )

    # And end to end, on a surface that does not spell anything the way we do.
    payload = chain.normalise({"tool": "Write", "args": {"filePath": "/tmp/x"}})
    assert payload["tool_name"] == "Write"
    assert payload["tool_input"]["file_path"] == "/tmp/x"


def test_every_surface_with_an_adapter_declares_one_the_schema_accepts():
    """Two more landed, and each is a claim about somebody else's software. What keeps them
    honest is the closed schema: an adapter naming a surface this project does not wire, or
    a field outside the four, is refused rather than merged into the table."""
    import json

    import chain

    declared = {
        json.loads(path.read_text(encoding="utf-8"))["surface_id"]
        for path in chain.ADAPTERS.glob("*.adapter.json")
    }
    # Two, not three. VS Code Copilot's landed with OpenCode's and went back out the same
    # day: D-011-02 lands adapters one at a time behind an executed denial, and nothing
    # anywhere runs that surface's path.
    assert declared == {"claude-code", "opencode"}

    # The surfaces with no adapter have none because nobody has read their payload, not
    # because nobody thought about it — writing one from a guess is the fabricated detection
    # this project already refuses one layer down.
    assert "codex-cli" not in declared, (
        "an adapter for codex-cli would be a claim about a payload no receipt has ever shown"
    )


# D-011-02, which nothing read until now: adapters land one at a time, each behind its own
# executed denial. The rationale is in specification 011 — the alternative is eight adapters
# landing together, of which seven are unprovable, "which is how a wave gets declared
# finished on work nobody could verify". It is a precedent and precedents are only worth
# what reads them.
#
# One row per surface that has an adapter, naming the file that executes that surface's
# denial. Not a receipt: receipts are written on a runner and this test has to hold on a
# laptop. What it holds is the harder half — that somebody can point at the thing that runs.
DENIAL_EXECUTED_BY = {
    "claude-code": ".github/workflows/install-matrix.yml",
    "opencode": "tests/test_opencode_plugin.py",
}


def test_no_adapter_lands_without_something_that_executes_its_denial():
    """EP-298, and it caught the session that wrote it.

    Two adapters landed together earlier today — OpenCode and VS Code Copilot — and neither
    was behind a denial. OpenCode's turned out to be fine: `just typecheck` runs the plugin's
    own deny path, driven the way OpenCode drives it. VS Code Copilot's was not: it shares
    Claude Code's settings file, is wired by name, and nothing anywhere runs its path. It was
    removed rather than argued for, because a precedent you write an exception to on the day
    it first applies to you is not a precedent.

    Two of eight surfaces have an adapter, which is what "one at a time" looks like from
    inside.
    """
    import json

    import chain

    shipped = {
        json.loads(path.read_text(encoding="utf-8"))["surface_id"]
        for path in chain.ADAPTERS.glob("*.adapter.json")
    }
    missing = sorted(shipped - set(DENIAL_EXECUTED_BY))
    assert not missing, (
        f"adapters whose surface has no executed denial: {missing}. D-011-02 lands them one "
        f"at a time, each behind its own — remove it, or name what runs it here."
    )
    for surface, runner in DENIAL_EXECUTED_BY.items():
        if surface in shipped:
            assert (ROOT / runner).is_file(), f"{surface} names {runner}, which is not there"


def test_the_precedent_this_check_reads_is_still_the_one_written_down():
    """A check enforcing a decision has to break when the decision changes, or it enforces
    whatever it happened to be written against."""
    spec = (ROOT / "specs" / "011-surface-adapter-contract" / "spec.md").read_text(encoding="utf-8")
    assert "adapters land one at a time, each behind its own executed denial" in spec


def test_a_receipt_written_under_a_superseded_adapter_version_is_not_this_adapter(tmp_path):
    """`EP-147`, and the half of it that can exist.

    The requirement asks a per-surface receipt to carry the surface id, the surface version,
    the adapter version and the deny protocol. `check-evidence-v1` has slots called
    `environment_id`, `protocol_id` and `protocol_version` and forbids all three when `kind`
    is `automated`: they are the manual half of the schema — the person, the protocol they
    followed, the machine they used — and adapter facts written there would make an automated
    run read as a human protocol record. That refusal is the schema working, not a gap in it.

    What is left is `tool_version`, which is free text and is where the adapter version lives.
    A receipt written under adapter 1 and read after the adapter moved to 2 is evidence about
    a protocol nobody is running any more, and until now nothing noticed.
    """

    from ai_engineering import surface as surfaces

    surfaces.adapter_identity.cache_clear() if hasattr(
        surfaces.adapter_identity, "cache_clear"
    ) else None
    declared = surfaces.adapter_identity("opencode")

    assert declared["adapter_version"], "the adapter declares no version to compare against"
    assert declared["deny_protocol"], (
        "the adapter declares no deny protocol. `EP-147` asks a receipt to carry one, and the "
        "reachable half of that is the adapter naming it rather than describing it in a "
        "sentence nothing can compare"
    )
    assert declared["deny_protocol"].islower(), (
        "the deny protocol is an identifier, not the prose in translations.reply.deny"
    )


def test_one_run_answers_three_states_and_says_which_proved_each():
    """`EP-199`: load and invoke are executed states in CI, not just install, deny and doctor.

    The driver already did all three and reported one. Importing the module and getting an
    export is discovery; the registration contract handing back the hook the surface would
    call is invocation; the hook refusing is enforcement. Writing only the last made two
    states that had genuinely executed read as unproven — the same false reading as claiming
    them, with the sign reversed, and this repository is about not doing either.

    What this holds is that the three are not three copies of one fact. Each carries the
    digest of the thing that proved it: the plugin bytes that resolved, the hook name the
    contract returned, and what the guard said. Three receipts with one artifact digest
    between them would be one proof wearing three hats.
    """

    import json

    import pytest

    receipts = ROOT / ".ai" / "receipts" / "surface"
    states = ("discovery", "invocation", "enforcement")
    found = {
        state: receipts / f"opencode.{state}.json"
        for state in states
        if (receipts / f"opencode.{state}.json").is_file()
    }
    if len(found) < len(states):
        pytest.skip("no surface receipts in this tree, so there is nothing to read")

    digests = {}
    for state, path in found.items():
        record = json.loads(path.read_text(encoding="utf-8"))
        assert record["outcome"] == "PASS", state
        assert record["kind"] == "automated", state
        digests[state] = record["artifact_digest"]

    assert len(set(digests.values())) == len(states), (
        f"the three states share an artifact digest: {digests}. Three receipts over one "
        "artefact are one proof counted three times"
    )


def test_the_two_refusals_nothing_had_ever_seen_say_no(tmp_path):
    """Two of the eight codes `_standing` can return had no case at all.

    `SURFACE_RECEIPT_UNREADABLE` is what a receipt file this process cannot read answers, and
    `SURFACE_RECEIPT_FOREIGN` is the one added this afternoon for a receipt written under an
    adapter version the adapter has since left. Both were built, neither had ever been seen
    refusing — which is this repository's defining defect, in the function that decides
    whether a surface reads as proven.

    Found by the mutation lane rather than by reading: fifty-nine of ninety-two survivors sit
    in this one function, and they are branches no case executes.
    """

    import json
    from datetime import UTC, datetime

    import pytest

    from ai_engineering import surface as surfaces

    root = tmp_path
    receipts = root / ".ai" / "receipts" / "surface"
    receipts.mkdir(parents=True)
    now = datetime(2026, 8, 19, 12, 0, tzinfo=UTC)
    fresh = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # A directory where a file belongs: readable as a path, unreadable as a receipt, and the
    # difference between "no receipt" and "a receipt nobody can read" is the whole code.
    (receipts / "cursor.discovery.json").mkdir()
    unreadable = surfaces.read(root, now=now).state("cursor", "discovery")
    assert unreadable.outcome == "INCOMPLETE"
    assert unreadable.code == surfaces.RECEIPT_UNREADABLE, unreadable

    # And a receipt for the surface that has an adapter, written under a version it has left.
    #
    # The caches are read, never cleared. An earlier draft cleared them and turned this case
    # green in isolation and red under `-n auto`: `adapter_proof` is memoised per process, and
    # a case that empties it mid-file hands the next one in the same worker a cold cache built
    # from whatever root that case had patched. Reading a module-level cache is free; resetting
    # one is a write to state shared with every test after it.
    required = surfaces.adapter_proof("opencode") or "opencode.enforcement"
    declared = surfaces.adapter_identity("opencode")
    if not declared.get("adapter_version"):  # pragma: no cover - the adapter always declares
        pytest.skip("the opencode adapter declares no version to be foreign to")
    stale_version = _receipt("opencode", "enforcement", finished=fresh)
    stale_version["id"] = required
    stale_version["tool_version"] = "opencode-adapter 99"
    (receipts / "opencode.enforcement.json").write_text(json.dumps(stale_version), encoding="utf-8")

    foreign = surfaces.read(root, now=now).state("opencode", "enforcement")
    assert foreign.outcome == "INCOMPLETE"
    assert foreign.code == surfaces.RECEIPT_FOREIGN, foreign
