"""State file integrity diagnostic check."""

from __future__ import annotations

from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorReport
from ai_engineering.state.io import read_json_model
from ai_engineering.state.models import InstallState, OwnershipMap

# Required state files
_REQUIRED_STATE_FILES: list[str] = [
    "state/install-state.json",
    "state/ownership-map.json",
    "state/decision-store.json",
]


def check_state_files(target: Path, report: DoctorReport) -> None:
    """Check that state files exist and are parseable."""
    ai_eng = target / ".ai-engineering"

    for relative in _REQUIRED_STATE_FILES:
        path = ai_eng / relative
        name = f"state:{Path(relative).name}"

        if not path.is_file():
            report.checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.FAIL,
                    message=f"Missing: {relative}",
                )
            )
            continue

        try:
            if "install-state" in relative:
                read_json_model(path, InstallState)
            elif "ownership-map" in relative:
                read_json_model(path, OwnershipMap)
            else:
                import json

                json.loads(path.read_text(encoding="utf-8"))

            report.checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.OK,
                    message=f"Valid: {relative}",
                )
            )
        except Exception as exc:
            report.checks.append(
                CheckResult(
                    name=name,
                    status=CheckStatus.FAIL,
                    message=f"Invalid {relative}: {exc}",
                )
            )
