"""RED-phase integration tests for `cleanup_run.py` (spec-129 T-9).

These tests intentionally fail with `ImportError` / `ModuleNotFoundError`
until T-10 lands the GREEN implementation under
`.ai-engineering/scripts/skills/skill_scripts/cleanup_run.py`.

The fixture pattern uses a real throwaway repo via `git init` inside
`tmp_path` (no mocks, no host-repo mutation). The module under test is
expected to expose:

  - `classify_branches(repo_path: Path, protected: list[str]) -> dict[str, Classification]`
  - `run_cleanup(repo_path: Path, protected: list[str], apply: bool) -> dict`
  - `Classification` typed record (or `Enum` mapping branch -> category)

Categories asserted by these tests (spec-129 §14.2 cleanup_run):
  - "merged-into-main"      — feature branch merged via FF or merge commit
  - "squash-merged"         — subject appears in main's history (90-day window)
  - "stale-no-commits-30d"  — no commits in 30+ days, not merged
  - "protected"             — in the caller-supplied protected list
  - "active"                — recent commits, not merged

Conservative defaults are required:
  - `--dry-run` NEVER deletes; returns JSON plan.
  - `--apply` deletes ONLY `merged-into-main` and `squash-merged`.
  - `stale-no-commits-30d` requires manual confirmation (skipped here).
  - `protected` is always preserved, even if technically merged.

Tests live under `tests/integration/scripts/` mirroring spec-129's plan
Phase 1 layout. The host repo's git state MUST NEVER be touched — every
test scopes its actions to a `tmp_path` repo (see boundary constraints
in spec-129 T-9 task brief).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

# RED-phase import: the module does not yet exist. Module collection itself
# fails fast — every test surfaces as ImportError/ModuleNotFoundError until
# T-10 lands.
from skill_scripts.cleanup_run import (  # noqa: F401
    Classification,
    classify_branches,
    run_cleanup,
)

# ---------------------------------------------------------------------------
# Fixtures — real git repo under tmp_path, never the host repo
# ---------------------------------------------------------------------------


@pytest.fixture
def repo_with_branches(tmp_path: Path) -> Path:
    """Initialise an empty git repo with a `main` branch and identity set.

    The caller seeds branches via the `_commit`, `_branch`, `_merge_ff`,
    `_merge_no_ff`, `_squash_merge`, and `_aged_commit` helpers below.
    Keeping seeding out of the fixture lets each test express exactly the
    history it depends on, which keeps failures localized.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    # Force a stable default branch name across user-level git config that may
    # set `init.defaultBranch` to something other than `main`.
    subprocess.run(
        ["git", "symbolic-ref", "HEAD", "refs/heads/main"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    return repo


def _commit(repo: Path, filename: str, message: str, *, when: str | None = None) -> str:
    """Create a commit; optionally backdate it with `GIT_*_DATE` env vars."""
    (repo / filename).write_text(f"content for {filename}\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", filename],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    env = os.environ.copy()
    if when is not None:
        env["GIT_AUTHOR_DATE"] = when
        env["GIT_COMMITTER_DATE"] = when
    subprocess.run(
        ["git", "commit", "-m", message],
        cwd=repo,
        check=True,
        capture_output=True,
        env=env,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _branch(repo: Path, name: str) -> None:
    """Create and switch to a new branch off the current HEAD."""
    subprocess.run(
        ["git", "checkout", "-b", name],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _checkout(repo: Path, name: str) -> None:
    """Switch to an existing branch."""
    subprocess.run(
        ["git", "checkout", name],
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _merge_no_ff(repo: Path, branch: str, message: str) -> str:
    """Non-fast-forward merge `branch` into the current branch."""
    subprocess.run(
        ["git", "merge", "--no-ff", "-m", message, branch],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _squash_merge_subject(repo: Path, branch: str, subject: str) -> str:
    """Simulate a squash-merge by committing `subject` directly onto current branch.

    Real squash merges leave a single commit whose subject typically mirrors
    the source branch's tip subject. We reproduce that signature so the
    classifier's "subject-in-main-history" heuristic has a positive match
    without depending on `git merge --squash` semantics (which require a
    follow-up `git commit` anyway).
    """
    placeholder = repo / f"_squash_{branch.replace('/', '_')}.txt"
    placeholder.write_text(f"squash for {branch}\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", placeholder.name],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", subject],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _list_branches(repo: Path) -> list[str]:
    """Return all local branch names."""
    result = subprocess.run(
        ["git", "for-each-ref", "--format=%(refname:short)", "refs/heads/"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


# ---------------------------------------------------------------------------
# 1. Classification — merged-into-main
# ---------------------------------------------------------------------------


def test_classify_merged_via_no_ff_merge(repo_with_branches: Path) -> None:
    """Branch merged via `git merge --no-ff` is classified `merged-into-main`."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/x")
    _commit(repo_with_branches, "x.txt", "feat: x")
    _checkout(repo_with_branches, "main")
    _merge_no_ff(repo_with_branches, "feature/x", "Merge branch 'feature/x'")
    result = classify_branches(repo_with_branches, protected=["main"])
    assert "feature/x" in result
    assert result["feature/x"] == "merged-into-main"


def test_classify_merged_via_fast_forward(repo_with_branches: Path) -> None:
    """A branch whose tip is reachable from main is `merged-into-main`."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/ff")
    feature_sha = _commit(repo_with_branches, "ff.txt", "feat: ff")
    _checkout(repo_with_branches, "main")
    # Fast-forward main to the feature tip.
    subprocess.run(
        ["git", "merge", "--ff-only", "feature/ff"],
        cwd=repo_with_branches,
        check=True,
        capture_output=True,
    )
    result = classify_branches(repo_with_branches, protected=["main"])
    assert result["feature/ff"] == "merged-into-main"
    # Sanity: main now points at the feature sha.
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_with_branches,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert head == feature_sha


# ---------------------------------------------------------------------------
# 2. Classification — squash-merged (subject-in-main-history heuristic)
# ---------------------------------------------------------------------------


def test_classify_squash_merged_by_subject_match(repo_with_branches: Path) -> None:
    """Branch tip subject appears in main's history -> `squash-merged`."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/squash")
    _commit(repo_with_branches, "squash.txt", "feat: shared subject line")
    _checkout(repo_with_branches, "main")
    # Simulate the squash merge: a commit on main with the same subject.
    _squash_merge_subject(
        repo_with_branches,
        "feature/squash",
        "feat: shared subject line",
    )
    result = classify_branches(repo_with_branches, protected=["main"])
    assert result["feature/squash"] == "squash-merged"


def test_classify_squash_merged_only_within_90_day_window(
    repo_with_branches: Path,
) -> None:
    """A subject match older than 90 days is NOT classified `squash-merged`.

    Prevents stale subject collisions across long-lived repos from
    being mistaken for recent squash merges.
    """
    long_ago = (datetime.now(UTC) - timedelta(days=120)).isoformat()
    _commit(repo_with_branches, "seed.txt", "feat: seed", when=long_ago)
    _commit(
        repo_with_branches,
        "old.txt",
        "feat: ancient subject",
        when=long_ago,
    )
    _branch(repo_with_branches, "feature/ancient")
    # Branch tip mirrors the ancient subject — but the corresponding main
    # commit is outside the 90-day window, so classifier must NOT mark it
    # as squash-merged. With no recent commits on the branch either, it
    # should be `stale-no-commits-30d`.
    _commit(
        repo_with_branches,
        "ancient.txt",
        "feat: ancient subject",
        when=long_ago,
    )
    _checkout(repo_with_branches, "main")
    result = classify_branches(repo_with_branches, protected=["main"])
    assert result["feature/ancient"] != "squash-merged"


# ---------------------------------------------------------------------------
# 3. Classification — stale-no-commits-30d
# ---------------------------------------------------------------------------


def test_classify_stale_branch_no_commits_30_days(repo_with_branches: Path) -> None:
    """Branch with no commits in 30+ days, not merged -> stale-no-commits-30d."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/stale")
    old_date = (datetime.now(UTC) - timedelta(days=45)).isoformat()
    _commit(repo_with_branches, "stale.txt", "feat: stale work", when=old_date)
    _checkout(repo_with_branches, "main")
    # Add an unrelated recent commit on main so the branch is genuinely
    # unmerged (no FF reachability, no squash subject collision).
    _commit(repo_with_branches, "fresh.txt", "feat: fresh main work")
    result = classify_branches(repo_with_branches, protected=["main"])
    assert result["feature/stale"] == "stale-no-commits-30d"


# ---------------------------------------------------------------------------
# 4. Classification — protected
# ---------------------------------------------------------------------------


def test_classify_protected_branches_marked(repo_with_branches: Path) -> None:
    """Branch in the `protected` list is classified `protected`."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "master")
    _checkout(repo_with_branches, "main")
    result = classify_branches(repo_with_branches, protected=["main", "master"])
    assert result["main"] == "protected"
    assert result["master"] == "protected"


def test_classify_protected_overrides_merged_classification(
    repo_with_branches: Path,
) -> None:
    """A protected branch is `protected` even if technically merged.

    Guards against `--apply` accidentally deleting an organisation-protected
    long-lived branch whose tip happens to be reachable from main.
    """
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "release/v1")
    _checkout(repo_with_branches, "main")
    # Fast-forward main onto the release branch tip.
    subprocess.run(
        ["git", "merge", "--ff-only", "release/v1"],
        cwd=repo_with_branches,
        check=True,
        capture_output=True,
    )
    result = classify_branches(
        repo_with_branches,
        protected=["main", "release/v1"],
    )
    assert result["release/v1"] == "protected"


# ---------------------------------------------------------------------------
# 5. Classification — active
# ---------------------------------------------------------------------------


def test_classify_active_branch_recent_unmerged(repo_with_branches: Path) -> None:
    """Branch with recent commits, not merged, no subject collision -> active."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/active")
    _commit(repo_with_branches, "active.txt", "feat: active work")
    _checkout(repo_with_branches, "main")
    _commit(repo_with_branches, "diverge.txt", "feat: diverged main")
    result = classify_branches(repo_with_branches, protected=["main"])
    assert result["feature/active"] == "active"


# ---------------------------------------------------------------------------
# 6. Dry-run mode — reports only, no deletion
# ---------------------------------------------------------------------------


def test_dry_run_reports_classifications_without_deleting(
    repo_with_branches: Path,
) -> None:
    """`--dry-run` returns the classification plan and deletes nothing."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/merged")
    _commit(repo_with_branches, "m.txt", "feat: m")
    _checkout(repo_with_branches, "main")
    _merge_no_ff(repo_with_branches, "feature/merged", "Merge branch 'feature/merged'")
    branches_before = set(_list_branches(repo_with_branches))
    plan = run_cleanup(repo_with_branches, protected=["main"], apply=False)
    branches_after = set(_list_branches(repo_with_branches))
    # No mutations occurred.
    assert branches_before == branches_after
    # Plan is a dict-like report with the safe-to-delete list.
    assert isinstance(plan, dict)
    safe = plan.get("safe_to_delete", plan.get("delete", []))
    assert "feature/merged" in safe


def test_dry_run_safe_list_is_json_serializable(repo_with_branches: Path) -> None:
    """The dry-run plan must round-trip through `json.dumps` for CLI emission."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/json")
    _commit(repo_with_branches, "j.txt", "feat: j")
    _checkout(repo_with_branches, "main")
    _merge_no_ff(repo_with_branches, "feature/json", "Merge branch 'feature/json'")
    plan = run_cleanup(repo_with_branches, protected=["main"], apply=False)
    # If a non-serializable value sneaks in (Path, datetime, set, …) this
    # raises TypeError — and the test must fail with a clear message.
    serialised = json.dumps(plan)
    assert "feature/json" in serialised


# ---------------------------------------------------------------------------
# 7. Apply mode — deletes only merged/squash-merged
# ---------------------------------------------------------------------------


def test_apply_deletes_merged_branches(repo_with_branches: Path) -> None:
    """`apply=True` deletes branches classified `merged-into-main`."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/del")
    _commit(repo_with_branches, "d.txt", "feat: d")
    _checkout(repo_with_branches, "main")
    _merge_no_ff(repo_with_branches, "feature/del", "Merge branch 'feature/del'")
    assert "feature/del" in _list_branches(repo_with_branches)
    run_cleanup(repo_with_branches, protected=["main"], apply=True)
    assert "feature/del" not in _list_branches(repo_with_branches)
    # main always survives.
    assert "main" in _list_branches(repo_with_branches)


def test_apply_deletes_squash_merged_branches(repo_with_branches: Path) -> None:
    """`apply=True` deletes branches classified `squash-merged`."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/sq")
    _commit(repo_with_branches, "sq.txt", "feat: squash subject")
    _checkout(repo_with_branches, "main")
    _squash_merge_subject(repo_with_branches, "feature/sq", "feat: squash subject")
    assert "feature/sq" in _list_branches(repo_with_branches)
    run_cleanup(repo_with_branches, protected=["main"], apply=True)
    assert "feature/sq" not in _list_branches(repo_with_branches)


def test_apply_preserves_stale_branches(repo_with_branches: Path) -> None:
    """Stale branches require manual confirmation — `apply=True` must skip them."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/stale")
    old = (datetime.now(UTC) - timedelta(days=60)).isoformat()
    _commit(repo_with_branches, "s.txt", "feat: old work", when=old)
    _checkout(repo_with_branches, "main")
    _commit(repo_with_branches, "newer.txt", "feat: newer main work")
    run_cleanup(repo_with_branches, protected=["main"], apply=True)
    # The stale branch must still exist — out-of-scope for automatic delete.
    assert "feature/stale" in _list_branches(repo_with_branches)


def test_apply_preserves_protected_branches(repo_with_branches: Path) -> None:
    """Even if a protected branch is technically merged, `apply` must not touch it."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "release/v1")
    _checkout(repo_with_branches, "main")
    subprocess.run(
        ["git", "merge", "--ff-only", "release/v1"],
        cwd=repo_with_branches,
        check=True,
        capture_output=True,
    )
    run_cleanup(
        repo_with_branches,
        protected=["main", "release/v1"],
        apply=True,
    )
    assert "release/v1" in _list_branches(repo_with_branches)


def test_apply_preserves_active_branches(repo_with_branches: Path) -> None:
    """Active (unmerged, recent) branches survive `apply=True`."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/active")
    _commit(repo_with_branches, "a.txt", "feat: a")
    _checkout(repo_with_branches, "main")
    _commit(repo_with_branches, "m.txt", "feat: m")
    run_cleanup(repo_with_branches, protected=["main"], apply=True)
    assert "feature/active" in _list_branches(repo_with_branches)


# ---------------------------------------------------------------------------
# 8. Idempotency — running --apply twice yields same end state
# ---------------------------------------------------------------------------


def test_apply_is_idempotent(repo_with_branches: Path) -> None:
    """A second `apply` after the first is a no-op and does not raise."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    _branch(repo_with_branches, "feature/idem")
    _commit(repo_with_branches, "i.txt", "feat: i")
    _checkout(repo_with_branches, "main")
    _merge_no_ff(repo_with_branches, "feature/idem", "Merge branch 'feature/idem'")
    run_cleanup(repo_with_branches, protected=["main"], apply=True)
    state_after_first = sorted(_list_branches(repo_with_branches))
    # Second run must complete cleanly even though the merged branch is gone.
    run_cleanup(repo_with_branches, protected=["main"], apply=True)
    state_after_second = sorted(_list_branches(repo_with_branches))
    assert state_after_first == state_after_second


# ---------------------------------------------------------------------------
# 9. Performance smoke — 10 branches classified under 500 ms
# ---------------------------------------------------------------------------


def test_classification_of_10_branches_under_500ms_p95(
    repo_with_branches: Path,
) -> None:
    """Classifying a 10-branch repo must finish well within the hot-path budget."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    for i in range(10):
        _branch(repo_with_branches, f"feature/perf-{i}")
        _commit(repo_with_branches, f"perf{i}.txt", f"feat: perf {i}")
        _checkout(repo_with_branches, "main")
    # Three trials; assert the p95 (worst of three is a conservative proxy).
    durations: list[float] = []
    for _ in range(3):
        start = time.monotonic()
        result = classify_branches(repo_with_branches, protected=["main"])
        durations.append(time.monotonic() - start)
        assert len(result) >= 11  # main + 10 features
    worst = max(durations)
    assert worst < 0.5, (
        f"classify_branches(10 branches) p95 ~ {worst * 1000:.1f}ms "
        f"(budget 500ms) — regression on the hot path"
    )


# ---------------------------------------------------------------------------
# 10. Edge case — empty repo (only main, no other branches)
# ---------------------------------------------------------------------------


def test_empty_repo_returns_no_safe_delete_list(repo_with_branches: Path) -> None:
    """Repo with only the protected default branch yields an empty delete plan."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    plan = run_cleanup(repo_with_branches, protected=["main"], apply=False)
    safe = plan.get("safe_to_delete", plan.get("delete", []))
    assert safe == []


def test_empty_repo_classification_only_contains_protected_main(
    repo_with_branches: Path,
) -> None:
    """Classification of a single-branch repo lists only `main` -> protected."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    result = classify_branches(repo_with_branches, protected=["main"])
    assert set(result.keys()) == {"main"}
    assert result["main"] == "protected"


def test_apply_on_empty_repo_does_not_crash(repo_with_branches: Path) -> None:
    """`apply=True` on a single-branch repo is a clean no-op."""
    _commit(repo_with_branches, "seed.txt", "feat: seed")
    run_cleanup(repo_with_branches, protected=["main"], apply=True)
    assert "main" in _list_branches(repo_with_branches)


# Silence unused-import warning for `sys` (kept for future diagnostic needs
# without forcing a re-edit during GREEN).
_ = sys
