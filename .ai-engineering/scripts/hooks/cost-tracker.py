#!/usr/bin/env python3
"""Stop hook: track token usage and estimate costs per session.

Replaces former telemetry-session.sh. Emits session_end event to
audit-log with token counts and estimated cost. Also appends to
~/.claude/metrics/costs.jsonl for ECC compatibility.

Fail-open: exit 0 always, async.
"""

import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from _lib.audit import (
    append_audit_event,
    get_audit_log,
    get_project_root,
    get_session_id,
    is_debug_mode,
    read_stdin,
)

_RATE_TABLE = {
    "haiku": {"input": 0.80, "output": 4.00},
    "sonnet": {"input": 3.00, "output": 15.00},
    "opus": {"input": 15.00, "output": 75.00},
}

_METRICS_DIR = Path.home() / ".claude" / "metrics"


def _extract_tokens(data: dict) -> tuple[int, int]:
    """Extract input and output token counts from stdin data."""
    usage = data.get("usage", {})

    tokens_in = usage.get("input_tokens", usage.get("prompt_tokens", 0))
    tokens_out = usage.get("output_tokens", usage.get("completion_tokens", 0))

    if not isinstance(tokens_in, (int, float)):
        tokens_in = 0
    if not isinstance(tokens_out, (int, float)):
        tokens_out = 0

    return int(tokens_in), int(tokens_out)


def _extract_model(data: dict) -> str:
    """Extract model name from stdin data or environment."""
    model = ""

    input_data = data.get("input", {})
    if isinstance(input_data, dict):
        model = input_data.get("model", "")

    if not model:
        cursor_data = data.get("_cursor", {})
        if isinstance(cursor_data, dict):
            model = cursor_data.get("model", "")

    if not model:
        model = os.environ.get("CLAUDE_MODEL", "")

    return model if isinstance(model, str) else str(model)


def _detect_tier(model: str) -> str:
    """Detect pricing tier from model name."""
    model_lower = model.lower()
    if "haiku" in model_lower:
        return "haiku"
    if "opus" in model_lower:
        return "opus"
    return "sonnet"


def _estimate_cost(tokens_in: int, tokens_out: int, tier: str) -> float:
    """Estimate cost in USD with 6 decimal precision."""
    rates = _RATE_TABLE.get(tier, _RATE_TABLE["sonnet"])
    cost_in = (tokens_in / 1_000_000) * rates["input"]
    cost_out = (tokens_out / 1_000_000) * rates["output"]
    return round(cost_in + cost_out, 6)


def main() -> None:
    data = read_stdin()

    tokens_in, tokens_out = _extract_tokens(data)
    model = _extract_model(data)
    tier = _detect_tier(model)
    estimated_cost = _estimate_cost(tokens_in, tokens_out, tier)
    session_id = get_session_id()
    project_root = get_project_root()
    audit_log = get_audit_log(project_root)
    timestamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    append_audit_event(
        audit_log,
        {
            "event": "session_end",
            "actor": "ai-session",
            "detail": {
                "type": "session_end",
                "session_id": session_id,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "estimated_cost_usd": estimated_cost,
                "model": model,
                "tier": tier,
            },
        },
        project_root=project_root,
    )

    try:
        _METRICS_DIR.mkdir(parents=True, exist_ok=True)
        costs_file = _METRICS_DIR / "costs.jsonl"
        cost_record = {
            "timestamp": timestamp,
            "session_id": session_id,
            "model": model,
            "tier": tier,
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "estimated_cost_usd": estimated_cost,
            "project": project_root.name,
        }
        with open(costs_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(cost_record, separators=(",", ":")) + "\n")
    except Exception:
        pass

    if is_debug_mode():
        debug_log = project_root / ".ai-engineering" / "state" / "telemetry-debug.log"
        try:
            with open(debug_log, "a", encoding="utf-8") as f:
                f.write(
                    f"[{timestamp}] session_end: model={model} tier={tier} "
                    f"in={tokens_in} out={tokens_out} cost=${estimated_cost:.6f}\n"
                )
        except Exception:
            pass


if __name__ == "__main__":
    import contextlib

    with contextlib.suppress(Exception):
        main()
    sys.exit(0)
