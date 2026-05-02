"""RED tests for spec-117 HX-05 T-2.1 -- canonical state-plane contract.

These tests pin the first explicit state-plane classification contract before
implementation begins. The current repo already has the relevant paths spread
across ``state.control_plane``, ``state.service``, validators, policy
publishers, and report consumers, but there is still no single contract that
states:

1. which global state paths remain durable cross-spec truth,
2. which current-state projections are derived compatibility views,
3. which operator-facing outputs are residue and therefore non-blocking, and
4. which globally parked spec-local audit artifacts require shimmed relocation.

Target API (does not exist yet -- created in HX-05 T-2.2)::

    from ai_engineering.state.control_plane import (
        StatePlaneArtifactClass,
        StatePlaneContract,
        resolve_state_plane_contract,
    )

    contract = resolve_state_plane_contract()

    contract.classify(path: str) -> StatePlaneArtifactClass
    contract.is_required_for_correctness(path: str) -> bool
    contract.requires_compatibility_shim(path: str) -> bool

TDD CONSTRAINT: this file is IMMUTABLE after HX-05 T-2.1 lands. HX-05 T-2.2
may only introduce production code that satisfies these assertions; the
assertions themselves never change.
"""

from __future__ import annotations

_DURABLE_CORE: tuple[str, ...] = (
    ".ai-engineering/state/decision-store.json",
    ".ai-engineering/state/framework-events.ndjson",
    ".ai-engineering/state/install-state.json",
)

_DERIVED_CURRENT_PROJECTIONS: tuple[str, ...] = (
    ".ai-engineering/state/ownership-map.json",
    ".ai-engineering/state/framework-capabilities.json",
)

_RESIDUE_OUTPUTS: tuple[str, ...] = (
    ".ai-engineering/state/gate-findings.json",
    ".ai-engineering/state/watch-residuals.json",
    ".ai-engineering/state/gate-cache/pre-commit.json",
    ".ai-engineering/state/strategic-compact.json",
    ".ai-engineering/state/locks/gate-findings.lock",
)

_SPEC_LOCAL_SPILLOVER: tuple[str, ...] = (
    ".ai-engineering/state/spec-116-t31-audit-classification.json",
    ".ai-engineering/state/spec-116-t41-audit-findings.json",
)


def test_state_plane_contract_classifies_cross_spec_durable_core() -> None:
    """The state plane must name the durable cross-spec core explicitly."""
    from ai_engineering.state.control_plane import (
        StatePlaneArtifactClass,
        resolve_state_plane_contract,
    )

    contract = resolve_state_plane_contract()

    for relative_path in _DURABLE_CORE:
        assert contract.classify(relative_path) is StatePlaneArtifactClass.DURABLE
        assert contract.is_required_for_correctness(relative_path) is True


def test_state_plane_contract_classifies_generated_current_views_as_derived() -> None:
    """Generated current-state projections must stay derived, not durable."""
    from ai_engineering.state.control_plane import (
        StatePlaneArtifactClass,
        resolve_state_plane_contract,
    )

    contract = resolve_state_plane_contract()

    for relative_path in _DERIVED_CURRENT_PROJECTIONS:
        assert contract.classify(relative_path) is StatePlaneArtifactClass.DERIVED
        assert contract.is_required_for_correctness(relative_path) is False
        assert contract.requires_compatibility_shim(relative_path) is False


def test_state_plane_contract_classifies_residue_outputs_as_non_blocking() -> None:
    """Residue paths must stay readable but never correctness-critical."""
    from ai_engineering.state.control_plane import (
        StatePlaneArtifactClass,
        resolve_state_plane_contract,
    )

    contract = resolve_state_plane_contract()

    for relative_path in _RESIDUE_OUTPUTS:
        assert contract.classify(relative_path) is StatePlaneArtifactClass.RESIDUE
        assert contract.is_required_for_correctness(relative_path) is False
        assert contract.requires_compatibility_shim(relative_path) is False


def test_state_plane_contract_marks_global_spec_local_audit_spillover_for_shimmed_relocation() -> (
    None
):
    """Global spec-local evidence must require a readable relocation shim."""
    from ai_engineering.state.control_plane import (
        StatePlaneArtifactClass,
        resolve_state_plane_contract,
    )

    contract = resolve_state_plane_contract()

    for relative_path in _SPEC_LOCAL_SPILLOVER:
        assert contract.classify(relative_path) is StatePlaneArtifactClass.SPEC_LOCAL_EVIDENCE
        assert contract.is_required_for_correctness(relative_path) is False
        assert contract.requires_compatibility_shim(relative_path) is True
