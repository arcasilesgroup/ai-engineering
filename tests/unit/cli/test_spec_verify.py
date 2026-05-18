"""Unit tests for ``ai-eng spec verify --sections`` (spec-139 M7.T1).

The ``--sections`` flag runs a deterministic regex/string-contains scan for
the five required headers declared in
``.ai-engineering/reference/spec-schema.md``: ``## Summary``, ``## Goals``,
``## Non-Goals``, ``## Decisions``, ``## Risks``. Optional headers
(``## References``, ``## Open Questions``) do not influence validity.

Exit codes:
- 0 when every required section is present (``valid=true``).
- 1 when one or more required sections are missing (``valid=false``).
- 1 when the spec path does not exist (error envelope on stderr).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

_FIXTURES = Path(__file__).parent / "fixtures" / "spec_verify"


@pytest.fixture()
def app() -> typer.Typer:
    from ai_engineering.cli_factory import create_app

    return create_app()


def _invoke(app: typer.Typer, spec_path: Path) -> tuple[int, str]:
    """Invoke ``spec verify --sections <path>`` and return (exit, combined_output).

    Older Typer (0.21.x) does not support ``mix_stderr=False`` on
    ``CliRunner``; stdout and stderr land in the same ``result.output``
    string. Tests inspect that combined stream — the JSON payload is the
    only line either path emits, so a single ``json.loads`` works for
    success and failure cases alike.
    """
    runner = CliRunner()
    result = runner.invoke(app, ["spec", "verify", "--sections", str(spec_path)])
    return result.exit_code, result.output


class TestSpecVerifySections:
    def test_complete_spec_is_valid(self, app: typer.Typer) -> None:
        """All required sections present → valid=true, missing=[], exit 0."""
        exit_code, output = _invoke(app, _FIXTURES / "complete.md")
        assert exit_code == 0, output
        payload = json.loads(output)
        assert payload["valid"] is True
        assert payload["missing_sections"] == []
        # Present-section ordering matches the schema's canonical order.
        assert payload["present_sections"] == [
            "## Summary",
            "## Goals",
            "## Non-Goals",
            "## Decisions",
            "## Risks",
        ]
        assert payload["path"].endswith("complete.md")

    def test_missing_risks_is_invalid(self, app: typer.Typer) -> None:
        """Spec missing ``## Risks`` → valid=false, missing=[``## Risks``], exit 1."""
        exit_code, output = _invoke(app, _FIXTURES / "missing_risks.md")
        assert exit_code == 1, output
        payload = json.loads(output)
        assert payload["valid"] is False
        assert payload["missing_sections"] == ["## Risks"]
        # The four sections that DO exist must appear in present_sections.
        for header in ("## Summary", "## Goals", "## Non-Goals", "## Decisions"):
            assert header in payload["present_sections"]
        assert "## Risks" not in payload["present_sections"]

    def test_missing_optional_sections_still_valid(self, app: typer.Typer) -> None:
        """Optional sections (References / Open Questions) absent → still valid."""
        exit_code, output = _invoke(app, _FIXTURES / "no_optionals.md")
        assert exit_code == 0, output
        payload = json.loads(output)
        assert payload["valid"] is True
        assert payload["missing_sections"] == []
        # The optional headers must NOT appear in present_sections (only the
        # five required headers are tracked there).
        for optional in ("## References", "## Open Questions"):
            assert optional not in payload["present_sections"]

    def test_missing_path_emits_error_envelope(self, app: typer.Typer, tmp_path: Path) -> None:
        """Nonexistent spec path → exit 1, JSON error envelope on stderr."""
        target = tmp_path / "does_not_exist.md"
        exit_code, output = _invoke(app, target)
        assert exit_code == 1
        payload = json.loads(output)
        assert payload["valid"] is False
        assert payload["missing_sections"] == []
        assert payload["present_sections"] == []
        assert "spec file not found" in payload["error"]
        assert payload["path"].endswith("does_not_exist.md")
