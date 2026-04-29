"""RED phase tests for `ai_engineering.governance.policy_engine`.

Spec: spec-110 Phase 3 (T-3.6).

These tests exercise the Rego-subset policy engine that will be created in T-3.7
against the three policies dropped by T-3.8:
  - `.ai-engineering/policies/branch_protection.rego`   (deny push to main/master)
  - `.ai-engineering/policies/commit_conventional.rego` (Conventional Commits subject)
  - `.ai-engineering/policies/risk_acceptance_ttl.rego` (TTL not expired)

Each policy gets one allow case and one deny case. Until T-3.7 + T-3.8 land,
all six tests fail individually with ImportError — the canonical RED signal.
The import is performed inside each test (rather than at module top) so that
pytest reports six per-test failures instead of a single collection error.

The contract under test (per plan-110.md T-3.7 and the dispatch task spec):
  - `from ai_engineering.governance.policy_engine import evaluate, Decision`
  - `evaluate(policy_path: Path, input_data: dict) -> Decision`
  - `Decision` is a dataclass exposing at minimum `allow: bool`.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_POLICIES_DIR = _REPO_ROOT / ".ai-engineering" / "policies"

_BRANCH_PROTECTION_REGO = _POLICIES_DIR / "branch_protection.rego"
_COMMIT_CONVENTIONAL_REGO = _POLICIES_DIR / "commit_conventional.rego"
_RISK_ACCEPTANCE_TTL_REGO = _POLICIES_DIR / "risk_acceptance_ttl.rego"


# ---------------------------------------------------------------------------
# branch_protection.rego — deny push to main/master, allow feature branches.
# ---------------------------------------------------------------------------


def test_branch_protection_allow_feature_branch() -> None:
    """Push to a feat/* branch is allowed."""
    from ai_engineering.governance.policy_engine import Decision, evaluate

    decision = evaluate(
        _BRANCH_PROTECTION_REGO,
        {"branch": "feat/spec-110-test", "action": "push"},
    )

    assert isinstance(decision, Decision)
    assert decision.allow is True


def test_branch_protection_deny_main_push() -> None:
    """Push to main is denied (protected branch)."""
    from ai_engineering.governance.policy_engine import Decision, evaluate

    decision = evaluate(
        _BRANCH_PROTECTION_REGO,
        {"branch": "main", "action": "push"},
    )

    assert isinstance(decision, Decision)
    assert decision.allow is False


# ---------------------------------------------------------------------------
# commit_conventional.rego — subject must match Conventional Commits prefix.
# ---------------------------------------------------------------------------


def test_commit_conventional_allow_proper_subject() -> None:
    """A subject with `<type>(<scope>): <description>` is allowed."""
    from ai_engineering.governance.policy_engine import Decision, evaluate

    decision = evaluate(
        _COMMIT_CONVENTIONAL_REGO,
        {"subject": "feat(spec-110): add CONSTITUTION.md baseline"},
    )

    assert isinstance(decision, Decision)
    assert decision.allow is True


def test_commit_conventional_deny_freeform() -> None:
    """A free-form subject without a type/scope prefix is denied."""
    from ai_engineering.governance.policy_engine import Decision, evaluate

    decision = evaluate(
        _COMMIT_CONVENTIONAL_REGO,
        {"subject": "fixed the thing"},
    )

    assert isinstance(decision, Decision)
    assert decision.allow is False


# ---------------------------------------------------------------------------
# risk_acceptance_ttl.rego — allow when TTL has not yet expired.
# ---------------------------------------------------------------------------


def test_risk_acceptance_ttl_allow_unexpired() -> None:
    """Risk acceptance with a future TTL is allowed."""
    from ai_engineering.governance.policy_engine import Decision, evaluate

    decision = evaluate(
        _RISK_ACCEPTANCE_TTL_REGO,
        {
            "ttl_expires_at": "2030-01-01T00:00:00Z",
            "now": "2026-04-29T00:00:00Z",
        },
    )

    assert isinstance(decision, Decision)
    assert decision.allow is True


def test_risk_acceptance_ttl_deny_expired() -> None:
    """Risk acceptance whose TTL has passed is denied."""
    from ai_engineering.governance.policy_engine import Decision, evaluate

    decision = evaluate(
        _RISK_ACCEPTANCE_TTL_REGO,
        {
            "ttl_expires_at": "2025-01-01T00:00:00Z",
            "now": "2026-04-29T00:00:00Z",
        },
    )

    assert isinstance(decision, Decision)
    assert decision.allow is False
