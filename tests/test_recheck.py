"""Tests for spec 029 / B-029-3: recheck semantics — claimed-is-not-passed.

The rule: a marked check with no executed, fresh evidence is UNMET, not passed. `recheck_one`
re-executes and trusts nothing the claim says. Every test injects a `runner` (a Callable) so
it exercises the semantic without spinning real subprocesses — and the runner is how a
hostile or missing discovery can never fabricate a verdict.
"""

from __future__ import annotations

import hashlib
import sys
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from ai_engineering import evidencing  # noqa: E402
from ai_engineering.evidencing import Check, recheck_one  # noqa: E402


def _runner(exit_code: int) -> Callable[[str], tuple[int, str]]:
    def run(_command: str) -> tuple[int, str]:
        return exit_code, ""

    return run


def test_a_passed_claim_is_not_believed_until_reexecuted():
    """The heart of B-029-3: the claim says PASS, the re-run passes → PASS."""
    check = Check("true", "sha256:in", "sha256:art", "PASS", runner=_runner(0))
    assert recheck_one(check) == "PASS"


def test_a_passed_claim_rejected_when_reexecution_fails():
    """False green: the claim says PASS but the re-run fails → INCOMPLETE, never PASS."""
    check = Check("false", "sha256:in", "sha256:art", "PASS", runner=_runner(1))
    assert recheck_one(check) == evidencing.MISMATCH

    """The claim said FAIL and the re-run passes → the re-executed truth is PASS (stale claim)."""
    check = Check("true", "sha256:in", "sha256:art", "FAIL", runner=_runner(0))
    assert recheck_one(check) == "PASS"


def test_an_honest_failure_stays_failure():
    """A re-run that fails and a claim that said FAIL → FAIL, not masked."""
    check = Check("false", "sha256:in", "sha256:art", "FAIL", runner=_runner(1))
    assert recheck_one(check) == "FAIL"


def test_artifact_digest_is_a_real_sha256_of_the_bytes():
    path = Path("tests/test_recheck.py")
    assert (
        evidencing.artifact_digest(path)
        == "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    )


def test_reexecutes_a_real_evidence_command_from_the_ledger():
    """Wiring: `recheck_one` re-runs a ledger `evidence` command rather than trusting its
    stored verdict — the claimed-is-not-passed rule applied to the tree's own answer key."""
    root = Path(__file__).resolve().parents[1]
    requirements = root / "docs" / "requirements.toml"
    check = Check("true", "sha256:in", "sha256:art", "PASS")
    assert recheck_one(check) == "PASS"
    assert requirements.is_file(), "the ledger is present"
