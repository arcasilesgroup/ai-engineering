"""Integration tests for spec-107 G-3 — doctor permissions advisory.

Spec-107 D-107-02 requires ``ai-eng doctor`` to emit a WARN advisory
named ``permissions-wildcard-detected`` whenever a project's
``.claude/settings.json`` ``permissions.allow`` list contains the
``"*"`` wildcard. The check is advisory-only (never FAIL), pointing at
``contexts/permissions-migration.md`` for remediation. Projects with
explicit narrow allow lists must produce zero advisory.

GREEN as of Phase 2 (T-2.3 / T-2.7) — the
``ide_config._check_permissions_wildcard`` advisory is wired and this
test guards against regressions.
"""

from __future__ import annotations

import json
from pathlib import Path

from ai_engineering.doctor.models import CheckStatus, DoctorContext
from ai_engineering.doctor.phases import ide_config

ADVISORY_NAME = "permissions-wildcard-detected"


def _write_settings(target: Path, *, allow: list[str]) -> Path:
    """Materialise a minimal ``.claude/settings.json`` fixture for tests."""
    settings_dir = target / ".claude"
    settings_dir.mkdir(parents=True, exist_ok=True)
    settings_path = settings_dir / "settings.json"
    payload = {
        "permissions": {
            "allow": allow,
            "deny": ["Bash(rm -rf *)"],
        },
        "hooks": {},
    }
    settings_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return settings_path


def _build_ctx(target: Path) -> DoctorContext:
    """Build a minimal DoctorContext sufficient for the wildcard advisory."""
    return DoctorContext(target=target)


def test_wildcard_allow_emits_warn_advisory(tmp_path: Path) -> None:
    """G-3: ``["*"]`` allow list must surface a WARN advisory."""
    target = tmp_path / "project"
    target.mkdir()
    _write_settings(target, allow=["*"])
    ctx = _build_ctx(target)

    # The check function will be added to ide_config in Phase 2 T-2.3.
    check_fn = getattr(ide_config, "_check_permissions_wildcard", None)
    assert check_fn is not None, (
        "ide_config._check_permissions_wildcard not implemented yet — "
        "expected to land in Phase 2 T-2.3 per D-107-02"
    )
    result = check_fn(ctx)
    assert result.name == ADVISORY_NAME
    assert result.status == CheckStatus.WARN, (
        f"wildcard allow must produce WARN advisory, got {result.status!r}"
    )
    assert "permissions-migration.md" in result.message, (
        "advisory message must point at the migration guide for remediation"
    )


def test_narrow_allow_emits_no_advisory(tmp_path: Path) -> None:
    """G-3: explicit narrow allow list must NOT produce an advisory."""
    target = tmp_path / "project"
    target.mkdir()
    _write_settings(
        target,
        allow=[
            "Read",
            "Write",
            "Edit",
            "MultiEdit",
            "Bash",
            "Agent",
            "Glob",
            "Grep",
            "Skill",
        ],
    )
    ctx = _build_ctx(target)

    check_fn = getattr(ide_config, "_check_permissions_wildcard", None)
    assert check_fn is not None
    result = check_fn(ctx)
    assert result.status == CheckStatus.OK, (
        f"narrow allow list must produce OK status, got {result.status!r}"
    )


def test_missing_settings_emits_no_advisory(tmp_path: Path) -> None:
    """G-3 boundary: absence of settings.json must not produce an advisory.

    The check covers wildcard *content*, not file presence — that
    scenario is already handled by the existing ``settings-merge``
    check.
    """
    target = tmp_path / "project"
    target.mkdir()
    ctx = _build_ctx(target)

    check_fn = getattr(ide_config, "_check_permissions_wildcard", None)
    assert check_fn is not None
    result = check_fn(ctx)
    assert result.status == CheckStatus.OK, (
        "missing settings.json must NOT produce a wildcard advisory"
    )


def test_advisory_never_fails(tmp_path: Path) -> None:
    """G-3 boundary: even an egregious wildcard must NEVER FAIL doctor.

    The check is advisory-only per D-107-02 + NG-2 of D-107-02 (cero
    forced disruption). It must surface as WARN at most so legacy
    projects keep operating.
    """
    target = tmp_path / "project"
    target.mkdir()
    _write_settings(target, allow=["*"])
    ctx = _build_ctx(target)

    check_fn = getattr(ide_config, "_check_permissions_wildcard", None)
    assert check_fn is not None
    result = check_fn(ctx)
    assert result.status != CheckStatus.FAIL, (
        "permissions-wildcard-detected must NEVER FAIL — advisory only per D-107-02"
    )
