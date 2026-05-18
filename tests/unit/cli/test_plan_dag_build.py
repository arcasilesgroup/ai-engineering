"""Unit tests for ``ai-eng plan dag-build`` (spec-139 M7.T2).

The command walks ``<subdir>/sub-*/plan.md``, parses each plan's
``exports:`` and ``imports:`` frontmatter lists, builds the DAG of
sub-spec dependencies, and runs a topological sort to assign waves
(wave 0 = no deps; wave 1 = depends only on wave 0; etc.).

Exit codes:
- 0 when the DAG resolves cleanly (``conflicts=[]``).
- 1 when conflicts (cycles or unresolvable imports) are present.

Output is JSON: ``{"waves": [["sub-001", "sub-002"], ...], "conflicts": [...]}``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

_FIXTURES = Path(__file__).parent / "fixtures" / "plan_dag"


@pytest.fixture()
def app() -> typer.Typer:
    from ai_engineering.cli_factory import create_app

    return create_app()


def _invoke(app: typer.Typer, subdir: Path) -> tuple[int, str]:
    """Invoke ``plan dag-build <subdir>`` and return (exit, combined_output).

    Older Typer (0.21.x) does not support ``mix_stderr=False``; stdout and
    stderr collapse into ``result.output``. The command emits exactly one
    JSON document either way, so a single ``json.loads`` covers both the
    happy path and the missing-subdir error envelope.
    """
    runner = CliRunner()
    result = runner.invoke(app, ["plan", "dag-build", str(subdir)])
    return result.exit_code, result.output


class TestPlanDagBuild:
    def test_no_imports_all_in_wave_zero(self, app: typer.Typer) -> None:
        """Plans with no imports → every sub-spec lands in wave 0."""
        exit_code, output = _invoke(app, _FIXTURES / "all_independent")
        assert exit_code == 0, output
        payload = json.loads(output)
        assert payload["conflicts"] == []
        assert len(payload["waves"]) == 1
        assert sorted(payload["waves"][0]) == ["sub-001", "sub-002", "sub-003"]

    def test_linear_dependency_chain_one_per_wave(self, app: typer.Typer) -> None:
        """sub-001 → sub-002 → sub-003 produces three single-element waves."""
        exit_code, output = _invoke(app, _FIXTURES / "linear_chain")
        assert exit_code == 0, output
        payload = json.loads(output)
        assert payload["conflicts"] == []
        assert payload["waves"] == [["sub-001"], ["sub-002"], ["sub-003"]]

    def test_no_overlap_all_in_wave_zero(self, app: typer.Typer) -> None:
        """Plans that export distinct tokens with no imports → all in wave 0."""
        exit_code, output = _invoke(app, _FIXTURES / "no_overlap")
        assert exit_code == 0, output
        payload = json.loads(output)
        assert payload["conflicts"] == []
        # All three sub-specs land in a single first wave because none of
        # them import anything from a sibling.
        assert len(payload["waves"]) == 1
        assert sorted(payload["waves"][0]) == ["sub-001", "sub-002", "sub-003"]

    def test_cycle_emits_conflict_and_exits_nonzero(self, app: typer.Typer) -> None:
        """sub-001 ↔ sub-002 cycle → conflicts non-empty, exit 1, waves empty."""
        exit_code, output = _invoke(app, _FIXTURES / "cycle")
        assert exit_code == 1, output
        payload = json.loads(output)
        assert payload["waves"] == []
        assert payload["conflicts"]
        # Cycle message must name both participants so an operator can
        # locate the offending plans without a second tool invocation.
        cycle_blob = " ".join(payload["conflicts"])
        assert "cycle" in cycle_blob.lower()
        assert "sub-001" in cycle_blob
        assert "sub-002" in cycle_blob

    def test_unresolvable_import_emits_conflict(self, app: typer.Typer, tmp_path: Path) -> None:
        """Importing a token nobody exports → conflict, exit 1."""
        sub_dir = tmp_path / "sub-001"
        sub_dir.mkdir()
        (sub_dir / "plan.md").write_text(
            "---\nspec: sub-001\nexports: []\nimports: [phantom]\n---\n",
            encoding="utf-8",
        )
        exit_code, output = _invoke(app, tmp_path)
        assert exit_code == 1, output
        payload = json.loads(output)
        assert payload["conflicts"]
        assert any("phantom" in msg for msg in payload["conflicts"])
