"""The one object every verb prints, and the contract it now names.

`policy/` held eight schemas and none for the envelope. The envelope carried
`schema_version: "1"` and no `schema`, which is a version number for a document nobody could
find: a reader written against version 1 of *what* had no way to check it was reading the
right object, and a field added on a Thursday would have been indistinguishable from one
that had always been there.

So the contract exists, the envelope names it, and the proof is not that the file parses —
it is that real verbs are run and their actual stdout is validated against it. A schema
nothing is measured against is the documentation this repository refuses.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from ai_engineering import cli

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "policy" / "envelope-v1.schema.json"


def schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))


def _resolve(rule: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    reference = rule.get("$ref")
    return root["$defs"][reference.removeprefix("#/$defs/")] if reference else rule


def problems(value: Any, rule: dict[str, Any], root: dict[str, Any], where: str) -> list[str]:
    """Every way this value fails this rule, as a list rather than the first one.

    A list, because a shape error found one run at a time is one run per error — the same
    argument `tests/pilot_register.py` makes about its own reader.
    """

    rule = _resolve(rule, root)
    found: list[str] = []

    if "oneOf" in rule:
        matched = [branch for branch in rule["oneOf"] if not problems(value, branch, root, where)]
        if len(matched) != 1:
            found.append(f"{where}: matches {len(matched)} of the alternatives, not exactly one")
        return found

    kind = rule.get("type")
    if kind == "null" and value is not None:
        found.append(f"{where}: expected null")
    if kind == "string" and not isinstance(value, str):
        found.append(f"{where}: expected a string, got {type(value).__name__}")
    if kind == "boolean" and not isinstance(value, bool):
        found.append(f"{where}: expected a boolean")
    if kind == "array" and not isinstance(value, list):
        found.append(f"{where}: expected an array")
    if kind == "object" and not isinstance(value, dict):
        found.append(f"{where}: expected an object")
    if found:
        return found

    if "const" in rule and value != rule["const"]:
        found.append(f"{where}: is {value!r} and the contract says {rule['const']!r}")
    if "enum" in rule and value not in rule["enum"]:
        found.append(f"{where}: {value!r} is not one of {rule['enum']}")
    if isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            found.append(f"{where}: shorter than its minimum")
        if "maxLength" in rule and len(value) > rule["maxLength"]:
            found.append(f"{where}: longer than its bound of {rule['maxLength']}")
        if "pattern" in rule and re.fullmatch(rule["pattern"], value) is None:
            found.append(f"{where}: {value!r} does not match {rule['pattern']}")
    if isinstance(value, list):
        if "maxItems" in rule and len(value) > rule["maxItems"]:
            found.append(f"{where}: more items than its bound")
        for index, item in enumerate(value):
            found.extend(problems(item, rule["items"], root, f"{where}[{index}]"))
    if isinstance(value, dict) and kind == "object":
        for name in rule.get("required", []):
            if name not in value:
                found.append(f"{where}: is missing {name}")
        if rule.get("additionalProperties") is False:
            for name in set(value) - set(rule.get("properties", {})):
                found.append(f"{where}: carries {name}, which the contract does not allow")
        for name, sub in rule.get("properties", {}).items():
            if name in value:
                found.extend(problems(value[name], sub, root, f"{where}.{name}"))
    return found


def run(arguments: list[str]) -> dict[str, Any]:
    """One real process, and its stdout parsed as the whole answer.

    Reading the envelope out of an in-process call would prove the builder agrees with
    itself. What has to hold is that the bytes reaching a script are the contract, and the
    only way to know is to be the script.
    """

    done = subprocess.run(
        [sys.executable, "-m", "ai_engineering.cli", "--json", *arguments],
        cwd=ROOT,
        env={**os.environ, "PYTHONPATH": str(ROOT / "src"), "NO_COLOR": "1"},
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert done.stdout.count("\n") == 1, f"stdout is not one line: {done.stdout[:200]!r}"
    assert "\x1b" not in done.stdout, "the machine rendering was decorated"
    return json.loads(done.stdout)


def test_the_envelope_schema_is_closed_and_names_itself():
    """A contract with an open door is a contract about the fields somebody remembered."""

    contract = schema()

    assert contract["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    assert contract["$id"] == cli.ENVELOPE_SCHEMA, "the constant and the file disagree"
    assert contract["additionalProperties"] is False
    assert contract["properties"]["schema"]["const"] == cli.ENVELOPE_SCHEMA
    assert contract["properties"]["schema_version"]["const"] == "1"

    # Every field is required. An optional one here is a field a reader cannot rely on and
    # a producer can drop without anything noticing, which is the whole failure this closes.
    assert sorted(contract["required"]) == sorted(contract["properties"])

    # The terminal vocabulary is the one `outcome-v1` states, and RUNNING is not in it.
    stated = json.loads((ROOT / "policy" / "outcome-v1.schema.json").read_text(encoding="utf-8"))
    assert contract["properties"]["outcome"]["enum"] == stated["properties"]["outcome"]["enum"]
    assert "RUNNING" not in contract["properties"]["outcome"]["enum"]


@pytest.mark.parametrize(
    "arguments",
    [
        ["spec", "list"],
        ["doctor", "--ci"],
        ["audit", "verify"],
        ["report", "surfaces"],
    ],
    ids=["spec-list", "doctor-ci", "audit-verify", "report-surfaces"],
)
def test_what_four_real_verbs_actually_print_validates_against_the_contract(arguments):
    """Executed, not constructed. Two of these four answer INCOMPLETE or FAIL on this
    machine, which is the point: an envelope has to be a valid envelope when the news is
    bad, and the error branch is the half a happy-path fixture never reaches."""

    contract = schema()
    envelope = run(arguments)

    assert problems(envelope, contract, contract, "envelope") == []
    assert envelope["schema"] == cli.ENVELOPE_SCHEMA


def test_a_field_nobody_declared_is_refused_by_the_reader_that_reads_it():
    """The validator is the thing being trusted here, so it is measured too. A scan that
    finds nothing and a scan that looked at nothing print the same result."""

    contract = schema()
    envelope = run(["spec", "list"])

    assert problems(envelope, contract, contract, "envelope") == []
    assert problems({**envelope, "extra": 1}, contract, contract, "envelope") != []
    assert problems({**envelope, "outcome": "GREEN"}, contract, contract, "envelope") != []
    assert problems({**envelope, "schema": "urn:something:else"}, contract, contract, "e") != []
    assert problems({k: v for k, v in envelope.items() if k != "error"}, contract, contract, "e")
    broken = {**envelope, "checks": [{"id": "x", "status": "PASS"}]}
    assert problems(broken, contract, contract, "envelope") != []
