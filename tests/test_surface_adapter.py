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
    assert seen.state("claude-code", "discovery").outcome == "PASS"
    assert seen.state("claude-code", "invocation").outcome == "INCOMPLETE"
    assert seen.state("claude-code", "enforcement").outcome == "INCOMPLETE"

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

    now = datetime.now(UTC)
    fresh = (now - timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
    root = tmp_path / "repository"
    (root / surface.RECEIPTS).mkdir(parents=True)
    (root / surface.RECEIPTS / "claude-code.discovery.json").write_text(
        json.dumps(_receipt("claude-code", "discovery", finished=fresh)), encoding="utf-8"
    )
    monkeypatch.setattr(paths, "repo_root", lambda start=None: root)

    result = report.main(["surfaces"])
    printed = capsys.readouterr().out

    # Unproven anywhere means unproven overall. One receipt does not make a surface proved.
    assert result.outcome == "INCOMPLETE"
    assert "claude-code" in printed and "discovery" in printed
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

    # Nor may any schema declare the same claim under another name. This block wrote a new
    # policy file and the guard could not see it: the adapter contract carried a hand-typed
    # `heartbeat` saying "installed, loaded, observed at", which is the deleted flag with
    # three fields instead of one.
    for schema in sorted((ROOT / "policy").glob("*.schema.json")):
        declared = json.loads(schema.read_text(encoding="utf-8")).get("properties", {})
        for claim in ("proven", "heartbeat", "blocks", "covered"):
            assert claim not in declared, f"{schema.name} declares {claim}"

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
    honest = _receipt("pi", "enforcement", finished=fresh) | {"applicability": "not_applicable"}
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
