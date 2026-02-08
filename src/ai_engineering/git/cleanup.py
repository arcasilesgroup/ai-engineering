"""Safe git branch cleanup workflow."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from ai_engineering.paths import repo_root, state_dir
from ai_engineering.policy.gates import PROTECTED_BRANCHES, current_branch
from ai_engineering.state.io import append_ndjson, write_json


COMPLIANCE_PREFIXES = ("dev/", "release/", "hotfix/")


def _run(root: Path, args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=root, capture_output=True, text=True, check=False)


def _default_branch(root: Path) -> str:
    symbolic = _run(root, ["git", "symbolic-ref", "refs/remotes/origin/HEAD"])
    if symbolic.returncode == 0:
        ref = symbolic.stdout.strip()
        if ref.startswith("refs/remotes/origin/"):
            return ref.removeprefix("refs/remotes/origin/")

    for candidate in ("main", "master"):
        exists = _run(root, ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{candidate}"])
        if exists.returncode == 0:
            return candidate
    return "main"


def _is_protected(branch: str, default_branch: str) -> bool:
    if branch in PROTECTED_BRANCHES or branch == default_branch:
        return True
    return any(branch.startswith(prefix) for prefix in COMPLIANCE_PREFIXES)


def _local_merged(root: Path, default_branch: str, current: str) -> list[str]:
    proc = _run(root, ["git", "branch", "--merged", default_branch])
    if proc.returncode != 0:
        return []
    branches: list[str] = []
    for line in proc.stdout.splitlines():
        branch = line.replace("*", "").strip()
        if not branch or branch == current or _is_protected(branch, default_branch):
            continue
        branches.append(branch)
    return sorted(set(branches))


def _local_gone(root: Path, default_branch: str, current: str) -> list[str]:
    proc = _run(root, ["git", "branch", "-vv"])
    if proc.returncode != 0:
        return []
    branches: list[str] = []
    for line in proc.stdout.splitlines():
        if ": gone]" not in line:
            continue
        cleaned = line.replace("*", "").strip()
        branch = cleaned.split()[0]
        if branch == current or _is_protected(branch, default_branch):
            continue
        branches.append(branch)
    return sorted(set(branches))


def _remote_merged(root: Path, default_branch: str) -> list[str]:
    proc = _run(root, ["git", "branch", "-r", "--merged", f"origin/{default_branch}"])
    if proc.returncode != 0:
        return []
    branches: list[str] = []
    for line in proc.stdout.splitlines():
        raw = line.strip()
        if not raw or raw.endswith("/HEAD"):
            continue
        if raw.startswith("origin/"):
            branch = raw.removeprefix("origin/")
        else:
            continue
        if _is_protected(branch, default_branch):
            continue
        branches.append(branch)
    return sorted(set(branches))


def _delete_local(root: Path, branches: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    deleted: list[str] = []
    errors: list[dict[str, str]] = []
    for branch in branches:
        proc = _run(root, ["git", "branch", "-d", branch])
        if proc.returncode == 0:
            deleted.append(branch)
        else:
            errors.append({"branch": branch, "error": proc.stderr.strip() or proc.stdout.strip()})
    return deleted, errors


def _delete_remote(root: Path, branches: list[str]) -> tuple[list[str], list[dict[str, str]]]:
    deleted: list[str] = []
    errors: list[dict[str, str]] = []
    for branch in branches:
        proc = _run(root, ["git", "push", "origin", "--delete", branch])
        if proc.returncode == 0:
            deleted.append(branch)
        else:
            errors.append({"branch": branch, "error": proc.stderr.strip() or proc.stdout.strip()})
    return deleted, errors


def run_git_cleanup(*, apply: bool, include_remote: bool, checkout_default: bool) -> dict[str, Any]:
    """Analyze or apply safe git branch cleanup operations."""

    root = repo_root()
    _run(root, ["git", "fetch", "--all", "--prune"])

    default_branch = _default_branch(root)
    current = current_branch(root)

    if checkout_default and apply and current != default_branch:
        _run(root, ["git", "checkout", default_branch])
        current = current_branch(root)

    local_merged = _local_merged(root, default_branch, current)
    local_gone = _local_gone(root, default_branch, current)
    local_candidates = sorted(set(local_merged + local_gone))
    remote_candidates = _remote_merged(root, default_branch) if include_remote else []

    deleted_local: list[str] = []
    deleted_remote: list[str] = []
    errors: list[dict[str, str]] = []

    if apply:
        deleted_local, local_errors = _delete_local(root, local_candidates)
        errors.extend(local_errors)
        if include_remote:
            deleted_remote, remote_errors = _delete_remote(root, remote_candidates)
            errors.extend(remote_errors)

    payload: dict[str, Any] = {
        "repo": str(root),
        "apply": apply,
        "defaultBranch": default_branch,
        "currentBranch": current,
        "includeRemote": include_remote,
        "checkoutDefault": checkout_default,
        "candidates": {
            "localMerged": local_merged,
            "localGone": local_gone,
            "localTotal": local_candidates,
            "remoteMerged": remote_candidates,
        },
        "deleted": {
            "local": deleted_local,
            "remote": deleted_remote,
        },
        "errors": errors,
    }

    write_json(state_dir(root) / "branch-cleanup-report.json", payload)
    append_ndjson(
        state_dir(root) / "audit-log.ndjson",
        {
            "event": "git_cleanup_applied" if apply else "git_cleanup_preview",
            "actor": "git-cleanup",
            "details": {
                "defaultBranch": default_branch,
                "localCandidates": len(local_candidates),
                "remoteCandidates": len(remote_candidates),
                "deletedLocal": len(deleted_local),
                "deletedRemote": len(deleted_remote),
            },
        },
    )
    return payload
