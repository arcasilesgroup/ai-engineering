"""The decision-boundary classifier, spec 036 / B-036-1.

A decision classifies its boundary: Always, Ask-first or Never inside the declared scope,
None out of it — indexed U0 (undeclared or malformed declarations) or U1.
(out-of-declaration) — the blocking result a surface reports as CANNOT DECIDE, never
coerced into a class (wayfinder W-02: Unknown -> CANNOT JUDGE; addyosmani ASK-14:
Always/Ask-first/Never). The classifier reads declarations from the capability-manifest
surface and never defines a second permission model (capability.py decides what an op may
do; this decides whether a decision is out of declared scope at all).
"""

from __future__ import annotations

import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ai_engineering import paths

CAPABILITIES = paths.policy("capabilities.toml")

# The capability schema's declared human_gate vocabulary (spec 022-era). Every listed gate
# maps deterministically; anything outside the vocabulary is undeclared (U0) and blocks,
# never a silent decision — capability.py fails closed on the same input.
_GATES = {
    "never": "Always",
    "before_write": "Ask-first",
    "before_exec": "Ask-first",
    "before_network": "Ask-first",
    "before_publish": "Ask-first",
    "always": "Never",
}


@dataclass(frozen=True)
class Classified:
    """The classifier's result: a verdict plus an indexed reason."""

    verdict: str | None  # "Always" | "Ask-first" | "Never" | None
    reason: str | None  # None in scope; "U0" undeclared/malformed; "U1".. out-of-declaration
    blocks: bool  # out-of-declaration or undeclared -> block, never guess

    @staticmethod
    def decided(verdict: str) -> Classified:
        return Classified(verdict=verdict, reason=None, blocks=False)

    @staticmethod
    def undecided(reason: str) -> Classified:
        return Classified(verdict=None, reason=reason, blocks=True)


_CANONICAL: dict[str, str] = {"always": "Always", "ask_first": "Ask-first", "never": "Never"}


def _normalise(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    folded = value.strip().casefold().replace("-", "_").replace(" ", "_")
    return _CANONICAL.get(folded)


def classify(decision: str, declarations: Mapping[str, str] | None) -> Classified:
    """Classify one decision against a boundary declaration mapping.

    In scope: Always / Ask-first / Never, deterministically. Out of scope: None with U1..
    and blocks. Undeclared or malformed declarations: None with U0 and blocks. Never
    coerces an undecided class (the clean control a downstream caller relies on).
    """
    if not decision or not isinstance(decision, str):
        return Classified.undecided("U0")
    if not declarations:
        return Classified.undecided("U0")
    folded = decision.strip().casefold().replace(" ", "_")
    declared = {
        k.strip().casefold().replace(" ", "_"): v for k, v in declarations.items() if k is not None
    }
    if folded not in declared:
        return Classified.undecided("U1")  # out of the declared boundary
    klass = _normalise(declared[folded])
    if klass is None:
        return Classified.undecided("U0")  # declared but malformed class
    return Classified.decided(klass)


def from_capability_manifest(manifest: Mapping[str, Any]) -> dict[str, str | None]:
    """Map capability states to boundary classes.

    The single source of truth: capabilities.toml / the manifest the capability contract
    reads. Each gate in the declared vocabulary maps strictly (never -> Always, the
    before_* gates -> Ask-first, always -> Never); a gate outside the vocabulary, or a
    missing one, maps to None — the caller's U0, a blocked decision that is never coerced
    into a class, matching capability.py's fail-closed posture on the same input.
    """
    mapping: dict[str, str | None] = {}
    for cap in manifest.get("capabilities") or []:
        cap_id = str(cap.get("id", "")).strip()
        if not cap_id:
            continue
        for mode in cap.get("modes") or []:
            mode_id = str(mode.get("id", "default")).strip() or "default"
            gate = mode.get("human_gate")
            mapping[f"{cap_id}:{mode_id}"] = _GATES.get(gate)
    return mapping


def load_capability_classes() -> dict[str, str | None]:
    """Read the live capabilities.toml the capability contract actually enforces."""
    with CAPABILITIES.open("rb") as fh:
        raw = tomllib.load(fh)
    return from_capability_manifest(raw)
