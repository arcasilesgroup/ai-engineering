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
