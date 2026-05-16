"""Frontmatter check — required fields + enum validation + extras allow-list.

spec-131 S7 D-131-17: validates the four required frontmatter fields
(``spec`` / ``title`` / ``status`` / ``effort``) and the two enum
constraints (``status`` / ``effort``). Declared extras (operator
metadata fields) clear via the explicit allow-list; unknown keys
emit ``ADVISORY`` warnings (exit 0) so operator-added metadata never
trips the hot path.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

_VALID_SEVERITIES = {"OK", "ADVISORY", "BLOCKER"}


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
    * ``BLOCKER frontmatter_missing_required`` per absent required key.
    * ``BLOCKER frontmatter_invalid_enum`` per enum violation.
    * ``ADVISORY frontmatter_unknown_key`` per unknown key (not in
      required, not in :data:`EXTRAS_ALLOWLIST`).
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

    for required in sorted(REQUIRED_FIELDS):
        if required not in fields or not fields[required]:
            results.append(
                CheckResult(
                    "frontmatter_missing_required",
                    "BLOCKER",
                    f"required frontmatter field '{required}' is missing or empty",
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
