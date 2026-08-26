"""Tests for spec 030 / B-030-1: the cold-read verifier.

A reviewer that reads only the spec (or answer key) and the delivered files — never the
constructor's conversation, never the plan's rationale — and has no write tools. Its rules:
"an uncertain check is a fail"; it reports what it saw, not what the builder said. A
verifier with write access or the constructor's reasoning is refused by the framework.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_engineering import verify_cold  # noqa: E402
from ai_engineering.verify_cold import Verdict  # noqa: E402


def _key(tmp_path: Path, *, unknown: bool = False) -> Path:
    key = tmp_path / "answer-key.yaml"
    checks = (
        '[[checks]]\nid = "c1"\nstatement = "the file exists"\njudged_by = "run it"\n'
        'command = "test -f src/app.py"\n'
    )
    unknown_block = 'unknowns = ["U1"]\n' if unknown else ""
    key.write_text(
        'schema = "urn:ai-engineering:answer-key:1"\nschema_version = "1"\nspec = "010"\n'
        f'spec_digest = "sha256:{"0" * 64}"\n{unknown_block}{checks}',
        encoding="utf-8",
    )
    return key


def test_a_cold_read_verifier_applies_the_key_read_only(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    verdict = verify_cold.verify(tmp_path, _key(tmp_path))
    assert verdict == Verdict.PASS


def test_an_uncertain_check_is_a_fail(tmp_path):
    """The key's run-it check fails on the delivered tree → FAIL, not a guess."""
    verdict = verify_cold.verify(tmp_path, _key(tmp_path))  # no src/ tree
    assert verdict == Verdict.FAIL


def test_an_unknown_observable_blocks_never_scores(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "app.py").write_text("x = 1\n", encoding="utf-8")
    verdict = verify_cold.verify(tmp_path, _key(tmp_path, unknown=True))
    assert verdict == Verdict.BLOCKED


def test_a_verifier_with_write_access_is_refused():
    """The cold-read contract: the runner must never open files for writing."""
    with pytest.raises(ValueError, match="read-only"):
        verify_cold.verify(ROOT, _key(ROOT), allow_write=True)


def test_a_verifier_with_the_constructors_reasoning_is_refused():
    """The cold-read contract: the constructor's reasoning must never reach the verifier."""
    with pytest.raises(ValueError, match="constructors reasoning"):
        verify_cold.verify(ROOT, _key(ROOT), constructor_reasoning="the fix is correct")
