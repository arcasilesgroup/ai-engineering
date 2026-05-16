"""Branch cleanup classifier and pruner (spec-129 T-10).

GREEN-phase implementation backing the contract pinned in
``tests/integration/scripts/test_cleanup_run.py`` (T-9). The module
classifies every local branch in a repository into one of five
mutually-exclusive categories and, in ``--apply`` mode, deletes the
subset known to be safe.

## Contract overview

* ``Classification`` — typed record exposing ``branch``, ``category``,
  ``confidence``, and ``safe_to_delete``. Implemented as a ``str``
  subclass whose string identity equals the ``category`` token; this
  lets callers write ``result[branch] == "merged-into-main"`` while
  still attaching the structured fields the JSON plan needs.
* ``classify_branches(repo_path, protected, main_branch="main")`` —
  inspects every local branch and returns ``{branch: Classification}``.
* ``run_cleanup(repo_path, protected, apply)`` — wraps
  ``classify_branches`` and (when ``apply=True``) deletes branches
  whose category is in the auto-delete set. Returns a JSON-serialisable
  dict with the keys ``deleted``, ``skipped``, ``safe_to_delete``,
  ``classifications``, ``protected``, ``main_branch``.
* ``main(argv)`` — argparse-driven CLI. ``--dry-run`` (default) prints
  the plan; ``--apply`` executes deletion. ``--protect`` accepts a
  comma-separated list (default ``main,master``).

## Categories (mutually exclusive, evaluated in priority order)

1. ``protected`` — branch name appears in the caller's protected list.
   Wins unconditionally so org-protected long-lived branches never enter
   the delete plan, even if technically merged.
2. ``merged-into-main`` — ``git merge-base --is-ancestor <branch>
   <main>`` exits ``0``. Covers both no-ff merges and fast-forwards.
3. ``squash-merged`` — branch tip subject appears in main's history
   within the last 90 days. Bounded window prevents stale subject
   collisions on long-lived repos from being mistaken for fresh
   squash merges.
4. ``stale-no-commits-30d`` — branch's most recent commit is older
   than 30 days **and** the branch is unmerged.
5. ``active`` — everything else: recent, unmerged, no subject match.

## Safety posture

* ``safe_to_delete`` is ``True`` **only** for ``merged-into-main`` and
  ``squash-merged``. Stale, protected, and active branches always
  require manual confirmation (out of scope for this script).
* ``--apply`` deletes with ``git branch -D`` and ``check=False`` so a
  second invocation on an already-pruned repo is a clean no-op (the
  ``not found`` stderr from git is captured and discarded).
* The script never touches the host repo's git state — every
  subprocess call accepts an explicit ``cwd=repo_path``.

## Performance

The 10-branch budget (500 ms p95) is honoured by a single ``for-each-
ref`` listing plus one ``merge-base --is-ancestor`` per branch and at
most one ``git log --since`` over main's 90-day history (subject
membership is computed once and reused across branches).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

__all__ = ["Classification", "classify_branches", "main", "run_cleanup"]

# Categories that ``--apply`` is allowed to delete automatically. Every
# other category requires manual confirmation, including ``stale`` —
# stale branches sometimes carry work-in-progress that the developer
# wants to revisit, so we leave that decision to a human.
_AUTO_DELETE_CATEGORIES: frozenset[str] = frozenset({"merged-into-main", "squash-merged"})

# Subject-match window for the squash-merge heuristic. A 90-day window
# is wide enough to catch the long tail of feature-branch lifetimes
# while narrow enough that stale subject collisions on long-lived repos
# do not silently re-categorise unrelated branches as "merged".
_SQUASH_LOOKBACK_DAYS = 90

# Staleness threshold; aligned with the test fixture's 45-day backdating
# and the 30-day boundary documented in spec-129 §14.2.
_STALE_DAYS = 30

Category = Literal[
    "merged-into-main",
    "squash-merged",
    "stale-no-commits-30d",
    "protected",
    "active",
]

Confidence = Literal["high", "medium", "low"]


class Classification(str):
    """Branch classification record.

    The class extends ``str`` so a ``dict`` of classifications round-
    trips through ``json.dumps`` (each value serialises as its category
    token) and so test assertions of the form
    ``result[branch] == "merged-into-main"`` evaluate naturally. The
    structured fields (``branch``, ``category``, ``confidence``,
    ``safe_to_delete``) remain available as attributes for callers that
    need the richer payload — e.g. the dry-run JSON plan.
    """

    branch: str
    category: Category
    confidence: Confidence
    safe_to_delete: bool

    def __new__(
        cls,
        *,
        branch: str,
        category: Category,
        confidence: Confidence,
        safe_to_delete: bool,
    ) -> Classification:
        instance = super().__new__(cls, category)
        instance.branch = branch
        instance.category = category
        instance.confidence = confidence
        instance.safe_to_delete = safe_to_delete
        return instance

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serialisable view of the classification."""
        return {
            "branch": self.branch,
            "category": self.category,
            "confidence": self.confidence,
            "safe_to_delete": self.safe_to_delete,
        }


@dataclass(frozen=True)
class _BranchInfo:
    """Internal record bundling the per-branch facts we need."""

    name: str
    tip_subject: str
    tip_unix: int


def _run_git(
    args: list[str],
    repo_path: Path,
    *,
    check: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a ``git`` subprocess scoped to ``repo_path``.

    ``check=False`` by default so callers can inspect non-zero exits
    (empty repo, missing ref, ``is-ancestor`` returning ``1``) without
    catching ``CalledProcessError`` at every site.
    """
    return subprocess.run(
        ["git", *args],
        cwd=repo_path,
        check=check,
        capture_output=True,
        text=True,
    )


def _list_branches(repo_path: Path) -> list[_BranchInfo]:
    """Return one ``_BranchInfo`` per local branch in ``repo_path``.

    Uses ``for-each-ref`` with a single format string so we capture
    name, subject, and commit timestamp in one git invocation rather
    than ``len(branches)`` separate ``git log`` calls. The ASCII unit
    separator (``\\x1f``) is safe because it never appears in commit
    subjects or branch names.
    """
    sep = "\x1f"
    fmt = sep.join(["%(refname:short)", "%(contents:subject)", "%(committerdate:unix)"])
    result = _run_git(
        ["for-each-ref", f"--format={fmt}", "refs/heads/"],
        repo_path,
    )
    if result.returncode != 0:
        return []
    branches: list[_BranchInfo] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        parts = line.split(sep)
        while len(parts) < 3:
            parts.append("")
        name, subject, unix_str = parts[0], parts[1], parts[2]
        try:
            unix_ts = int(unix_str) if unix_str else 0
        except ValueError:
            unix_ts = 0
        branches.append(_BranchInfo(name=name, tip_subject=subject, tip_unix=unix_ts))
    return branches


def _main_exists(repo_path: Path, main_branch: str) -> bool:
    """Whether ``main_branch`` resolves to a commit in ``repo_path``.

    A freshly-initialised repo has the symbolic ref ``HEAD`` pointing
    at ``refs/heads/main`` but no commit attached — ``rev-parse`` then
    exits non-zero. Distinguishing this from the "real" main lets us
    short-circuit reachability and squash checks instead of letting
    ``git merge-base`` emit spurious errors.
    """
    result = _run_git(["rev-parse", "--verify", main_branch], repo_path)
    return result.returncode == 0


def _is_ancestor(
    repo_path: Path,
    branch: str,
    main_branch: str,
) -> bool:
    """Whether every commit reachable from ``branch`` is reachable from main.

    Equivalent to "branch has been merged into main" — fast-forward or
    no-ff merges both leave the branch tip as an ancestor of main.
    """
    result = _run_git(
        ["merge-base", "--is-ancestor", branch, main_branch],
        repo_path,
    )
    return result.returncode == 0


def _recent_main_subjects(
    repo_path: Path,
    main_branch: str,
    lookback_days: int,
) -> set[str]:
    """Return the set of subjects on ``main_branch`` within the lookback window.

    The set is computed once per ``classify_branches`` call and reused
    for every branch's squash-merge check, keeping the cost on the hot
    path bounded by a single ``git log`` invocation.
    """
    cutoff = (datetime.now(UTC) - timedelta(days=lookback_days)).isoformat()
    result = _run_git(
        [
            "log",
            main_branch,
            "--format=%s",
            f"--since={cutoff}",
        ],
        repo_path,
    )
    if result.returncode != 0:
        return set()
    return {line for line in result.stdout.splitlines() if line}


def _classify_one(
    branch: _BranchInfo,
    *,
    repo_path: Path,
    main_branch: str,
    main_present: bool,
    protected_set: frozenset[str],
    main_subjects: set[str],
    now_unix: int,
) -> Classification:
    """Classify a single branch using the priority ladder.

    The ladder is documented in the module docstring; this function
    mirrors it exactly so a regression in test expectations maps to a
    single conditional rather than scattered logic.
    """
    if branch.name in protected_set:
        return Classification(
            branch=branch.name,
            category="protected",
            confidence="high",
            safe_to_delete=False,
        )

    if main_present and branch.name != main_branch:
        if _is_ancestor(repo_path, branch.name, main_branch):
            return Classification(
                branch=branch.name,
                category="merged-into-main",
                confidence="high",
                safe_to_delete=True,
            )
        if branch.tip_subject and branch.tip_subject in main_subjects:
            return Classification(
                branch=branch.name,
                category="squash-merged",
                confidence="medium",
                safe_to_delete=True,
            )

    age_days = max(now_unix - branch.tip_unix, 0) // 86400
    if age_days > _STALE_DAYS:
        return Classification(
            branch=branch.name,
            category="stale-no-commits-30d",
            confidence="medium",
            safe_to_delete=False,
        )

    return Classification(
        branch=branch.name,
        category="active",
        confidence="medium",
        safe_to_delete=False,
    )


def classify_branches(
    repo_path: Path,
    protected: list[str],
    main_branch: str = "main",
) -> dict[str, Classification]:
    """Classify every local branch in ``repo_path``.

    Args:
        repo_path: Filesystem path to a git working tree. Must point at
            a real repo; behaviour on a non-repo path is delegated to
            ``git`` (which exits non-zero, yielding an empty result).
        protected: Branch names that must always classify as
            ``protected``. Typically ``["main", "master"]`` plus any
            release branches the caller wants to preserve.
        main_branch: Name of the integration branch used for ancestry
            and squash-subject lookups. Defaults to ``"main"``.

    Returns:
        Mapping of branch name to ``Classification``. Empty on a repo
        with no branches (e.g. immediately after ``git init`` before
        the first commit).
    """
    branches = _list_branches(repo_path)
    if not branches:
        return {}

    protected_set = frozenset(protected)
    main_present = _main_exists(repo_path, main_branch)
    main_subjects: set[str] = (
        _recent_main_subjects(repo_path, main_branch, _SQUASH_LOOKBACK_DAYS)
        if main_present
        else set()
    )
    now_unix = int(time.time())

    return {
        branch.name: _classify_one(
            branch,
            repo_path=repo_path,
            main_branch=main_branch,
            main_present=main_present,
            protected_set=protected_set,
            main_subjects=main_subjects,
            now_unix=now_unix,
        )
        for branch in branches
    }


def _delete_branch(repo_path: Path, branch: str) -> bool:
    """Attempt to delete ``branch``; return whether it now no longer exists.

    Uses ``git branch -D`` with ``check=False`` so an already-pruned
    branch (idempotent re-run) yields ``True`` without surfacing the
    ``not found`` stderr to the caller. The boolean return signals
    whether the branch is *gone* after the call, which is the property
    callers actually want — not whether this specific invocation did
    the deleting.
    """
    result = _run_git(["branch", "-D", branch], repo_path)
    if result.returncode == 0:
        return True
    # git emits "branch '<name>' not found" or similar — verify absence
    # rather than parsing locale-sensitive error strings.
    check = _run_git(["rev-parse", "--verify", f"refs/heads/{branch}"], repo_path)
    return check.returncode != 0


def run_cleanup(
    repo_path: Path,
    protected: list[str],
    apply: bool,
    main_branch: str = "main",
) -> dict[str, object]:
    """Classify, optionally delete, and return a JSON-serialisable plan.

    Args:
        repo_path: Working tree to clean up.
        protected: Branches that must never be touched.
        apply: ``False`` (dry-run) classifies only; ``True`` deletes
            every branch whose category is in the auto-delete set.
        main_branch: Integration branch name; forwarded to
            ``classify_branches``.

    Returns:
        Dict with the following keys:

        * ``classifications`` — ``{branch: category_string}`` snapshot.
        * ``safe_to_delete`` — branches the plan would (or did) remove.
        * ``deleted`` — branches actually removed by this call (empty
          on dry-run).
        * ``skipped`` — safe candidates that were skipped because
          ``apply=False`` (the safety net for the dry-run JSON path).
        * ``protected`` — echo of the protected list for auditability.
        * ``main_branch`` — echo of the integration branch.
    """
    classifications = classify_branches(repo_path, protected, main_branch=main_branch)
    protected_set = frozenset(protected)
    safe_to_delete: list[str] = sorted(
        name
        for name, classification in classifications.items()
        if classification.safe_to_delete
        and classification.category in _AUTO_DELETE_CATEGORIES
        and name not in protected_set
    )

    deleted: list[str] = []
    skipped: list[str] = []
    if apply:
        for name in safe_to_delete:
            if _delete_branch(repo_path, name):
                deleted.append(name)
    else:
        skipped = list(safe_to_delete)

    return {
        "classifications": {
            name: classification.category for name, classification in classifications.items()
        },
        "safe_to_delete": safe_to_delete,
        "deleted": deleted,
        "skipped": skipped,
        "protected": list(protected),
        "main_branch": main_branch,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI entry point for ``cleanup_run.py``.

    Defaults are conservative: ``--dry-run`` is implied when neither
    ``--dry-run`` nor ``--apply`` is given, and ``--protect`` covers
    ``main,master`` so callers do not have to remember to pass it.
    """
    parser = argparse.ArgumentParser(
        prog="cleanup_run",
        description="Classify and optionally prune merged local branches.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="apply",
        action="store_false",
        help="Report the classification plan without deleting (default).",
    )
    mode.add_argument(
        "--apply",
        dest="apply",
        action="store_true",
        help="Delete branches classified as merged or squash-merged.",
    )
    parser.set_defaults(apply=False)
    parser.add_argument(
        "--protect",
        default="main,master",
        help="Comma-separated branches that must never be deleted.",
    )
    parser.add_argument(
        "--main",
        dest="main_branch",
        default="main",
        help="Integration branch name (defaults to 'main').",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="Path to the repository working tree. Defaults to cwd.",
    )
    args = parser.parse_args(argv)

    protected = [p.strip() for p in args.protect.split(",") if p.strip()]
    plan = run_cleanup(
        Path(args.repo),
        protected=protected,
        apply=args.apply,
        main_branch=args.main_branch,
    )
    print(json.dumps(plan, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":  # pragma: no cover — exercised via CLI only.
    sys.exit(main())
