"""spec-104 D-104-05 watch-residuals emit helper.

When the watch loop hits its active 30-min or passive 4-h wall-clock cap
(D-104-05), it materialises the still-failing checks into
``.ai-engineering/state/watch-residuals.json`` so spec-105 risk-accept-all
has a deterministic input file. The schema is identical to
``gate-findings.json`` v1 (D-104-06) — ``produced_by`` is the only
discriminator (``"watch-loop"`` here vs ``"ai-commit"``/``"ai-pr"``).

Atomic publish via ``tempfile + os.replace`` mirrors
``orchestrator._emit_findings`` so torn writes are impossible.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_engineering.state.models import (
    GateFinding,
    GateFindingsDocument,
    GateProducedBy,
    WallClockMs,
)

logger = logging.getLogger(__name__)


def _git_branch() -> str:
    """Return the current git branch name; ``"unknown"`` on failure."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unknown"
    if getattr(result, "returncode", 1) == 0:
        return (result.stdout or "").strip() or "unknown"
    return "unknown"


def _git_sha() -> str | None:
    """Return ``git rev-parse HEAD``; ``None`` when unavailable."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
        )
    except OSError:
        return None
    if getattr(result, "returncode", 1) == 0:
        sha = (result.stdout or "").strip()
        return sha or None
    return None


def emit(
    failed_checks: list[dict[str, Any]],
    output_path: Path | None = None,
) -> Path:
    """Emit ``watch-residuals.json`` per D-104-06 schema v1 from failed checks.

    Args:
        failed_checks: List of dicts shaped like ``GateFinding`` (check,
            rule_id, file, line, severity, message, auto_fixable,
            auto_fix_command). Severity is preserved verbatim — no
            normalisation, no remapping.
        output_path: Optional override for the destination path. When
            omitted the canonical default
            ``.ai-engineering/state/watch-residuals.json`` (relative to
            cwd) is used.

    Returns:
        The :class:`~pathlib.Path` written. Identical to ``output_path``
        when provided.
    """
    if output_path is None:
        output_path = Path.cwd() / ".ai-engineering" / "state" / "watch-residuals.json"

    findings = [GateFinding.model_validate(check) for check in failed_checks]

    branch = _git_branch()
    sha = _git_sha()

    doc = GateFindingsDocument(
        schema="ai-engineering/gate-findings/v1",
        session_id=uuid.uuid4(),
        produced_by=GateProducedBy.WATCH_LOOP,
        produced_at=datetime.now(UTC),
        branch=branch,
        commit_sha=sha,
        findings=findings,
        auto_fixed=[],
        cache_hits=[],
        cache_misses=[],
        wall_clock_ms=WallClockMs(wave1_fixers=0, wave2_checkers=0, total=0),
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = doc.model_dump_json(by_alias=True)

    # Atomic publish: write to a sibling tempfile then os.replace into place.
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=str(output_path.parent),
        prefix=f"{output_path.name}.",
        suffix=".tmp",
        delete=False,
        encoding="utf-8",
    ) as tmp:
        tmp.write(payload)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name

    os.replace(tmp_path, str(output_path))
    return output_path
