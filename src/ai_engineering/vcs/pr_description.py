"""Provider-agnostic PR description builder.

Generates structured PR titles and bodies from project context:
active spec, recent commits, and branch name.

Output format follows the **What / Why / How / Checklist / Stats**
convention used across both GitHub and Azure DevOps pull requests.

Functions:
    build_pr_title — short PR title from branch and spec.
    build_pr_description — full Markdown PR body.
"""

from __future__ import annotations

import re
from pathlib import Path

from ai_engineering.git.operations import current_branch, run_git
from ai_engineering.state.models import TaskLifecycleState
from ai_engineering.state.work_plane import read_task_ledger, resolve_active_work_plane


def _active_spec_path(project_root: Path) -> Path:
    """Return the resolved active spec path from the work-plane contract."""
    return resolve_active_work_plane(project_root).spec_path


def _active_spec_relpath(project_root: Path) -> str:
    """Return the active spec path relative to the project root."""
    return _active_spec_path(project_root).relative_to(project_root).as_posix()


def build_pr_title(project_root: Path) -> str:
    """Build a PR title from the active spec and branch name.

    Format: ``feat(spec-NNN): <branch-slug-humanized>`` when a spec is active,
    or ``<branch-slug-humanized>`` when no spec is active.

    Args:
        project_root: Root directory of the project.

    Returns:
        Single-line PR title string.
    """
    branch = current_branch(project_root)
    slug = _humanize_branch(branch)
    spec = _read_active_spec(project_root)
    if spec:
        return f"feat(spec-{_normalize_spec_identifier(spec)}): {slug}"
    return slug


def build_pr_description(project_root: Path, *, max_commits: int = 20) -> str:
    """Build a structured Markdown PR description.

    Sections: **What**, **Why**, **How**, **Checklist**, **Stats**.
    When a spec is active, ``What`` and ``Why`` are populated from
    ``spec.md``; otherwise a branch-derived summary is used.

    Args:
        project_root: Root directory of the project.
        max_commits: Maximum number of commit subjects to include.

    Returns:
        Multi-line Markdown string suitable for PR body.
    """
    spec = _read_active_spec(project_root)
    branch = current_branch(project_root)
    commits = _recent_commit_subjects(project_root, max_commits=max_commits)
    ctx = _read_spec_context(project_root, spec) if spec else _empty_spec_context()

    lines: list[str] = []
    lines.extend(_what_section_lines(spec, branch, ctx))
    lines.extend(_why_section_lines(project_root, spec, ctx))
    lines.extend(_how_section_lines(commits))
    lines.extend(_issue_section_lines(project_root, spec))
    lines.extend(_checklist_section_lines())
    lines.extend(_stats_section_lines(project_root, branch, commits))

    return "\n".join(lines) if lines else "No description generated."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _empty_spec_context() -> dict[str, str]:
    """Return an empty spec context payload."""
    return {"title": "", "problem": "", "solution": ""}


def _what_section_lines(spec: str | None, branch: str, ctx: dict[str, str]) -> list[str]:
    """Build the What section for the PR description."""
    if not spec:
        return [f"## What\n\n{_humanize_branch(branch)}.\n"]

    normalized_spec = _normalize_spec_identifier(spec)
    spec_id = normalized_spec.split("-")[0] if "-" in normalized_spec else normalized_spec
    title = ctx["title"] or _humanize_branch(branch)
    return [f"## What\n\nImplements Spec {spec_id} — {title}.\n"]


def _why_section_lines(project_root: Path, spec: str | None, ctx: dict[str, str]) -> list[str]:
    """Build the Why section plus spec link lines."""
    if not spec:
        return []

    lines: list[str] = []
    if ctx["problem"]:
        lines.append(f"## Why\n\n{ctx['problem']}\n")

    spec_url = _build_spec_url(project_root, spec)
    display_spec = _normalize_spec_identifier(spec)
    lines.append(
        f"**Spec**: [{display_spec}]({spec_url})\n" if spec_url else f"**Spec**: `{display_spec}`\n"
    )
    return lines


def _how_section_lines(commits: list[str]) -> list[str]:
    """Build the How section from commit subjects."""
    if not commits:
        return []

    return ["## How\n", *[f"- {subject}" for subject in commits], ""]


def _issue_section_lines(project_root: Path, spec: str | None) -> list[str]:
    """Build issue reference lines for the PR body."""
    if not spec:
        return []

    spec_refs = _read_spec_refs(project_root)
    if spec_refs:
        closeable, mention_only = _resolve_refs(project_root, spec_refs)
        if closeable or mention_only:
            return _resolved_issue_lines(closeable, mention_only)
    return _legacy_issue_lines(project_root, spec)


def _resolved_issue_lines(closeable: list[str], mention_only: list[str]) -> list[str]:
    """Format resolved closeable and mention-only refs."""
    lines = [ref if ref.startswith("AB#") else f"Closes {ref}" for ref in closeable]
    lines.extend(f"Related: {ref}" for ref in mention_only)
    if lines:
        lines.append("")
    return lines


def _legacy_issue_lines(project_root: Path, spec: str) -> list[str]:
    """Build legacy issue-closing lines from provider lookup."""
    issue_ref = _build_issue_reference(project_root, spec)
    return [f"{issue_ref}\n"] if issue_ref else []


def _checklist_section_lines() -> list[str]:
    """Build the static checklist section."""
    return [
        "## Checklist\n",
        "- [ ] All tests pass",
        "- [ ] `ruff check` clean",
        "- [ ] `ty check` clean",
        "- [ ] `gitleaks` — no leaks",
        "- [ ] CHANGELOG.md updated",
        "",
    ]


def _stats_section_lines(project_root: Path, branch: str, commits: list[str]) -> list[str]:
    """Build the Stats section when diff or commit data is available."""
    stats = _git_diff_stats(project_root)
    commit_count = len(commits)
    if not stats and not commit_count:
        return []

    lines = ["## Stats\n"]
    if stats:
        lines.append(f"- {stats}")
    if commit_count:
        lines.append(f"- {commit_count} commits on `{branch}`")
    lines.append("")
    return lines


def _get_repo_url(project_root: Path) -> str | None:
    """Detect the repository web URL from the git remote origin.

    Supports GitHub (``github.com``) and Azure DevOps
    (``dev.azure.com``, ``visualstudio.com``).

    Args:
        project_root: Root directory of the project.

    Returns:
        Repository web URL, or None if detection fails.
    """
    ok, output = run_git(["remote", "get-url", "origin"], project_root)
    if not ok or not output.strip():
        return None

    url = output.strip()

    # SSH → HTTPS conversion for GitHub
    if url.startswith("git@github.com:"):
        path = url.removeprefix("git@github.com:")
        if path.endswith(".git"):
            path = path[:-4]
        return f"https://github.com/{path}"

    # HTTPS GitHub
    if "github.com" in url:
        if url.endswith(".git"):
            url = url[:-4]
        return url

    # SSH → HTTPS conversion for Azure DevOps
    if url.startswith("git@ssh.dev.azure.com:"):
        # git@ssh.dev.azure.com:v3/org/project/repo
        path = url.removeprefix("git@ssh.dev.azure.com:v3/")
        parts = path.split("/")
        if len(parts) >= 3:
            org, project, repo = parts[0], parts[1], parts[2]
            return f"https://dev.azure.com/{org}/{project}/_git/{repo}"

    # HTTPS Azure DevOps
    if "dev.azure.com" in url:
        if url.endswith(".git"):
            url = url[:-4]
        return url

    return None


def _build_spec_url(project_root: Path, spec: str) -> str | None:
    """Build a clickable URL to the active spec file.

    The URL follows the resolved active work-plane contract rather than
    assuming the legacy singleton ``.ai-engineering/specs/spec.md`` path.

    Args:
        project_root: Root directory of the project.
        spec: Spec identifier (e.g., ``"036-platform-runbooks"``).

    Returns:
        Full URL to the spec file, or None if repo URL cannot be determined.
    """
    repo_url = _get_repo_url(project_root)
    if not repo_url:
        return None

    spec_path = _active_spec_relpath(project_root)

    if "github.com" in repo_url:
        return f"{repo_url}/blob/main/{spec_path}"

    if "dev.azure.com" in repo_url:
        return f"{repo_url}?path=/{spec_path}&version=GBmain"

    return None


def _normalize_spec_identifier(spec: str) -> str:
    """Normalize a spec identifier for user-facing rendering."""
    return spec.removeprefix("spec-")


def _read_active_spec(project_root: Path) -> str | None:
    """Read the active spec identifier from the resolved work plane.

    Extracts the ``id`` field from YAML frontmatter, or falls back
    to scanning for a ``# Spec NNN`` heading pattern.

    Args:
        project_root: Root directory of the project.

    Returns:
        Active spec identifier (e.g. ``"055"``),
        or None if no spec is active or file is missing.
    """
    work_plane = resolve_active_work_plane(project_root)
    spec_path = work_plane.spec_path
    if not spec_path.exists():
        return None

    try:
        text = spec_path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Placeholder means no active spec
    if text.strip().startswith("# No active spec"):
        ledger = read_task_ledger(project_root)
        if ledger is not None and any(
            task.status != TaskLifecycleState.DONE for task in ledger.tasks
        ):
            fallback_id = work_plane.specs_dir.name.strip()
            return fallback_id or None
        return None

    # Try frontmatter id field
    match = re.search(r'^id:\s*["\']?(\S+?)["\']?\s*$', text, re.MULTILINE)
    if match:
        return match.group(1).strip()

    # Fallback: NNN- pattern in headings
    match = re.search(r"^# .*?(\d{3})-", text, re.MULTILINE)
    if match:
        return match.group(1)

    return None


def _read_spec_refs(project_root: Path) -> dict[str, list[str]]:
    """Read work-item refs from spec frontmatter.

    Parses the ``refs`` block in ``specs/spec.md`` YAML frontmatter::

        ---
        id: "055"
        refs:
          features: [AB#100]
          user_stories: [AB#101]
          tasks: [AB#102, AB#103]
          issues: ["#45", "#46"]
        ---

    Args:
        project_root: Root directory of the project.

    Returns:
        Dict with keys ``features``, ``user_stories``, ``tasks``,
        ``issues`` (each a list of strings).  Empty dict if no refs
        or no frontmatter found.
    """
    spec_path = _active_spec_path(project_root)
    if not spec_path.exists():
        return {}

    try:
        text = spec_path.read_text(encoding="utf-8")
    except OSError:
        return {}

    # Extract frontmatter block
    fm_match = re.match(r"^---\n(.+?)\n---", text, re.DOTALL)
    if not fm_match:
        return {}

    frontmatter = fm_match.group(1)

    # Check if refs section exists
    refs_match = re.search(r"^refs:\s*$", frontmatter, re.MULTILINE)
    if not refs_match:
        return {}

    # Extract each ref category
    result: dict[str, list[str]] = {}
    for key in ("features", "user_stories", "tasks", "issues"):
        pattern = rf"^\s+{key}:\s*\[([^\]]*)\]"
        match = re.search(pattern, frontmatter, re.MULTILINE)
        if match:
            raw = match.group(1).strip()
            if raw:
                items = [item.strip().strip("\"'") for item in raw.split(",") if item.strip()]
                result[key] = items

    return result


def _resolve_refs(
    project_root: Path,
    refs: dict[str, list[str]],
) -> tuple[list[str], list[str]]:
    """Resolve spec refs into closeable and mention-only lists.

    Delegates to ``work_items.service.resolve_closeable_refs``
    for hierarchy rule evaluation.

    Args:
        project_root: Root directory of the project.
        refs: Ref dict from ``_read_spec_refs``.

    Returns:
        Tuple of ``(closeable_refs, mention_only_refs)``.
    """
    try:
        from ai_engineering.work_items.service import resolve_closeable_refs
    except ImportError:
        return [], []

    return resolve_closeable_refs(project_root, refs)


def _read_spec_context(project_root: Path, spec: str) -> dict[str, str]:
    """Read the resolved active spec and extract key sections for the PR description.

    Uses the active work-plane resolver to locate the current spec surface.

    Args:
        project_root: Root directory of the project.
        spec: Spec identifier (used for logging, not path construction).

    Returns:
        Dict with ``title``, ``problem``, ``solution`` (may be empty strings).
    """
    empty: dict[str, str] = {"title": "", "problem": "", "solution": ""}
    spec_path = _active_spec_path(project_root)
    if not spec_path.exists():
        return empty

    try:
        text = spec_path.read_text(encoding="utf-8")
    except OSError:
        return empty

    title = _extract_spec_title(text)

    problem = _extract_section(text, "Problem")
    solution = _extract_section(text, "Solution")

    return {"title": title, "problem": problem, "solution": solution}


def _extract_section(text: str, heading: str) -> str:
    """Extract first paragraph of a ``## <heading>`` section.

    Args:
        text: Full Markdown document text.
        heading: Section heading (e.g. ``"Problem"``).

    Returns:
        First paragraph of the section, or empty string if not found.
    """
    target_heading = f"## {heading}"
    collecting = False
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.rstrip()
        if stripped.startswith("## "):
            if collecting:
                break
            collecting = stripped == target_heading
            continue
        if collecting:
            lines.append(line)

    content = "\n".join(lines).strip()
    if not content:
        return ""
    paragraphs = content.split("\n\n")
    return paragraphs[0].strip() if paragraphs else ""


def _extract_spec_title(text: str) -> str:
    """Extract the title suffix from the first level-1 spec heading."""
    for line in text.splitlines():
        if not line.startswith("# "):
            continue
        _, separator, tail = line.partition(" — ")
        return tail.strip() if separator else ""
    return ""


def _git_diff_stats(project_root: Path) -> str | None:
    """Get the summary line of ``git diff --stat`` vs ``origin/main``.

    Args:
        project_root: Root directory of the project.

    Returns:
        Summary string (e.g. ``"12 files changed, 340 insertions(+), …"``),
        or None if unavailable.
    """
    ok, output = run_git(
        ["diff", "--stat", "origin/main..HEAD"],
        project_root,
    )
    if not ok or not output.strip():
        return None
    lines = output.strip().splitlines()
    return lines[-1].strip() if lines else None


def _recent_commit_subjects(
    project_root: Path,
    *,
    max_commits: int = 20,
) -> list[str]:
    """Get recent commit subjects on the current branch vs origin/main.

    Falls back to the last ``max_commits`` commits if origin/main
    is not reachable.

    Args:
        project_root: Root directory of the project.
        max_commits: Maximum number of subjects to return.

    Returns:
        List of commit subject strings (newest first).
    """
    # Try branch diff against origin/main
    ok, output = run_git(
        ["log", "origin/main..HEAD", "--format=%s", f"-{max_commits}"],
        project_root,
    )
    if ok and output.strip():
        return [line.strip() for line in output.strip().splitlines() if line.strip()]

    # Fallback: last N commits
    ok, output = run_git(
        ["log", "--format=%s", f"-{max_commits}"],
        project_root,
    )
    if ok and output.strip():
        return [line.strip() for line in output.strip().splitlines() if line.strip()]

    return []


def _build_issue_reference(project_root: Path, spec: str) -> str | None:
    """Build an issue-closing keyword for the PR body.

    Returns ``Closes #N`` (GitHub) or ``AB#NNN`` (Azure DevOps),
    or None if no linked issue is found.

    Args:
        project_root: Root directory of the project.
        spec: Spec slug (e.g. ``"037-work-item-sync"``).

    Returns:
        Issue reference string, or None.
    """
    try:
        from ai_engineering.work_items.service import get_linked_issue_id
    except ImportError:
        return None

    issue_id = get_linked_issue_id(project_root, spec)
    if not issue_id:
        return None

    from ai_engineering.vcs.factory import detect_from_remote

    provider_name = detect_from_remote(project_root)
    if provider_name == "azure_devops":
        return f"AB#{issue_id}"
    return f"Closes #{issue_id}"


def _humanize_branch(branch: str) -> str:
    """Convert a branch name to a human-readable title.

    Strips common prefixes (``feat/``, ``fix/``, ``chore/``) and replaces
    hyphens/underscores with spaces, capitalizing the first word.

    Args:
        branch: Git branch name.

    Returns:
        Human-readable title string.
    """
    # Strip common prefixes
    for prefix in ("feat/", "fix/", "chore/", "refactor/", "docs/", "spec/"):
        if branch.startswith(prefix):
            branch = branch[len(prefix) :]
            break

    # Replace separators with spaces
    title = branch.replace("-", " ").replace("_", " ").strip()
    if title:
        title = title[0].upper() + title[1:]
    return title
