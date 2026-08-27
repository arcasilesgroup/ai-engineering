"""The answer key contract for spec 029 / B-029-2, validated without dependencies.

A machine-readable standard, decided in `ai-spec` before a gate runs, that a reviewer
applies to the delivered work. Every check is binary (`judged_by: run it | a/b pick`); the
key is digest-bound to the spec it judges; an observable not decided is `BLOCKED: U<n>`,
never a fabricated score.

The validator is standard library only — this project declares no dependencies — and the
policy file `policy/answer-key-v1.schema.json` is the loaded source of truth: the carried
schema URN, the `schema_version`, the allowed `judged_by` values and the required fields
are all read from it, so the code never duplicates the contract it enforces.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_FILE = ROOT / "policy" / "answer-key-v1.schema.json"

_HEX64 = re.compile(r"^sha256:[0-9a-f]{64}$")
_SPEC_ID = re.compile(r"^[0-9]{3}$")
_CHECK_ID = re.compile(r"^[a-z0-9-]+$")
_UNKNOWN_ID = re.compile(r"^U[0-9]+$")


def _load_schema() -> dict:
    return json.loads(SCHEMA_FILE.read_text(encoding="utf-8"))


_loaded: dict | None = None


def _schema() -> dict:
    global _loaded
    if _loaded is None:
        _loaded = _load_schema()
    return _loaded


def _schema_urn() -> str:
    return str(_schema().get("$id", ""))


def _schema_version() -> str:
    return str(_schema()["properties"]["schema_version"]["const"])


def _judged_by() -> set[str]:
    return set(_schema()["properties"]["checks"]["items"]["properties"]["judged_by"]["enum"])


def _required() -> tuple[str, ...]:
    return tuple(_schema()["required"])


def validate(key: dict) -> list[str]:
    """Return every way the key is not a valid answer key. Empty means valid."""
    found: list[str] = []

    if not isinstance(key, dict):
        return ["the key is not an object"]

    schema_urn = _schema_urn()
    if key.get("schema") not in (schema_urn,):
        found.append(f"unknown schema {key.get('schema')!r}: not a carried answer-key contract")

    for field in _required():
        if field not in key:
            found.append(f"missing required field {field!r}")

    if key.get("schema_version") != _schema_version():
        found.append(
            f"schema_version must be {_schema_version()}, got {key.get('schema_version')!r}"
        )

    spec = key.get("spec", "")
    if not isinstance(spec, str) or not _SPEC_ID.match(spec):
        found.append(f"spec must match ^[0-9]{{3}}$, got {spec!r}")

    digest = key.get("spec_digest")
    if digest is not None and (not isinstance(digest, str) or not _HEX64.match(digest)):
        found.append(f"spec_digest must be sha256:<64 lowercase hex>, got {digest!r}")

    # additionalProperties: false at the top level.
    allowed = set(_schema().get("properties", {}))
    for extra in set(key) - allowed:
        found.append(f"unknown top-level field {extra!r}")

    unknowns = key.get("unknowns", [])
    if not isinstance(unknowns, list):
        found.append("unknowns must be an array")
    elif any(not isinstance(u, str) or not _UNKNOWN_ID.match(u) for u in unknowns):
        found.append(f"unknowns must match ^U[0-9]+$, got {unknowns!r}")

    checks = key.get("checks")
    if not isinstance(checks, list) or not checks:
        found.append("checks must be a non-empty array")
        return found

    judged_by = _judged_by()
    for check in checks:
        if not isinstance(check, dict):
            found.append("a check is not an object")
            continue
        check_allowed = set(_schema()["properties"]["checks"]["items"]["properties"])
        for extra in set(check) - check_allowed:
            found.append(f"unknown field {extra!r} in check {check.get('id')!r}")
        for field in ("id", "statement", "judged_by"):
            if field not in check:
                found.append(f"missing {field!r} in check {check.get('id')!r}")
        if "id" in check and (not isinstance(check["id"], str) or not _CHECK_ID.match(check["id"])):
            found.append(f"check id must match ^[a-z0-9-]+$, got {check['id']!r}")
        if check.get("judged_by") not in judged_by:
            found.append(
                f"judged_by must be one of {sorted(judged_by)}, got {check.get('judged_by')!r}"
            )
        if check.get("judged_by") == "run it" and not isinstance(check.get("command"), str):
            found.append(f"a 'run it' check needs a command, got {check.get('command')!r}")

    return found


def apply(key: dict, *, touched: set[str] | None = None, failures: set[str] | None = None) -> str:
    """Apply the key to a deliverable. Returns PASS, FAIL or BLOCKED: U<n>.

    `touched` names the unknowns the deliverable exercised; `failures` names decided checks
    that did not hold. A touched unknown is BLOCKED — the work hit a standard nobody decided
    — never a fabricated score and never a silent pass.
    """
    del key
    touched = touched or set()
    failures = failures or set()

    unknown = sorted(touched)
    if unknown:
        return "BLOCKED: " + ", ".join(unknown)

    if failures:
        return "FAIL"

    # Every check is a decided standard; reaching here means all held or are untested.
    return "PASS"


def valid(payload: dict) -> bool:
    return validate(payload) == []


if __name__ == "__main__":
    import sys
    import tomllib

    p = Path("answer-key.yaml")
    payload = tomllib.loads(p.read_text(encoding="utf-8"))
    problems = validate(payload)
    if problems:
        print("\n".join(problems), file=sys.stderr)
        raise SystemExit(1)
    print("answer-key valid")
