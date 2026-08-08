"""Editing a fourth file on a branch that has no plan.

It counts honestly: the branch's own changes against the merge base with the default
branch, an exclusion list for the files that carry the design rather than the
implementation, and an explicit policy for the default branch — where this gate stays
quiet, because a push to the default branch is pre-push's business and two controls
saying the same thing is one control nobody reads.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from _emit import config, repo_root
from _wrap import guard

BUDGET = 3  # the fourth file is the one that trips it
SKIP = ("specs/", "docs/", ".ai/", "CONSTITUTION.md", "AGENTS.md", "CLAUDE.md")


def git(root: Path, *args: str) -> str:
    out = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=5)
    return out.stdout.strip()


def default_branch(root: Path) -> str:
    ref = git(root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD")
    return ref.rsplit("/", 1)[-1] if ref else "main"


def changed(root: Path) -> set[str]:
    """Files this branch changed, not files the working tree happens to have dirty."""
    head = default_branch(root)
    base = git(root, "merge-base", "HEAD", head) or git(
        root, "merge-base", "HEAD", f"origin/{head}"
    )
    names = git(root, "diff", "--name-only", base, "HEAD") if base else ""
    names += "\n" + git(root, "diff", "--name-only", "HEAD")
    names += "\n" + git(root, "ls-files", "--others", "--exclude-standard")
    return {n for n in names.split("\n") if n}


def has_plan(names: set[str]) -> bool:
    """The plan that opens the gate has to belong to the branch it opens. The glob this
    replaces asked only whether any plan.md existed anywhere under specs/, so the first
    spec a repository ever wrote opened the gate for every branch after it — which is why
    this guard had not fired in its own repository since 001 landed."""
    return any(name.startswith("specs/") and name.endswith("plan.md") for name in names)


@guard("design_gate")
def run(payload: dict) -> str | None:
    budget = int(config().get("guards", {}).get("design_budget", BUDGET))
    if budget <= 0:
        return None
    root = repo_root()
    if root is None:
        return None
    branch = git(root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch in (default_branch(root), "HEAD"):
        return None  # pre-push owns the default branch; this gate does not duplicate it
    names = changed(root)
    if has_plan(names):
        return None

    target = (payload.get("tool_input") or {}).get("file_path", "")
    try:
        target = str(Path(target).resolve().relative_to(root))
    except (ValueError, OSError):
        target = ""
    files = {name for name in names if not name.startswith(SKIP)}
    files |= {target} if target and not target.startswith(SKIP) else set()
    if len(files) <= budget:
        return None
    return f"this branch has changed {len(files)} files and has no plan. Write one with /ai-plan."
