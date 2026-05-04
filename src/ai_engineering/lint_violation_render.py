"""spec-119 D-119-05 lint-as-prompt renderers.

Compliance reporters and skill handlers emit structured violation envelopes
matching `.ai-engineering/schemas/lint-violation.schema.json`. Human review
still benefits from a markdown-table view; this module is the canonical
renderer that converts a list of envelopes back to a readable surface.

Core principle: structured form is canonical. The renderer is a derived
view, not a parser. Any consumer that wants to act on violations should
read the structured form directly and skip the renderer.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

_REQUIRED_FIELDS: frozenset[str] = frozenset(
    {"rule_id", "severity", "expected", "actual", "fix_hint"}
)


def _validate_envelope(envelope: Mapping[str, object]) -> None:
    missing = _REQUIRED_FIELDS - envelope.keys()
    if missing:
        msg = f"lint-violation envelope missing required fields: {sorted(missing)}"
        raise ValueError(msg)
    severity = envelope.get("severity")
    if severity not in {"error", "warning", "info"}:
        msg = f"lint-violation envelope severity must be error|warning|info, got {severity!r}"
        raise ValueError(msg)


def _location(envelope: Mapping[str, object]) -> str:
    file = envelope.get("file")
    line = envelope.get("line")
    if file and line:
        return f"{file}:{line}"
    if file:
        return str(file)
    return "-"


def _escape_table_cell(value: object) -> str:
    """Markdown table cells cannot carry pipes or hard newlines unescaped."""
    s = str(value).replace("|", "\\|").replace("\n", " ")
    return s.strip() or "-"


def render_text(envelope: Mapping[str, object]) -> str:
    """Single-violation human-readable line, used by stream-style outputs.

    Format: `[severity] rule_id @ location -- expected: ... -- actual: ... -- fix: ...`
    """
    _validate_envelope(envelope)
    severity = envelope["severity"]
    rule_id = envelope["rule_id"]
    return (
        f"[{severity}] {rule_id} @ {_location(envelope)} "
        f"-- expected: {envelope['expected']} "
        f"-- actual: {envelope['actual']} "
        f"-- fix: {envelope['fix_hint']}"
    )


def render_table(violations: Iterable[Mapping[str, object]]) -> str:
    """Render a list of envelopes as a markdown table.

    Empty input renders an explicit "no violations" line so reviewers can
    distinguish "ran the lint and found nothing" from "skipped the lint".
    """
    materialized = list(violations)
    if not materialized:
        return "_No lint violations._"
    for env in materialized:
        _validate_envelope(env)
    rows = ["| Severity | Rule | Location | Expected | Actual | Fix Hint |"]
    rows.append("|---|---|---|---|---|---|")
    for env in materialized:
        rows.append(
            "| "
            + " | ".join(_escape_table_cell(env.get(col, "")) for col in ("severity", "rule_id"))
            + " | "
            + _escape_table_cell(_location(env))
            + " | "
            + " | ".join(
                _escape_table_cell(env.get(col, "")) for col in ("expected", "actual", "fix_hint")
            )
            + " |"
        )
    return "\n".join(rows)


__all__ = ["render_table", "render_text"]
