"""A write outside the claim is denied.

Specification 013: `claimed_paths` is enforced on every write and every commit, and again
by CI over the pushed diff. This file is the first half — the guard on the machine doing
the writing. The CI half reads the claim held on the remote and is not here yet, so
EP-188 is not closed by this file alone and nothing in it says otherwise.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hooks"))


@pytest.fixture
def claimed(tmp_path):
    """A repository with one claim in force, over one file and one directory."""
    root = tmp_path / "repository"
    (root / ".ai").mkdir(parents=True)
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / ".ai" / "claim.json").write_text(
        json.dumps({"item": "work-42", "paths": ["src/thing.py", "docs/"]}), encoding="utf-8"
    )
    return root


def test_a_write_inside_the_claim_is_allowed(claimed):
    import claim_scope_guard

    assert claim_scope_guard.decide(claimed, str(claimed / "src" / "thing.py")) is None
    assert claim_scope_guard.decide(claimed, str(claimed / "docs" / "any.md")) is None


def test_a_write_outside_the_claim_is_denied_and_says_what_was_claimed(claimed):
    """The refusal names the item and the paths, because the person reading it is deciding
    whether to widen the claim or take a different task — and neither is possible from the
    word "denied"."""
    import claim_scope_guard

    reason = claim_scope_guard.decide(claimed, str(claimed / "src" / "other.py"))
    assert reason is not None
    assert "work-42" in reason and "src/thing.py" in reason


def test_a_claim_that_cannot_be_read_denies_rather_than_disappears(claimed):
    """Fail closed. A corrupt claim file is not the absence of a claim: somebody else may
    hold this work, and the one thing that must not happen is writing anyway."""
    import claim_scope_guard

    (claimed / ".ai" / "claim.json").write_text("{not json", encoding="utf-8")
    reason = claim_scope_guard.decide(claimed, str(claimed / "src" / "thing.py"))
    assert reason is not None and "could not be read" in reason


def test_no_claim_in_force_is_not_a_denial(tmp_path):
    """The single-writer case, which is every repository that has never coordinated. This
    guard governs writes while a claim is held; it does not invent one."""
    import claim_scope_guard

    root = tmp_path / "plain"
    (root / "src").mkdir(parents=True)
    assert claim_scope_guard.decide(root, str(root / "src" / "anything.py")) is None


def test_a_path_outside_the_repository_is_denied_while_a_claim_is_held(claimed):
    """A claim is about this repository. A write somewhere else while holding one is not a
    scope question this guard can answer, and answering it as allowed is the fail-open
    direction."""
    import claim_scope_guard

    assert claim_scope_guard.decide(claimed, str(claimed.parent / "elsewhere.txt")) is not None


def test_a_claimed_path_cannot_be_escaped_with_a_traversal(claimed):
    """`src/thing.py/../../etc/passwd` resolves outside the claim, and a check that compared
    the string it was handed would have allowed it."""
    import claim_scope_guard

    escape = str(claimed / "src" / "thing.py" / ".." / ".." / "elsewhere.py")
    assert claim_scope_guard.decide(claimed, escape) is not None


def test_the_denial_stops_the_call(claimed, monkeypatch):
    """End to end through the decorator: a denied write exits non-zero rather than
    returning a string somebody has to remember to read."""
    import claim_scope_guard

    monkeypatch.setattr(claim_scope_guard, "repo_root", lambda: claimed)
    with pytest.raises(SystemExit) as stopped:
        claim_scope_guard.run(
            {"tool_name": "Write", "tool_input": {"file_path": str(claimed / "src" / "other.py")}}
        )
    assert stopped.value.code != 0


def test_the_guard_is_registered_and_classified():
    """A hook that is not in the dispatcher table does not exist, and a hook on a blocking
    event that is not a guard is the contract this repository will not bend."""
    import chain
    import claim_scope_guard

    registered = {name for name, _ in chain.TABLE["PreToolUse"]}
    assert "claim_scope_guard" in registered
    assert claim_scope_guard.run.hook_class == "guard"
    assert "claim_scope_guard" not in chain.TELEMETRY
