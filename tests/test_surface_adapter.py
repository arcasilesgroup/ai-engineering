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
        "heartbeat",
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

    assert set(schema["properties"]["heartbeat"]["properties"]) == {
        "installed",
        "loaded",
        "observed_at",
    }
    assert set(schema["properties"]["trust"]["properties"]) == {"required", "ceremony"}

    # The policy the reader must obey, declared beside the shape it applies to, so a reader
    # written later cannot quietly choose a friendlier rule.
    assert schema["x-adapter-policy"] == {
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
        "heartbeat",
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
        "heartbeat": "heartbeat",
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
        doctor.coverage = lambda where: []
        published = {fact.id for fact in doctor.main([]).checks}
    finally:
        paths_module.repo_root = original
        doctor.CHECKS = checks
        doctor.coverage = coverage
    assert "surface-claude-code-enforcement" in published
    assert "surface-zed-enforcement" in published
