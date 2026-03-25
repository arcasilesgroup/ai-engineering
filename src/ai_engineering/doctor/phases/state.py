"""Doctor phase: state file validation.

Checks:
- state-files-parseable: All 3 state files exist and parse into their models.
- state-schema: install-state.json has schema_version "2.0" and required fields.
- ownership-coverage: ownership-map patterns cover all defaults from state/defaults.py.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.state.defaults import (
    _DEFAULT_OWNERSHIP_PATHS,
    default_decision_store,
    default_install_state,
    default_ownership_map,
)
from ai_engineering.state.io import write_json_model
from ai_engineering.state.models import InstallState, OwnershipMap


def _state_dir(ctx: DoctorContext) -> Path:
    return ctx.target / ".ai-engineering" / "state"


def _check_files_parseable(ctx: DoctorContext) -> CheckResult:
    """Validate that all 3 state files exist and are parseable."""
    sd = _state_dir(ctx)
    files = {
        "install-state.json": InstallState,
        "ownership-map.json": OwnershipMap,
        "decision-store.json": None,  # generic JSON parse
    }
    missing: list[str] = []
    unparseable: list[str] = []

    for filename, model_cls in files.items():
        path = sd / filename
        if not path.is_file():
            missing.append(filename)
            continue
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if model_cls is not None:
                model_cls.model_validate(data)
        except (json.JSONDecodeError, ValueError, OSError):
            unparseable.append(filename)

    if missing or unparseable:
        parts: list[str] = []
        if missing:
            parts.append(f"missing: {', '.join(missing)}")
        if unparseable:
            parts.append(f"unparseable: {', '.join(unparseable)}")
        return CheckResult(
            name="state-files-parseable",
            status=CheckStatus.FAIL,
            message="; ".join(parts),
            fixable=True,
        )

    return CheckResult(
        name="state-files-parseable",
        status=CheckStatus.OK,
        message="all state files present and parseable",
    )


def _check_state_schema(ctx: DoctorContext) -> CheckResult:
    """Check install-state has schema_version 2.0 and required fields."""
    sd = _state_dir(ctx)
    path = sd / "install-state.json"
    if not path.is_file():
        return CheckResult(
            name="state-schema",
            status=CheckStatus.WARN,
            message="install-state.json not found; cannot validate schema",
        )

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        state = InstallState.model_validate(data)
    except (json.JSONDecodeError, ValueError, OSError):
        return CheckResult(
            name="state-schema",
            status=CheckStatus.WARN,
            message="install-state.json unparseable; cannot validate schema",
        )

    if state.schema_version != "2.0":
        return CheckResult(
            name="state-schema",
            status=CheckStatus.WARN,
            message=f"schema_version is '{state.schema_version}', expected '2.0'",
        )

    # Check required fields are present in the raw data
    required_keys = {"schema_version", "installed_at"}
    raw_keys = set(data.keys())
    missing = required_keys - raw_keys
    if missing:
        return CheckResult(
            name="state-schema",
            status=CheckStatus.WARN,
            message=f"missing required fields: {', '.join(sorted(missing))}",
        )

    return CheckResult(
        name="state-schema",
        status=CheckStatus.OK,
        message="install-state schema valid (v2.0)",
    )


def _check_ownership_coverage(ctx: DoctorContext) -> CheckResult:
    """Compare ownership map patterns against defaults."""
    sd = _state_dir(ctx)
    path = sd / "ownership-map.json"
    if not path.is_file():
        return CheckResult(
            name="ownership-coverage",
            status=CheckStatus.WARN,
            message="ownership-map.json not found; cannot check coverage",
        )

    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
        omap = OwnershipMap.model_validate(data)
    except (json.JSONDecodeError, ValueError, OSError):
        return CheckResult(
            name="ownership-coverage",
            status=CheckStatus.WARN,
            message="ownership-map.json unparseable; cannot check coverage",
        )

    current_patterns = {entry.pattern for entry in omap.paths}
    default_patterns = {p[0] for p in _DEFAULT_OWNERSHIP_PATHS}
    missing = default_patterns - current_patterns

    if missing:
        return CheckResult(
            name="ownership-coverage",
            status=CheckStatus.WARN,
            message=f"{len(missing)} default pattern(s) missing from ownership map",
        )

    return CheckResult(
        name="ownership-coverage",
        status=CheckStatus.OK,
        message="ownership map covers all default patterns",
    )


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all state phase checks."""
    return [
        _check_files_parseable(ctx),
        _check_state_schema(ctx),
        _check_ownership_coverage(ctx),
    ]


def fix(
    ctx: DoctorContext,
    failed: list[CheckResult],
    *,
    dry_run: bool = False,
) -> list[CheckResult]:
    """Attempt to fix failed state checks.

    Only ``state-files-parseable`` is fixable: regenerates missing state files
    from defaults. Other checks are not auto-fixable.
    """
    results: list[CheckResult] = []
    sd = _state_dir(ctx)

    for cr in failed:
        if cr.name != "state-files-parseable":
            results.append(cr)
            continue

        if dry_run:
            results.append(
                CheckResult(
                    name=cr.name,
                    status=CheckStatus.FIXED,
                    message="would regenerate missing state files",
                )
            )
            continue

        # Regenerate missing files
        sd.mkdir(parents=True, exist_ok=True)
        regenerated: list[str] = []

        is_path = sd / "install-state.json"
        if not is_path.is_file():
            write_json_model(is_path, default_install_state())
            regenerated.append("install-state.json")

        om_path = sd / "ownership-map.json"
        if not om_path.is_file():
            write_json_model(om_path, default_ownership_map())
            regenerated.append("ownership-map.json")

        ds_path = sd / "decision-store.json"
        if not ds_path.is_file():
            write_json_model(ds_path, default_decision_store())
            regenerated.append("decision-store.json")

        if regenerated:
            results.append(
                CheckResult(
                    name=cr.name,
                    status=CheckStatus.FIXED,
                    message=f"regenerated: {', '.join(regenerated)}",
                )
            )
        else:
            # Files existed but were unparseable -- re-check
            results.append(cr)

    return results
