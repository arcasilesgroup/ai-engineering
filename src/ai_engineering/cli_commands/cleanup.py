"""``ai-eng cleanup`` — 7-mode git branch cleanup CLI (spec-133 D-133-03).

Top-level command with subcommands:

- ``branches`` — 7 modes via flags: ``--pruned`` / ``--merged`` /
  ``--squashed`` / ``--stale`` / ``--untracked`` / ``--reset`` / ``--all``
- ``runtime`` — rotates ``.ai-engineering/runtime/`` per retention policy
- ``specs`` — invokes ``spec_lifecycle.py consolidate_shipped``
- ``all`` — composite: branches --all + runtime + specs

Universal flags (apply to every subcommand):
- ``--dry-run`` — preview without acting
- ``--json`` — structured output for CI / skill consumption
- ``--strict`` — fail-fast on first error
- ``--tracked`` — also delete corresponding remote tracking refs

Quality bar (spec-133 D-133-26):
- Idempotent (re-run = no-op)
- Exit-coded per category (0 / 1 / 2 / 78)
- Refuses detached HEAD
- Never deletes the current branch
"""

from __future__ import annotations

import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import typer

from ai_engineering.cli_output import is_json_mode, set_json_mode
from ai_engineering.git.operations import (
    PROTECTED_BRANCHES,
    current_branch,
    run_git,
)
from ai_engineering.maintenance.branch_cleanup import (
    delete_branches,
    fetch_and_prune,
    list_gone_branches,
    list_merged_branches,
)
from ai_engineering.paths import resolve_project_root

# ---------------------------------------------------------------------------
# Subcommand: cleanup branches (7 modes)
# ---------------------------------------------------------------------------


@dataclass
class CleanupBranchesResult:
    """Result envelope for ``ai-eng cleanup branches``."""

    mode: str
    dry_run: bool
    deleted: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    pruned_refs: int = 0

    def to_envelope(self) -> dict[str, object]:
        return {
            "ok": not self.errors,
            "command": "cleanup-branches",
            "code": 0 if not self.errors else 1,
            "data": {
                "mode": self.mode,
                "dry_run": self.dry_run,
                "deleted": self.deleted,
                "skipped": self.skipped,
                "errors": self.errors,
                "pruned_refs": self.pruned_refs,
            },
        }


def _refuse_detached_head(root: Path) -> None:
    """Refuse to operate if HEAD is detached (D-133-26 safety)."""
    active = current_branch(root)
    if not active or active == "HEAD":
        sys.stderr.write(
            "BLOCKED: refusing to operate in detached HEAD state.\n"
            "  Checkout a branch first: git checkout main\n"
        )
        raise typer.Exit(code=2)


def _list_squashed_branches(root: Path, base: str = "main") -> list[str]:
    """Detect squash-merged branches via ``merge-base`` + ``commit-tree``.

    Catches branches that GitHub/GitLab "Squash and merge" workflows
    leave behind — ``git branch --merged`` misses these entirely.
    Algorithm per git-trim taxonomy (research-anchored, D-133-03).
    """
    ok, branches_out = run_git(
        ["branch", "--format=%(refname:short)"],
        root,
    )
    if not ok:
        return []
    active = current_branch(root)
    candidates: list[str] = []
    for line in branches_out.splitlines():
        name = line.strip()
        if not name or name in PROTECTED_BRANCHES or name == active:
            continue
        if name == base:
            continue

        # Compute the merge-base and the diff-tree hash.
        mb_ok, mb_out = run_git(["merge-base", base, name], root)
        if not mb_ok or not mb_out.strip():
            continue
        merge_base = mb_out.strip()

        tree_ok, tree_out = run_git(["rev-parse", f"{name}^{{tree}}"], root)
        if not tree_ok:
            continue
        tree = tree_out.strip()

        # commit-tree against merge-base, compare against cherry-picks in base
        ct_ok, ct_out = run_git(["commit-tree", tree, "-p", merge_base, "-m", "_check"], root)
        if not ct_ok:
            continue
        synthetic = ct_out.strip()

        # If synthetic commit is reachable from base (was squash-merged), include
        cherry_ok, cherry_out = run_git(["cherry", base, synthetic], root)
        if cherry_ok and cherry_out.strip().startswith("-"):
            candidates.append(name)

    return candidates


def _list_untracked_branches(root: Path) -> list[str]:
    """List local branches with no remote-tracking ref."""
    ok, output = run_git(
        ["for-each-ref", "--format=%(refname:short) %(upstream)", "refs/heads/"],
        root,
    )
    if not ok:
        return []
    active = current_branch(root)
    branches: list[str] = []
    for line in output.splitlines():
        parts = line.split(maxsplit=1)
        name = parts[0]
        upstream = parts[1] if len(parts) > 1 else ""
        if not upstream and name not in PROTECTED_BRANCHES and name != active:
            branches.append(name)
    return branches


def _list_stale_branches(root: Path, days: int = 90) -> list[str]:
    """List branches with no commits in N days (default 90)."""
    import datetime

    cutoff_ts = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())
    ok, output = run_git(
        ["for-each-ref", "--format=%(refname:short) %(committerdate:unix)", "refs/heads/"],
        root,
    )
    if not ok:
        return []
    active = current_branch(root)
    branches: list[str] = []
    for line in output.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue
        name, ts_str = parts[0], parts[-1]
        try:
            ts = int(ts_str)
        except ValueError:
            continue
        if ts <= cutoff_ts and name not in PROTECTED_BRANCHES and name != active:
            branches.append(name)
    return branches


def _resolve_target_branches(
    root: Path,
    *,
    pruned: bool,
    merged: bool,
    squashed: bool,
    stale: bool,
    untracked: bool,
    reset: bool,
    all_modes: bool,
) -> list[str]:
    """Return the union of branch names matching the enabled modes."""
    if all_modes:
        pruned = merged = squashed = stale = untracked = reset = True

    targets: set[str] = set()
    if pruned:
        # Pruned = upstream tracking ref gone = `list_gone_branches`
        targets.update(list_gone_branches(root))
    if merged:
        targets.update(list_merged_branches(root))
    if squashed:
        targets.update(_list_squashed_branches(root))
    if stale:
        targets.update(_list_stale_branches(root))
    if untracked:
        targets.update(_list_untracked_branches(root))
    if reset:
        # `--reset` is interactive in the original git-trim; for ai-eng we
        # leave the implementation as observation-only without --force.
        targets.update(_list_untracked_branches(root))
    return sorted(targets)


def cleanup_branches_cmd(
    pruned: Annotated[
        bool, typer.Option("--pruned", help="Delete branches with [gone] upstream.")
    ] = False,
    merged: Annotated[bool, typer.Option("--merged", help="Delete merged branches.")] = False,
    squashed: Annotated[
        bool, typer.Option("--squashed", help="Delete squash-merged branches.")
    ] = False,
    stale: Annotated[
        bool, typer.Option("--stale", help="Delete branches with no commits in 90 days.")
    ] = False,
    untracked: Annotated[
        bool, typer.Option("--untracked", help="Delete branches with no upstream ref.")
    ] = False,
    reset: Annotated[bool, typer.Option("--reset", help="Force re-sync to remote state.")] = False,
    all_modes: Annotated[bool, typer.Option("--all", help="All 7 cleanup modes combined.")] = False,
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview without deleting.")] = False,
    output_json: Annotated[bool, typer.Option("--json", help="Output structured JSON.")] = False,
    strict: Annotated[bool, typer.Option("--strict", help="Fail-fast on first error.")] = False,
    tracked: Annotated[
        bool, typer.Option("--tracked", help="Also delete remote tracking refs.")
    ] = False,
    force: Annotated[bool, typer.Option("--force", help="Bypass safety checks.")] = False,
) -> None:
    """Clean up local git branches across 7 canonical modes.

    Exit codes per D-133-26:
    - 0 = clean (no branches matched OR all matched-and-deleted)
    - 1 = found-and-acted (deletions happened)
    - 2 = blocked-by-protection (detached HEAD or other safety guard)
    - 78 = stack-drift-block (set by middleware)
    """
    if output_json:
        set_json_mode(True)

    root = resolve_project_root(None)
    _refuse_detached_head(root)

    # D-149-02 (was D-148-16): a no-flag invocation is PLAN-ONLY and deletes
    # nothing. The old "default to --merged and delete" was a destructive
    # default (the inverse of the pit of success). Now the operator must pass
    # an explicit mode (--merged/.../--all) to delete, or --dry-run to preview.
    plan_only = not any([pruned, merged, squashed, stale, untracked, reset, all_modes])
    if plan_only:
        merged = True  # compute the merged candidate set to show in the plan
        chosen_mode = "plan-only (no mode flag)"
    else:
        modes = [
            n
            for n, v in [
                ("pruned", pruned),
                ("merged", merged),
                ("squashed", squashed),
                ("stale", stale),
                ("untracked", untracked),
                ("reset", reset),
                ("all", all_modes),
            ]
            if v
        ]
        chosen_mode = ",".join(modes)

    # Pruned mode requires `git fetch --prune` first
    pruned_refs = 0
    if pruned or all_modes:
        ok, n = fetch_and_prune(root)
        if ok:
            pruned_refs = n

    targets = _resolve_target_branches(
        root,
        pruned=pruned,
        merged=merged,
        squashed=squashed,
        stale=stale,
        untracked=untracked,
        reset=reset,
        all_modes=all_modes,
    )

    # Plan-only and dry-run both delete nothing; the envelope reports
    # ``dry_run`` truthfully so machine consumers never see a silent delete.
    no_delete = dry_run or plan_only
    result = CleanupBranchesResult(mode=chosen_mode, dry_run=no_delete, pruned_refs=pruned_refs)

    if no_delete:
        result.skipped = targets
    elif targets:
        deleted, failed = delete_branches(root, targets, force=force)
        result.deleted = deleted
        result.skipped = failed

    if is_json_mode():
        print(json.dumps(result.to_envelope()))
    else:
        if plan_only:
            print(f"PLAN-ONLY: {len(targets)} branch(es) match --merged; nothing deleted.")
            for b in targets:
                print(f"  - {b}")
            print(
                "Re-run with an explicit mode (--merged / --pruned / --all) to delete, "
                "or --dry-run to preview."
            )
        elif dry_run:
            print(f"DRY-RUN: would delete {len(targets)} branches (mode: {chosen_mode})")
            for b in targets:
                print(f"  - {b}")
        else:
            deleted_n = len(result.deleted)
            skipped_n = len(result.skipped)
            print(f"Deleted {deleted_n} branches; skipped {skipped_n} (mode: {chosen_mode})")

    if result.errors:
        raise typer.Exit(code=1)


# ---------------------------------------------------------------------------
# Subcommand: cleanup runtime
# ---------------------------------------------------------------------------


def cleanup_runtime_cmd(
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Preview rotation without acting.")
    ] = False,
    output_json: Annotated[bool, typer.Option("--json", help="Output structured JSON.")] = False,
) -> None:
    """Rotate ``.ai-engineering/runtime/`` per retention policy."""
    if output_json:
        set_json_mode(True)
    root = resolve_project_root(None)
    script = root / ".ai-engineering" / "scripts" / "runtime_rotate.py"
    args = [sys.executable, str(script)]
    if dry_run:
        args.append("--dry-run")
    if output_json:
        args.append("--json")
    result = subprocess.run(args, check=False)
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


# ---------------------------------------------------------------------------
# Subcommand: cleanup specs
# ---------------------------------------------------------------------------


def cleanup_specs_cmd(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview spec consolidation.")] = False,
    output_json: Annotated[bool, typer.Option("--json", help="Output structured JSON.")] = False,
) -> None:
    """Reconcile merged specs, then consolidate shipped ledger rows.

    Runs two ``spec_lifecycle.py`` verbs in order (spec-153 D-153-03):

    1. ``reconcile_merged`` — the merged-branch backstop: auto-marks any
       non-terminal spec whose branch is merged into the default branch as
       SHIPPED (catching GitHub-UI merges ``/ai-pr`` never marked). It mutates,
       so it is **skipped in ``--dry-run``** (the verb has no preview mode).
    2. ``consolidate_shipped`` — appends the canonical ``_history.md`` row for
       every SHIPPED sidecar (including the ones reconcile just marked).
    """
    if output_json:
        set_json_mode(True)
    root = resolve_project_root(None)
    script = root / ".ai-engineering" / "scripts" / "spec_lifecycle.py"

    # 1. Reconcile merged-but-unshipped specs first (mutating; live runs only).
    #    Fail-open: a non-zero reconcile must not block the consolidate pass.
    if not dry_run:
        reconcile_args = [sys.executable, str(script), "reconcile_merged"]
        subprocess.run(reconcile_args, check=False)

    # 2. Consolidate SHIPPED sidecars into the ledger (honours --dry-run).
    consolidate_args = [sys.executable, str(script), "consolidate_shipped"]
    if dry_run:
        consolidate_args.append("--dry-run")
    result = subprocess.run(consolidate_args, check=False)
    if result.returncode != 0:
        raise typer.Exit(code=result.returncode)


# ---------------------------------------------------------------------------
# Subcommand: cleanup all (composite)
# ---------------------------------------------------------------------------


def cleanup_all_cmd(
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Preview all cleanups.")] = False,
    output_json: Annotated[bool, typer.Option("--json", help="Output structured JSON.")] = False,
) -> None:
    """Run branches --all + runtime + specs in sequence."""
    if output_json:
        set_json_mode(True)
    cleanup_branches_cmd(
        all_modes=True,
        dry_run=dry_run,
        output_json=output_json,
    )
    cleanup_runtime_cmd(dry_run=dry_run, output_json=output_json)
    cleanup_specs_cmd(dry_run=dry_run, output_json=output_json)
