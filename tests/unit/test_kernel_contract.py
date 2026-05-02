"""RED tests for spec-117 HX-04 T-2.1 -- canonical kernel contract.

These tests pin the first executable contract for the HX-04 harness kernel
before implementation begins. The current repo already has the pieces spread
across ``policy.orchestrator``, ``policy.mode_dispatch``, ``watch_residuals``,
and the gate CLI adapter, but there is still no single explicit contract that
states:

1. which checks are registered for the active local kernel run,
2. which gate mode actually resolved,
3. which findings-envelope family is authoritative,
4. how residual output stays compatible with that envelope, and
5. which layer owns findings publication during the parity-first migration.

Target API (does not exist yet -- created in HX-04 T-2.2)::

    from ai_engineering.policy.orchestrator import KernelContract, resolve_kernel_contract

    contract = resolve_kernel_contract(
        project_root: Path,
        mode: str = "local",
    )

    # minimal required fields for Phase 2
    contract.check_registration: tuple[str, ...]
    contract.gate_mode: Literal["regulated", "prototyping"]
    contract.findings_document_model: type[GateFindingsDocument]
    contract.findings_schema: str
    contract.residual_document_model: type[GateFindingsDocument]
    contract.residual_output_name: str
    contract.publish_owner: Literal["adapter", "kernel"]

TDD CONSTRAINT: this file is IMMUTABLE after HX-04 T-2.1 lands. HX-04 T-2.2
may only introduce production code that satisfies these assertions; the
assertions themselves never change.
"""

from __future__ import annotations

from pathlib import Path
from unittest import mock

from ai_engineering.state.models import GateFindingsDocument

_LOCAL_REGULATED_REGISTRATION: tuple[str, ...] = (
    "gitleaks",
    "ruff",
    "ty",
    "pytest-smoke",
    "validate",
)

_LOCAL_PROTOTYPING_REGISTRATION: tuple[str, ...] = (
    "gitleaks",
    "ruff",
    "ty",
    "pytest-smoke",
)


def _seed_manifest(root: Path, *, declared_mode: str) -> None:
    ai_dir = root / ".ai-engineering"
    specs_dir = ai_dir / "specs"
    state_dir = ai_dir / "state"
    specs_dir.mkdir(parents=True, exist_ok=True)
    state_dir.mkdir(parents=True, exist_ok=True)
    (ai_dir / "manifest.yml").write_text(
        "\n".join(
            [
                "schema_version: '2.0'",
                "providers:",
                "  stacks: [python]",
                "gates:",
                f"  mode: {declared_mode}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (specs_dir / "spec.md").write_text("# Active spec\n", encoding="utf-8")
    (specs_dir / "plan.md").write_text("# Active plan\n", encoding="utf-8")


def test_kernel_contract_local_registration_matches_regulated_mode(tmp_path: Path) -> None:
    """Default local registration must expose the regulated local kernel set.

    On a feature branch with no CI or push-target escalation, a manifest that
    declares ``regulated`` should still resolve to the canonical five local
    checks. Registration must come from the kernel contract rather than being
    inferred from independent tier and dispatcher tables.
    """
    _seed_manifest(tmp_path, declared_mode="regulated")

    with mock.patch("subprocess.check_output", return_value="feature/hx04\n"):
        from ai_engineering.policy.orchestrator import resolve_kernel_contract

        contract = resolve_kernel_contract(tmp_path, mode="local")

    assert contract.gate_mode == "regulated"
    assert contract.check_registration == _LOCAL_REGULATED_REGISTRATION, (
        "Kernel registration drifted from the regulated local contract; "
        f"expected {_LOCAL_REGULATED_REGISTRATION!r}, got {contract.check_registration!r}"
    )


def test_kernel_contract_feature_branch_honors_prototyping_registration(tmp_path: Path) -> None:
    """Feature-branch prototyping must drop Tier 2 local registration.

    The Phase 2 kernel contract must make the resolved mode and resulting local
    registration explicit in one place; otherwise check registration and mode
    resolution continue to drift independently.
    """
    _seed_manifest(tmp_path, declared_mode="prototyping")

    with mock.patch("subprocess.check_output", return_value="feature/hx04\n"):
        from ai_engineering.policy.orchestrator import resolve_kernel_contract

        contract = resolve_kernel_contract(tmp_path, mode="local")

    assert contract.gate_mode == "prototyping"
    assert contract.check_registration == _LOCAL_PROTOTYPING_REGISTRATION, (
        "Feature-branch prototyping must exclude the Tier 2 local checker "
        f"from kernel registration; got {contract.check_registration!r}"
    )


def test_kernel_contract_protected_branch_escalates_to_regulated(tmp_path: Path) -> None:
    """Protected-branch resolution must force regulated local registration."""
    _seed_manifest(tmp_path, declared_mode="prototyping")

    with mock.patch("subprocess.check_output", return_value="main\n"):
        from ai_engineering.policy.orchestrator import resolve_kernel_contract

        contract = resolve_kernel_contract(tmp_path, mode="local")

    assert contract.gate_mode == "regulated"
    assert contract.check_registration == _LOCAL_REGULATED_REGISTRATION, (
        "Protected branches must escalate prototyping to the regulated local "
        f"kernel registration; got {contract.check_registration!r}"
    )


def test_kernel_contract_declares_findings_and_residual_envelope_compatibility(
    tmp_path: Path,
) -> None:
    """The kernel contract must name one findings envelope plus residual parity.

    ``GateFindingsDocument`` remains the normalized envelope seed for HX-04,
    and watch residuals remain compatibility-safe siblings of that model family.
    The contract must state both explicitly.
    """
    _seed_manifest(tmp_path, declared_mode="regulated")

    with mock.patch("subprocess.check_output", return_value="feature/hx04\n"):
        from ai_engineering.policy.orchestrator import resolve_kernel_contract

        contract = resolve_kernel_contract(tmp_path, mode="local")

    assert contract.findings_document_model is GateFindingsDocument
    assert contract.findings_schema == "ai-engineering/gate-findings/v1"
    assert contract.residual_document_model is GateFindingsDocument
    assert contract.residual_output_name == "watch-residuals.json"


def test_kernel_contract_makes_publish_owner_explicit_for_phase2_first_cut(
    tmp_path: Path,
) -> None:
    """Phase 2 must state which layer owns findings publication.

    The guard review and compatibility boundary kept publish ownership on the
    adapter side for the first cut. The kernel contract must expose that fact
    explicitly so later cutover can be tested rather than inferred.
    """
    _seed_manifest(tmp_path, declared_mode="regulated")

    with mock.patch("subprocess.check_output", return_value="feature/hx04\n"):
        from ai_engineering.policy.orchestrator import resolve_kernel_contract

        contract = resolve_kernel_contract(tmp_path, mode="local")

    assert contract.publish_owner == "adapter", (
        "The Phase 2 first cut must make findings publication ownership explicit "
        "instead of leaving it split across layers implicitly."
    )
