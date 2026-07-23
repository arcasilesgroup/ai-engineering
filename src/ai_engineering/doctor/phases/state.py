"""Doctor phase: state file validation (spec-148 files-only).

Checks:
- state-files-parseable: install-state.json + framework-capabilities.json
  load cleanly via the canonical repository readers.
- state-schema: install-state.json has schema_version "2.0" and required fields.
- ownership-coverage: ownership-map.json covers all defaults from state/defaults.py.
"""

from __future__ import annotations

from pathlib import Path

from ai_engineering.config.loader import load_manifest_root_entry_points
from ai_engineering.doctor.models import CheckResult, CheckStatus, DoctorContext
from ai_engineering.state.defaults import (
    default_install_state,
    default_ownership_paths,
)
from ai_engineering.state.io import write_json_model
from skill_domain.state_models import InstallState


def _state_dir(ctx: DoctorContext) -> Path:
    return ctx.target / ".ai-engineering" / "state"


def _check_files_parseable(ctx: DoctorContext) -> CheckResult:
    """Validate that the canonical state files load cleanly (spec-148 files-only).

    The install-completed signal is ``install-state.json``; FAIL when it is
    absent (uninstalled) or when it / framework-capabilities.json fail to
    load via the canonical repository readers.
    """
    from ai_engineering.state.repository import DurableStateRepository

    state_dir = _state_dir(ctx)
    if not state_dir.is_dir():
        return CheckResult(
            name="state-files-parseable",
            status=CheckStatus.FAIL,
            message="state directory missing at .ai-engineering/state/",
            fixable=True,
        )

    if not (state_dir / "install-state.json").is_file():
        return CheckResult(
            name="state-files-parseable",
            status=CheckStatus.FAIL,
            message="install-state.json missing",
            fixable=True,
        )

    repo = DurableStateRepository(ctx.target)
    failures: list[str] = []

    try:
        state = repo.load_install_state()
        InstallState.model_validate(state.model_dump(mode="python"))
    except (ValueError, OSError) as exc:
        failures.append(f"install-state.json: {exc}")

    try:
        repo.load_framework_capabilities()
    except (ValueError, OSError) as exc:
        failures.append(f"framework-capabilities.json: {exc}")

    if failures:
        return CheckResult(
            name="state-files-parseable",
            status=CheckStatus.FAIL,
            message="; ".join(failures),
            fixable=True,
        )

    return CheckResult(
        name="state-files-parseable",
        status=CheckStatus.OK,
        message="state files load cleanly",
    )


def _check_state_schema(ctx: DoctorContext) -> CheckResult:
    """Check install-state.json has schema_version 2.0 and required fields.

    spec-148 files-only: install state lives in ``install-state.json``. WARN
    (rather than fix) when the file is absent — ``_check_files_parseable``
    reports the FAIL with a fixer.
    """
    from ai_engineering.state.repository import DurableStateRepository

    if not (_state_dir(ctx) / "install-state.json").is_file():
        return CheckResult(
            name="state-schema",
            status=CheckStatus.WARN,
            message="install-state.json missing; schema cannot be validated",
        )

    try:
        state = DurableStateRepository(ctx.target).load_install_state()
    except (ValueError, OSError):
        return CheckResult(
            name="state-schema",
            status=CheckStatus.WARN,
            message="install-state.json unloadable; cannot validate schema",
        )

    if state.schema_version != "2.0":
        return CheckResult(
            name="state-schema",
            status=CheckStatus.WARN,
            message=f"schema_version is '{state.schema_version}', expected '2.0'",
        )

    if state.installed_at is None:
        return CheckResult(
            name="state-schema",
            status=CheckStatus.WARN,
            message="missing required field: installed_at",
        )

    return CheckResult(
        name="state-schema",
        status=CheckStatus.OK,
        message="install_state schema valid (v2.0)",
    )


def _check_ownership_coverage(ctx: DoctorContext) -> CheckResult:
    """Compare ownership-map.json patterns against defaults (spec-148 files-only)."""
    from ai_engineering.state.repository import DurableStateRepository

    path = _state_dir(ctx) / "ownership-map.json"
    if not path.is_file():
        return CheckResult(
            name="ownership-coverage",
            status=CheckStatus.WARN,
            message="ownership-map.json absent; cannot check coverage",
        )
    try:
        omap = DurableStateRepository(ctx.target).load_ownership()
    except (ValueError, OSError):
        return CheckResult(
            name="ownership-coverage",
            status=CheckStatus.WARN,
            message="ownership-map.json unparseable; cannot check coverage",
        )
    current_patterns = {entry.pattern for entry in omap.paths}

    default_patterns = {
        pattern
        for pattern, _, _ in default_ownership_paths(
            root_entry_points=load_manifest_root_entry_points(ctx.target),
        )
    }
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


def _check_audit_chain_events(ctx: DoctorContext) -> CheckResult:
    """Advisory check (spec-107 D-107-10 / G-12, H2): hash-chain over events.

    Verifies the ``framework-events.ndjson`` audit chain by walking
    ``prev_event_hash`` pointers. Pure WARN advisory: never FAIL, never
    block. A missing file (no events emitted yet) is OK. A chain break
    surfaces as WARN with the first break index + reason so operators
    can investigate without blocking the install/doctor flow.
    """
    from ai_engineering.state.audit_chain import verify_audit_chain

    advisory_name = "audit-chain-events"
    sd = _state_dir(ctx)
    events_path = sd / "framework-events.ndjson"
    if not events_path.is_file():
        return CheckResult(
            name=advisory_name,
            status=CheckStatus.OK,
            message="framework-events.ndjson not present; chain vacuously valid",
        )
    verdict = verify_audit_chain(events_path, mode="ndjson")
    if verdict.ok:
        return CheckResult(
            name=advisory_name,
            status=CheckStatus.OK,
            message=(f"events chain intact ({verdict.entries_checked} entries verified)"),
        )
    return CheckResult(
        name=advisory_name,
        status=CheckStatus.WARN,
        message=(
            f"events chain break at index {verdict.first_break_index}: {verdict.first_break_reason}"
        ),
    )


def _check_audit_chain_decisions(ctx: DoctorContext) -> CheckResult:
    """Advisory check (spec-107 D-107-10 / G-12, H2): hash-chain over decisions.

    Verifies the ``decision-store.json`` audit chain by walking
    ``prev_event_hash`` pointers across the ``decisions`` array. Pure
    WARN advisory: never FAIL, never block. Legacy decisions written
    before spec-107 lack the field and are treated as valid by the
    verifier (additive backward-compat per D-107-10).

    spec-124 D-124-12: ``decision-store.json`` migrated to state.db; the
    JSON-array hash-chain check no longer applies on disk. State.db
    rows carry their own audit hash via the ``decisions`` table.
    """
    from ai_engineering.state.audit_chain import verify_audit_chain

    advisory_name = "audit-chain-decisions"
    sd = _state_dir(ctx)
    decisions_path = sd / "decision-store.json"
    if not decisions_path.is_file():
        return CheckResult(
            name=advisory_name,
            status=CheckStatus.OK,
            message=(
                "decision-store.json not present (spec-124 D-124-12); "
                "state.db.decisions is canonical"
            ),
        )
    verdict = verify_audit_chain(decisions_path, mode="json_array")
    if verdict.ok:
        return CheckResult(
            name=advisory_name,
            status=CheckStatus.OK,
            message=(f"decisions chain intact ({verdict.entries_checked} entries verified)"),
        )
    return CheckResult(
        name=advisory_name,
        status=CheckStatus.WARN,
        message=(
            f"decisions chain break at index {verdict.first_break_index}: "
            f"{verdict.first_break_reason}"
        ),
    )


def check(ctx: DoctorContext) -> list[CheckResult]:
    """Run all state phase checks."""
    return [
        _check_files_parseable(ctx),
        _check_state_schema(ctx),
        _check_ownership_coverage(ctx),
        _check_audit_chain_events(ctx),
        _check_audit_chain_decisions(ctx),
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

        # Regenerate missing files. Only ``install-state.json`` is regenerated
        # post-spec-124 D-124-12 -- ``ownership-map.json`` and
        # ``decision-store.json`` were migrated to ``state.db`` in wave 5
        # and must not be recreated on disk.
        sd.mkdir(parents=True, exist_ok=True)
        regenerated: list[str] = []

        is_path = sd / "install-state.json"
        if not is_path.is_file():
            write_json_model(is_path, default_install_state())
            regenerated.append("install-state.json")

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
