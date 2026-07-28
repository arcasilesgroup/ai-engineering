"""The token counter must not present an estimate as a measurement (D-201-19).

``tools/token_baseline/count.py`` falls back to a ``len(text) / 4`` character
heuristic when ``tiktoken`` is absent — which is the DEFAULT, because
``tiktoken`` ships as an optional extra. The header already recorded the
tokenizer, but the VALUES were named ``grand_total_tokens`` / ``per_file_tokens``
and printed as ``grand_total={n} tokens`` regardless, so a roughly 3.6%-wrong
figure read as authoritative.

These tests pin the labelling at the value, and pin that labelling never moves
the number.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

from tools.token_baseline import count as count_mod


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A minimal canonical surface: one skill, one agent, one rulebook file."""
    skill = tmp_path / ".claude" / "skills" / "ai-demo" / "SKILL.md"
    skill.parent.mkdir(parents=True)
    skill.write_text("# demo skill\n" + ("word " * 200), encoding="utf-8")

    agent = tmp_path / ".claude" / "agents" / "ai-demo.md"
    agent.parent.mkdir(parents=True)
    agent.write_text("# demo agent\n" + ("word " * 100), encoding="utf-8")

    (tmp_path / "CLAUDE.md").write_text("# rulebook\n" + ("word " * 50), encoding="utf-8")
    return tmp_path


@pytest.fixture
def no_tiktoken(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``import tiktoken`` fail deterministically, whatever the env holds."""
    monkeypatch.setitem(sys.modules, "tiktoken", None)


def test_heuristic_snapshot_is_labelled_estimated(repo: Path, no_tiktoken: None) -> None:
    """With tiktoken unavailable the numbers are marked as estimates."""
    snapshot = count_mod.build_snapshot(repo)

    assert snapshot["_header"]["tokenizer"] == "char4-heuristic"
    assert snapshot["_header"]["estimated"] is True
    assert snapshot["grand_total_tokens_are_estimated"] is True
    assert snapshot["grand_total_tokens"] > 0


def test_stdout_payload_carries_an_approximation_marker(
    repo: Path, no_tiktoken: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """`--stdout` output marks the total as approximate, not exact."""
    assert count_mod.main(["--repo-root", str(repo), "--stdout"]) == 0
    out = capsys.readouterr().out

    assert "~" in out or "approx" in out.lower()
    payload = json.loads(out)
    assert payload["grand_total_tokens_are_estimated"] is True


def test_summary_line_marks_the_total_as_approximate(
    repo: Path, no_tiktoken: None, capsys: pytest.CaptureFixture[str]
) -> None:
    """The written-snapshot summary marks the total too, not only the JSON."""
    output = repo / "snapshot.json"
    assert count_mod.main(["--repo-root", str(repo), "--output", str(output)]) == 0
    summary = capsys.readouterr().out

    assert "grand_total=~" in summary, summary
    assert "char4-heuristic" in summary


def test_exact_tokenizer_carries_no_approximation_marker(
    repo: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A real BPE count is reported as a measurement, unqualified."""
    monkeypatch.setattr(
        count_mod, "_load_encoder", lambda: ((lambda text: len(text.split())), "cl100k_base")
    )

    snapshot = count_mod.build_snapshot(repo)
    assert snapshot["_header"]["estimated"] is False
    assert snapshot["grand_total_tokens_are_estimated"] is False

    assert count_mod.main(["--repo-root", str(repo), "--stdout"]) == 0
    out = capsys.readouterr().out
    assert "~" not in out
    assert "approx" not in out.lower()


def test_labelling_never_changes_the_number(repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The same encoder yields the same total under either label.

    The label describes the number; it must never be confusable with a change
    to the number itself.
    """

    def counter(text: str) -> int:
        return len(text.split())

    monkeypatch.setattr(count_mod, "_load_encoder", lambda: (counter, "cl100k_base"))
    exact = count_mod.build_snapshot(repo)

    monkeypatch.setattr(count_mod, "_load_encoder", lambda: (counter, "char4-heuristic"))
    estimated = count_mod.build_snapshot(repo)

    assert exact["grand_total_tokens"] == estimated["grand_total_tokens"]
    assert exact["per_file_tokens"] == estimated["per_file_tokens"]
    assert exact["grand_total_tokens_are_estimated"] is False
    assert estimated["grand_total_tokens_are_estimated"] is True


def test_the_optional_extra_is_declared_and_stays_out_of_core() -> None:
    """`tiktoken` is an opt-in extra — never a core dependency (D-201-19)."""
    import tomllib

    repo_root = Path(__file__).resolve().parents[3]
    with (repo_root / "pyproject.toml").open("rb") as handle:
        data = tomllib.load(handle)

    core = " ".join(data["project"]["dependencies"])
    assert "tiktoken" not in core

    extra = data["project"]["optional-dependencies"]["tokens"]
    assert any("tiktoken" in requirement for requirement in extra), extra
