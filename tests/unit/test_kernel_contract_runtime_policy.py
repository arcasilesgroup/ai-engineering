"""HX-04 T-2.3 -- runtime policy carried by the shared kernel contract."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from unittest import mock


def _seed_manifest(root: Path, *, declared_mode: str = "regulated") -> None:
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


def _resolve_contract(project_root: Path):
    with mock.patch("subprocess.check_output", return_value="feature/hx04\n"):
        from ai_engineering.policy.orchestrator import resolve_kernel_contract

        return resolve_kernel_contract(project_root, mode="local")


def test_kernel_contract_declares_retry_ceiling_of_three(tmp_path: Path) -> None:
    _seed_manifest(tmp_path)

    contract = _resolve_contract(tmp_path)

    assert contract.retry_ceiling == 3, (
        f"Kernel retry ceiling must stay at 3 for the first HX-04 cut; got {contract.retry_ceiling!r}"  # noqa: E501
    )


def test_kernel_contract_declares_active_and_passive_loop_caps(tmp_path: Path) -> None:
    _seed_manifest(tmp_path)

    contract = _resolve_contract(tmp_path)

    assert contract.active_loop_cap == timedelta(minutes=30)
    assert contract.passive_loop_cap == timedelta(hours=4)


def test_kernel_contract_exposes_blocked_disposition_output(tmp_path: Path) -> None:
    _seed_manifest(tmp_path)

    contract = _resolve_contract(tmp_path)

    assert contract.blocked_disposition.status == "blocked"
    assert contract.blocked_disposition.exit_code == 90
    assert contract.blocked_disposition.residual_output_name == contract.residual_output_name
    assert "ai-eng risk accept-all" in contract.blocked_disposition.next_action_command
