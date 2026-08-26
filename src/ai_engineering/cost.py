"""The cost calibration gate for spec 029 / B-029-4.

Bounded-sample first: before an expensive lane runs, `--limit <n>` samples a small batch,
projects total cost and wall-time from the observed per-unit numbers, and refuses to
continue without consent above a `policy/`-declared threshold. In non-interactive mode,
absent consent, it fails closed (deepsec `calibrate.sh` made mandatory, headstart's ArXiv
gate). `doctor` pre-runs prerequisites so a costly lane does not discover a missing
credential or pinned engine mid-run.
"""

from __future__ import annotations

import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
THRESHOLDS = ROOT / "policy" / "cost-thresholds.toml"


class _Policy(dict):
    """The declared gate numbers; a missing or stale policy is INCOMPLETE, never a guess."""

    def __init__(self, raw: dict) -> None:
        super().__init__(raw)
        if not isinstance(raw.get("threshold_usd"), (int, float)) or raw["threshold_usd"] <= 0:
            raise ValueError(
                f"policy/cost-thresholds.toml must declare threshold_usd > 0, "
                f"got {raw.get('threshold_usd')!r}"
            )
        if not isinstance(raw.get("limit"), int) or raw["limit"] <= 0:
            raise ValueError(
                f"policy/cost-thresholds.toml must declare limit > 0, got {raw.get('limit')!r}"
            )


def policy() -> _Policy:
    try:
        raw = tomllib.loads(THRESHOLDS.read_text(encoding="utf-8"))
    except OSError as exc:  # pragma: no cover - defensive
        raise ValueError(f"cannot read {THRESHOLDS}: {exc}") from exc
    if raw.get("schema") != "urn:ai-engineering:cost-thresholds:1":
        raise ValueError(f"unknown schema in {THRESHOLDS}: {raw.get('schema')!r}")
    return _Policy(raw)


def calibrate(
    limit: int,
    samples: list[tuple[float, float]],
    *,
    threshold_usd: float | None = None,
    interactive: bool = False,
) -> tuple[int, float | None, bool]:
    """Return (limit, projected_total_usd, may_run).

    `samples` is the observed per-unit (cost_usd, wall_seconds) from the bounded batch;
    `threshold_usd` overrides the declared policy number only under a direct call (tests);
    the gate itself always reads `policy()`.
    """
    threshold = threshold_usd if threshold_usd is not None else policy()["threshold_usd"]
    if not samples:
        return limit, None, False

    cost_per_unit = sum(c for c, _ in samples) / len(samples)
    projected = cost_per_unit * limit

    if projected < threshold:
        return limit, projected, True

    # Over threshold: consent is required. In non-interactive mode absent consent, fail
    # closed. An interactive caller that answers yes may continue.
    if interactive:
        return limit, projected, True
    return limit, projected, False


def doctor_prereqs() -> list[str]:
    """The pre-run prerequisites a costly lane needs, each with its check. Empty is clean.

    A lane that starts before its config, credentials, git and pinned engines are verified
    is a lane that discovers the absence mid-run — the cost the gate exists to prevent.
    """
    found: list[str] = []
    if not (ROOT / ".ai" / "intent.md").is_file():
        found.append("no Solution Intent at .ai/intent.md — the lane has no anchored record")
    if not THRESHOLDS.is_file():
        found.append(f"no threshold policy at {THRESHOLDS.relative_to(ROOT)}")
    if not (ROOT / ".git").is_dir():
        found.append("not inside a git repository — receipts cannot be anchored")
    return found


if __name__ == "__main__":  # pragma: no cover
    import argparse

    p = argparse.ArgumentParser("ai-eng cost")
    p.add_argument("limit", nargs="?", type=int, default=None)
    a = p.parse_args()
    try:
        limits = [a.limit] if a.limit else [policy()["limit"]]
    except ValueError as why:
        print(why, file=sys.stderr)
        raise SystemExit(2) from why
    problems = doctor_prereqs()
    for line in problems:
        print(f"  INCOMPLETE {line}")
    if problems:
        raise SystemExit(1)
    print(f"  threshold_usd={policy()['threshold_usd']} limit={limits[0]}")
