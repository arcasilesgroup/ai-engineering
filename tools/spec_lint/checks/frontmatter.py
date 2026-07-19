"""Frontmatter check — required fields + enum validation + extras allow-list.

spec-131 S7 D-131-17: validates the four required frontmatter fields
(``spec`` / ``title`` / ``status`` / ``effort``) and the two enum
constraints (``status`` / ``effort``). Declared extras (operator
metadata fields) clear via the explicit allow-list; unknown keys
emit ``ADVISORY`` warnings (exit 0) so operator-added metadata never
trips the hot path.

spec-139 M8 D-139-06: adds the ``summary`` field with a dated rollout.
During the soft window (today through :data:`SUMMARY_HARD_REQUIRED_AFTER`)
missing ``summary`` emits an ``ADVISORY``; after the cutover the same
condition promotes to ``BLOCKER``. The two-stage rollout lets the
existing spec corpus backfill ``summary:`` without breaking the hot
path on day one. Length cap is 300 chars (1-2 sentences).
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass
from pathlib import Path

import yaml

_VALID_SEVERITIES = {"OK", "ADVISORY", "BLOCKER"}

# spec-139 M8 D-139-06 — date on which the ``summary`` advisory promotes
# to BLOCKER. Stored as a UTC date so timezone drift never flips the gate
# unexpectedly. The 30-day soft window starts from the M8 ship date
# (2026-05-17) and lands on 2026-06-16.
SUMMARY_HARD_REQUIRED_AFTER = _dt.date(2026, 6, 16)

# Maximum length of the ``summary`` field (1-2 sentence target, per
# spec-schema.md ``summary`` row).
SUMMARY_MAX_LEN = 300


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a spec_lint check.

    ``line`` is the 1-based source line where the issue was detected,
    or 0 when the issue is file-level (e.g., missing frontmatter fence).
    """

    check_name: str
    severity: str
    reason: str
    line: int = 0

    def __post_init__(self) -> None:
        if self.severity not in _VALID_SEVERITIES:
            raise ValueError(f"severity {self.severity!r} not in {sorted(_VALID_SEVERITIES)}")


# spec-schema.md §"Required Frontmatter" — the four mandatory fields.
REQUIRED_FIELDS = frozenset({"spec", "title", "status", "effort"})

# Enum-constrained values per spec-schema.md.
ENUMS: dict[str, frozenset[str]] = {
    "status": frozenset({"draft", "approved", "in-progress", "done"}),
    "effort": frozenset({"trivial", "small", "medium", "large"}),
}

# spec-131 D-131-17 — operator-metadata extras that clear without warning.
# Adding entries here is the documented escape hatch when a new metadata
# field becomes mainstream across the spec corpus.
EXTRAS_ALLOWLIST = frozenset(
    {
        "branch",
        "pr",
        "slug",
        "target_dispatch",
        "source_brief",
        "chains_after",
        "approved_at",
        "approved_by",
        # spec-139 M8 D-139-06 — ``summary`` is validated explicitly by the
        # dated-rollout block below; listing it here keeps the
        # ``frontmatter_unknown_key`` advisory silent when the field is
        # present.
        "summary",
        # Spec corpus surface fields observed in the run (spec-138/139/140/141).
        "mantra",
        "trigger_incident",
        "auto_approved",
        "auto_approval_reason",
        "date_approved",
    }
)


def _parse_frontmatter(text: str) -> tuple[dict[str, str] | None, int]:
    """Parse a markdown YAML frontmatter block.

    Returns ``(fields, last_line)`` where ``fields`` is the key→value
    mapping (``None`` when no fence is present) and ``last_line`` is the
    1-based line number of the closing ``---`` fence (or 0 if absent).

    The parser is intentionally pure-stdlib and bounded: it only walks
    the leading frontmatter block and stops at the closing fence. Values
    are stripped of surrounding whitespace. Multi-line scalars, lists,
    and nested maps are not supported — the spec corpus uses only flat
    ``key: value`` lines.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None, 0

    fields: dict[str, str] = {}
    for idx, raw in enumerate(lines[1:], start=2):
        if raw.strip() == "---":
            return fields, idx
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        if ":" not in raw:
            continue
        key, _, value = raw.partition(":")
        fields[key.strip()] = value.strip()
    # No closing fence found — return what we parsed plus a sentinel
    # that ``check_frontmatter`` reads as "incomplete".
    return fields, 0


def check_frontmatter(spec_path: Path) -> list[CheckResult]:
    """Validate the frontmatter of ``spec_path``.

    Emits:

    * ``BLOCKER frontmatter_missing`` if no ``---`` fence is present.
    * ``BLOCKER frontmatter_yaml_invalid`` if the block is not valid YAML
      (spec-188 D-188-02 — integrity gate, fails closed).
    * ``BLOCKER frontmatter_missing_required`` per absent required key.
    * ``BLOCKER frontmatter_invalid_enum`` per enum violation.
    * ``ADVISORY frontmatter_unknown_key`` per unknown key (not in
      required, not in :data:`EXTRAS_ALLOWLIST`).
    * ``ADVISORY frontmatter_missing_summary`` until
      :data:`SUMMARY_HARD_REQUIRED_AFTER`; ``BLOCKER`` after the cutover
      (spec-139 M8 D-139-06).
    * ``ADVISORY frontmatter_summary_too_long`` when ``summary`` exceeds
      :data:`SUMMARY_MAX_LEN`.
    """
    text = spec_path.read_text(encoding="utf-8")
    fields, fence_line = _parse_frontmatter(text)

    if fields is None:
        return [
            CheckResult(
                "frontmatter_missing",
                "BLOCKER",
                "spec.md must open with a YAML frontmatter fence (---)",
            )
        ]

    if fence_line == 0:
        return [
            CheckResult(
                "frontmatter_missing",
                "BLOCKER",
                "frontmatter block is missing its closing --- fence",
            )
        ]

    results: list[CheckResult] = []

    # spec-188 D-188-02 — strict YAML validation of the frontmatter block.
    # The stdlib partition parser above tolerates malformed YAML (e.g. an
    # unquoted value whose mid-value colon starts a phantom key). spec_lint
    # is an integrity gate and must fail closed on frontmatter a real YAML
    # parser rejects (gate-policy.md). The block spans the lines between the
    # opening fence (line 1) and the closing fence (``fence_line``).
    block = "\n".join(text.splitlines()[1 : fence_line - 1])
    try:
        yaml.safe_load(block)
    except yaml.YAMLError as exc:
        results.append(
            CheckResult(
                "frontmatter_yaml_invalid",
                "BLOCKER",
                f"frontmatter is not valid YAML: {str(exc).splitlines()[0]}",
            )
        )

    for required in sorted(REQUIRED_FIELDS):
        if required not in fields or not fields[required]:
            results.append(
                CheckResult(
                    "frontmatter_missing_required",
                    "BLOCKER",
                    f"required frontmatter field '{required}' is missing or empty",
                )
            )

    # spec-139 M8 D-139-06 — ``summary`` rollout: soft window emits
    # ADVISORY, hard window emits BLOCKER. The severity is computed at
    # check-time from the system clock so the gate flips automatically
    # on 2026-06-16 without a code change.
    summary_value = fields.get("summary", "").strip()
    if not summary_value:
        severity = "BLOCKER" if _dt.date.today() > SUMMARY_HARD_REQUIRED_AFTER else "ADVISORY"
        results.append(
            CheckResult(
                "frontmatter_missing_summary",
                severity,
                (
                    "frontmatter field 'summary' is missing or empty "
                    f"(soft requirement until {SUMMARY_HARD_REQUIRED_AFTER.isoformat()}, "
                    "hard requirement after; see spec-schema.md)"
                ),
            )
        )
    elif len(summary_value) > SUMMARY_MAX_LEN:
        results.append(
            CheckResult(
                "frontmatter_summary_too_long",
                "ADVISORY",
                (
                    f"frontmatter 'summary' is {len(summary_value)} chars; "
                    f"target is ≤{SUMMARY_MAX_LEN} chars (1-2 sentences)"
                ),
            )
        )

    for enum_field, allowed in ENUMS.items():
        if fields.get(enum_field) and fields[enum_field] not in allowed:
            results.append(
                CheckResult(
                    "frontmatter_invalid_enum",
                    "BLOCKER",
                    (
                        f"frontmatter '{enum_field}' value "
                        f"{fields[enum_field]!r} not in {sorted(allowed)}"
                    ),
                )
            )

    for key in sorted(fields):
        if key in REQUIRED_FIELDS or key in EXTRAS_ALLOWLIST:
            continue
        results.append(
            CheckResult(
                "frontmatter_unknown_key",
                "ADVISORY",
                (f"unknown frontmatter key '{key}' (not required, not in EXTRAS_ALLOWLIST)"),
            )
        )

    return results
