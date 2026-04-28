"""Phase 1 GREEN: shared execution-kernel extraction (spec-106 G-1).

Asserts:

1. ``.claude/skills/_shared/execution-kernel.md`` exists.
2. The three orchestrator SKILL.md files (dispatch, autopilot, run) each
   reference the shared kernel via the canonical ``_shared/execution-kernel.md``
   path -- delegation, not inline kernel.
3. Combined line count of the three orchestrators decreased by >=150 lines
   relative to the pre-extraction baseline. Baseline measured 2026-04-27 with
   ``wc -l`` BEFORE T-1.3 edits; recorded as ``PRE_BASELINE_LINES`` constant.

These tests are GREEN at commit time -- they guard against future drift that
would re-inline the kernel or undo the line-budget reduction.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SHARED_KERNEL = REPO_ROOT / ".claude" / "skills" / "_shared" / "execution-kernel.md"
DISPATCH = REPO_ROOT / ".claude" / "skills" / "ai-dispatch" / "SKILL.md"
AUTOPILOT = REPO_ROOT / ".claude" / "skills" / "ai-autopilot" / "SKILL.md"
RUN = REPO_ROOT / ".claude" / "skills" / "ai-run" / "SKILL.md"

# Pre-extraction baseline (measured 2026-04-27 BEFORE T-1.3 edits via wc -l):
#   ai-dispatch/SKILL.md   157
#   ai-autopilot/SKILL.md  192
#   ai-run/SKILL.md        145
#   ----------------------------
#   combined               494
PRE_BASELINE_LINES = 494
LINE_REDUCTION_TARGET = 150
POST_BUDGET = PRE_BASELINE_LINES - LINE_REDUCTION_TARGET  # 344

# Canonical reference string consumers must contain to prove delegation.
DELEGATION_MARKER = "_shared/execution-kernel.md"


def _line_count(path: Path) -> int:
    """Count lines the way ``wc -l`` does (matches human-visible output)."""
    return len(path.read_text(encoding="utf-8").splitlines())


def test_shared_execution_kernel_exists() -> None:
    """Shared handler file must exist at the canonical _shared/ path."""
    assert SHARED_KERNEL.exists(), f"missing shared handler: {SHARED_KERNEL}"
    body = SHARED_KERNEL.read_text(encoding="utf-8")
    assert body.strip(), "shared kernel must not be empty"
    # Sanity: the kernel must declare its consumers so future maintainers
    # do not orphan it during a sweep.
    assert "## Consumers" in body, (
        "execution-kernel.md must include a '## Consumers' section listing "
        "ai-dispatch, ai-autopilot, ai-run"
    )


def test_dispatch_delegates_to_kernel() -> None:
    """ai-dispatch must reference the shared kernel (no inline duplication)."""
    assert DISPATCH.exists(), f"missing skill file: {DISPATCH}"
    text = DISPATCH.read_text(encoding="utf-8")
    assert DELEGATION_MARKER in text, (
        f"ai-dispatch/SKILL.md must reference '{DELEGATION_MARKER}' to delegate "
        f"the dispatch-per-task -> build-verify-review loop instead of inlining it"
    )


def test_autopilot_delegates_to_kernel() -> None:
    """ai-autopilot must reference the shared kernel for its per-wave loop."""
    assert AUTOPILOT.exists(), f"missing skill file: {AUTOPILOT}"
    text = AUTOPILOT.read_text(encoding="utf-8")
    assert DELEGATION_MARKER in text, (
        f"ai-autopilot/SKILL.md must reference '{DELEGATION_MARKER}' so the "
        f"per-wave dispatch loop reuses the canonical kernel"
    )


def test_run_delegates_to_kernel() -> None:
    """ai-run must reference the shared kernel for its per-item loop."""
    assert RUN.exists(), f"missing skill file: {RUN}"
    text = RUN.read_text(encoding="utf-8")
    assert DELEGATION_MARKER in text, (
        f"ai-run/SKILL.md must reference '{DELEGATION_MARKER}' so the per-item "
        f"backlog execution loop reuses the canonical kernel"
    )


def test_combined_orchestrator_line_count_reduced_by_150() -> None:
    """Combined dispatch+autopilot+run line count must drop >=150 vs baseline.

    spec-106 G-1: extracting the kernel must produce a measurable reduction
    in the orchestrator surface area; this test fails if a future edit
    re-inlines the kernel or otherwise inflates the orchestrators back past
    the post-extraction budget.
    """
    actual = _line_count(DISPATCH) + _line_count(AUTOPILOT) + _line_count(RUN)
    reduction = PRE_BASELINE_LINES - actual
    assert actual <= POST_BUDGET, (
        f"Combined orchestrator line count {actual} exceeds post-extraction "
        f"budget {POST_BUDGET} (baseline {PRE_BASELINE_LINES} - target reduction "
        f"{LINE_REDUCTION_TARGET}). Current reduction: {reduction} lines."
    )
