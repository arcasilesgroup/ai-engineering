"""Auto-spec gate classifier — pure domain helper (spec-134 D-134-04).

Routes a working-tree diff to either the ``condensed`` spec path or
the ``full`` interrogation path. The helper is pure: it accepts a
``files`` list and the raw ``git diff`` output as inputs and returns a
:class:`GateDecision`. The skill handler
(``.claude/skills/ai-brainstorm/handlers/auto-spec-gate.md``) is the
adapter that runs ``git diff`` and passes the raw output in.

Principles
----------

* §10.5 TDD — the classifier is exercised by
  ``tests/unit/skills/test_brainstorm_auto_spec_gate.py`` (RED-first).
* §10.6 SDD — every routing rule traces back to the spec at
  ``.ai-engineering/runtime/autopilot/sub-004/spec.md`` (Exploration
  → Signal detection table).
* §10.8 Hexagonal architecture — no subprocess, no I/O. The skill
  handler is the adapter; this module is the domain.

Decision contract
-----------------

* ``route='full'`` is the safe default. Any hard trigger or any
  threshold breach flips the decision to full interrogation.
* ``route='condensed'`` requires (a) no hard triggers fired,
  (b) every threshold strictly satisfied, and (c) at least one file
  in the diff (an empty diff routes to full — the operator clearly
  has not staged anything yet).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

from ai_engineering.config.manifest import AutoSpecGateConfig

__all__ = ["AutoSpecGateConfig", "GateDecision", "classify_diff"]


# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateDecision:
    """Outcome of :func:`classify_diff`.

    Attributes
    ----------
    route:
        ``'condensed'`` when the diff is trivial enough for the
        condensed-spec path; ``'full'`` for full interrogation.
    reason:
        Human-readable summary suitable for surfacing in the chat
        thread (e.g., ``"hard trigger: public_api"``).
    triggers:
        Names of hard triggers that fired, if any. Empty list when the
        gate routed on threshold breach alone.
    """

    route: Literal["condensed", "full"]
    reason: str
    triggers: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Hard-trigger predicates — one regex per signal vector.
# ---------------------------------------------------------------------------

_PUBLIC_API_PATTERNS = (
    re.compile(r"^src/.+/__init__\.py$"),
    re.compile(r"^src/.+/cli_factory\.py$"),
    re.compile(r"^src/.+/cli_commands/.+$"),
)

_STATE_OR_SCHEMA_PATTERNS = (
    re.compile(r"^\.ai-engineering/state/.+$"),
    re.compile(r"^\.ai-engineering/schemas/.+\.json$"),
    re.compile(r".+\.sql$"),
    re.compile(r".+/migrations/.+$"),
)

_SECURITY_SURFACE_PATTERNS = (
    re.compile(r".+/_shared/redactor\.py$"),
    re.compile(r".+/security/.+$"),
    re.compile(r"^\.ai-engineering/scripts/hooks/.+$"),
    re.compile(r"^\.ai-engineering/state/hooks-manifest\.json$"),
    re.compile(r"^\.ai-engineering/security/.+$"),
)

_DEPENDENCY_FILES = frozenset({"pyproject.toml", "package.json"})


def _path_matches_any(path: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    """Return True when ``path`` matches any of the given regexes."""
    return any(p.search(path) for p in patterns)


def _diff_adds_dependency(diff_text: str) -> bool:
    """Return True when ``diff_text`` adds a dependency line.

    Heuristic: a ``+`` prefixed line that looks like a Python or JSON
    dependency entry. Removals are intentionally ignored — yagni.
    """
    for line in diff_text.splitlines():
        if not line.startswith("+") or line.startswith("+++"):
            continue
        stripped = line[1:].strip()
        if re.match(r'^"[^"]+"\s*:\s*"[^"]+",?$', stripped):
            return True
        if re.match(r'^"[a-zA-Z_][\w\-]*[><=!~]+[^"]+",?$', stripped):
            return True
    return False


def _match_hard_triggers(files: list[str], diff_text: str, config: AutoSpecGateConfig) -> list[str]:
    """Return the names of hard triggers that fired for this diff."""
    triggers: list[str] = []
    flags = config.hard_triggers
    if flags.public_api and any(_path_matches_any(f, _PUBLIC_API_PATTERNS) for f in files):
        triggers.append("public_api")
    if flags.state_or_schema and any(
        _path_matches_any(f, _STATE_OR_SCHEMA_PATTERNS) for f in files
    ):
        triggers.append("state_or_schema")
    if flags.security_surface and any(
        _path_matches_any(f, _SECURITY_SURFACE_PATTERNS) for f in files
    ):
        triggers.append("security_surface")
    if (
        flags.new_dependency
        and any(f in _DEPENDENCY_FILES for f in files)
        and _diff_adds_dependency(diff_text)
    ):
        triggers.append("new_dependency")
    return triggers


# ---------------------------------------------------------------------------
# Threshold helpers.
# ---------------------------------------------------------------------------

_SHORTSTAT_RE = re.compile(
    r"(?P<ins>\d+)\s+insertions?\(\+\)|"
    r"(?P<del>\d+)\s+deletions?\(-\)"
)


def _parse_loc(diff_text: str) -> int:
    """Return total LoC delta (insertions + deletions) from shortstat output."""
    total = 0
    for match in _SHORTSTAT_RE.finditer(diff_text):
        ins = match.group("ins")
        dels = match.group("del")
        if ins is not None:
            total += int(ins)
        if dels is not None:
            total += int(dels)
    return total


def _count_cross_modules(files: list[str]) -> int:
    """Return the number of distinct ``src/<first-segment>/`` modules touched."""
    modules: set[str] = set()
    for path in files:
        parts = path.split("/")
        if len(parts) >= 3 and parts[0] == "src":
            modules.add(parts[1])
    return len(modules)


# ---------------------------------------------------------------------------
# Public entry point.
# ---------------------------------------------------------------------------


def classify_diff(
    *,
    files: list[str],
    diff_text: str,
    config: AutoSpecGateConfig,
    regulated: bool,
) -> GateDecision:
    """Classify a working-tree diff for the auto-spec gate.

    Parameters
    ----------
    files:
        Output of ``git diff --name-only HEAD``, one path per entry.
    diff_text:
        Concatenated output of ``git diff --shortstat HEAD`` plus
        ``git diff HEAD -- pyproject.toml package.json`` so the helper
        can recover both LoC totals and dependency-block additions
        from a single string.
    config:
        :class:`AutoSpecGateConfig` from the loaded manifest.
    regulated:
        ``True`` when the runtime ``gates.mode == "regulated"``. The
        caller resolves this — the helper stays free of manifest I/O.

    Returns
    -------
    GateDecision
        Routing decision with reason + triggers attached.
    """
    if not config.enabled:
        return GateDecision(route="full", reason="auto_spec_gate disabled by opt-out knob")

    if not files:
        return GateDecision(route="full", reason="no staged or tracked changes detected")

    triggers = _match_hard_triggers(files, diff_text, config)
    if triggers:
        return GateDecision(
            route="full",
            reason=f"hard trigger fired: {', '.join(triggers)}",
            triggers=triggers,
        )

    thresholds = config.regulated_overrides if regulated else config.thresholds
    file_count = len(files)
    loc_count = _parse_loc(diff_text)
    module_count = _count_cross_modules(files)

    if file_count > thresholds.files:
        return GateDecision(
            route="full",
            reason=f"files threshold exceeded ({file_count} > {thresholds.files})",
        )
    if loc_count > thresholds.loc:
        return GateDecision(
            route="full",
            reason=f"loc threshold exceeded ({loc_count} > {thresholds.loc})",
        )
    if module_count > thresholds.cross_module:
        return GateDecision(
            route="full",
            reason=f"cross_module threshold exceeded ({module_count} > {thresholds.cross_module})",
        )

    return GateDecision(route="condensed", reason="trivial diff — condensed-spec path")
