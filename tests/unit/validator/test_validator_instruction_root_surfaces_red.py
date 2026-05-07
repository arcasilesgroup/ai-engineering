"""RED tests for provider-aware root instruction parity coverage.

These tests intentionally fail until the validator checks enabled providers'
root instruction surfaces symmetrically instead of only comparing
``CLAUDE.md`` against ``AGENTS.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ai_engineering.validator._shared import IntegrityReport, IntegrityStatus
from ai_engineering.validator.categories.mirror_sync import _check_instruction_parity

_MANIFEST_TEMPLATE = """\
name: test-project
version: 1.0.0
ai_providers:
  enabled: [{providers}]
  primary: {primary}
"""

_MINIMAL_PARITY_CONTENT = """\
# Instructions

## Skills

- skill1
"""


def _write_manifest(root: Path, providers: list[str]) -> None:
    """Write a minimal manifest with the requested enabled providers."""
    manifest = root / ".ai-engineering" / "manifest.yml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        _MANIFEST_TEMPLATE.format(
            providers=", ".join(providers),
            primary=providers[0],
        ),
        encoding="utf-8",
    )


def _write_file(path: Path, content: str) -> None:
    """Create a UTF-8 text file, including parent directories."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.mark.parametrize(
    ("providers", "missing_surface"),
    [
        (["claude-code", "github_copilot"], ".github/copilot-instructions.md"),
        (["claude-code", "gemini"], "GEMINI.md"),
    ],
)
def test_instruction_parity_flags_missing_enabled_provider_root_surface(
    tmp_path: Path,
    providers: list[str],
    missing_surface: str,
) -> None:
    """Enabled provider-specific root instructions should be parity-validated."""
    _write_manifest(tmp_path, providers)
    _write_file(tmp_path / "CLAUDE.md", _MINIMAL_PARITY_CONTENT)
    _write_file(tmp_path / "AGENTS.md", _MINIMAL_PARITY_CONTENT)

    report = IntegrityReport()

    _check_instruction_parity(tmp_path, report)

    observed_checks = [
        (check.name, check.status.value, check.file_path, check.message) for check in report.checks
    ]

    assert any(
        check.status in (IntegrityStatus.FAIL, IntegrityStatus.WARN)
        and (check.file_path == missing_surface or missing_surface in check.message)
        for check in report.checks
    ), (
        "_check_instruction_parity should flag the missing enabled-provider "
        f"root surface {missing_surface}, but got "
        f"{observed_checks}"
    )


def test_instruction_parity_validates_codex_root_entrypoint_without_claude(
    tmp_path: Path,
) -> None:
    """Codex should not depend on CLAUDE.md before validating its root entry point."""
    _write_manifest(tmp_path, ["codex"])
    _write_file(tmp_path / "AGENTS.md", "# Instructions\n")

    report = IntegrityReport()

    _check_instruction_parity(tmp_path, report)

    observed_checks = [
        (check.name, check.status.value, check.file_path, check.message) for check in report.checks
    ]

    assert any(
        check.status in (IntegrityStatus.FAIL, IntegrityStatus.WARN)
        and (check.file_path == "AGENTS.md" or "AGENTS.md" in check.message)
        for check in report.checks
    ), (
        "_check_instruction_parity should validate Codex's AGENTS.md root "
        "entry point even when claude-code is disabled, but got "
        f"{observed_checks}"
    )
