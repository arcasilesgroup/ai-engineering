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
        return f"feat(spec-{spec}): {slug}"
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
    lines: list[str] = []

    spec = _read_active_spec(project_root)
    branch = current_branch(project_root)
    commits = _recent_commit_subjects(project_root, max_commits=max_commits)

    # -- What ----------------------------------------------------------
    if spec:
        ctx = _read_spec_context(project_root, spec)
        spec_id = spec.split("-")[0] if "-" in spec else spec
        title = ctx["title"] or _humanize_branch(branch)
        lines.append(f"## What\n\nImplements Spec {spec_id} — {title}.\n")
    else:
        lines.append(f"## What\n\n{_humanize_branch(branch)}.\n")

    # -- Why -----------------------------------------------------------
    if spec:
        ctx = ctx if "ctx" in dir() else _read_spec_context(project_root, spec)
        if ctx["problem"]:
            lines.append(f"## Why\n\n{ctx['problem']}\n")
        spec_url = _build_spec_url(project_root, spec)
        if spec_url:
            lines.append(f"**Spec**: [{spec}]({spec_url})\n")
        else:
            lines.append(f"**Spec**: `{spec}`\n")

    # -- How -----------------------------------------------------------
    if commits:
        lines.append("## How\n")
        for subject in commits:
            lines.append(f"- {subject}")
        lines.append("")

    # -- Issue link -----------------------------------------------------
    if spec:
        spec_refs = _read_spec_refs(project_root)
        if spec_refs:
            closeable, mention_only = _resolve_refs(project_root, spec_refs)
            if closeable or mention_only:
                for ref in closeable:
                    if ref.startswith("AB#"):
                        lines.append(ref)
                    else:
                        lines.append(f"Closes {ref}")
                for ref in mention_only:
                    lines.append(f"Related: {ref}")
                lines.append("")
            else:
                # Refs present but nothing resolved — fall back
                issue_ref = _build_issue_reference(project_root, spec)
                if issue_ref:
                    lines.append(f"{issue_ref}\n")
        else:
            # No frontmatter refs — use legacy lookup
            issue_ref = _build_issue_reference(project_root, spec)
            if issue_ref:
                lines.append(f"{issue_ref}\n")

    # -- Checklist -----------------------------------------------------
    lines.append("## Checklist\n")
    lines.append("- [ ] All tests pass")
    lines.append("- [ ] `ruff check` clean")
    lines.append("- [ ] `ty check` clean")
    lines.append("- [ ] `gitleaks` — no leaks")
    lines.append("- [ ] CHANGELOG.md updated")
    lines.append("")

    # -- Stats ---------------------------------------------------------
    stats = _git_diff_stats(project_root)
    commit_count = len(commits)
    if stats or commit_count:
        lines.append("## Stats\n")
        if stats:
            lines.append(f"- {stats}")
        if commit_count:
            lines.append(f"- {commit_count} commits on `{branch}`")
        lines.append("")

    return "\n".join(lines) if lines else "No description generated."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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
    """Build a clickeable URL to the spec directory.

    Checks both the active ``specs/{slug}/`` and archived
    ``specs/archive/{slug}/`` locations on disk so the URL stays valid
    after spec-reset archives the directory.

    Args:
        project_root: Root directory of the project.
        spec: Spec identifier (e.g., ``"036-platform-runbooks"``).

    Returns:
        Full URL to the spec file, or None if repo URL cannot be determined.
    """
    repo_url = _get_repo_url(project_root)
    if not repo_url:
        return None

    # Working Buffer model: spec lives at fixed path
    spec_path = ".ai-engineering/specs/spec.md"

    if "github.com" in repo_url:
        return f"{repo_url}/blob/main/{spec_path}"

    if "dev.azure.com" in repo_url:
        return f"{repo_url}?path=/{spec_path}&version=GBmain"

    return None


def _read_active_spec(project_root: Path) -> str | None:
    """Read the active spec identifier from ``specs/spec.md``.

    Extracts the ``id`` field from YAML frontmatter, or falls back
    to scanning for a ``# Spec NNN`` heading pattern.

    Args:
        project_root: Root directory of the project.

    Returns:
        Active spec identifier (e.g. ``"055"``),
        or None if no spec is active or file is missing.
    """
    spec_path = project_root / ".ai-engineering" / "specs" / "spec.md"
    if not spec_path.exists():
        return None

    try:
        text = spec_path.read_text(encoding="utf-8")
    except OSError:
        return None

    # Placeholder means no active spec
    if text.strip().startswith("# No active spec"):
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
    spec_path = project_root / ".ai-engineering" / "specs" / "spec.md"
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
    """Read ``specs/spec.md`` and extract key sections for the PR description.

    Uses the Working Buffer model: spec lives at ``specs/spec.md`` (fixed path).

    Args:
        project_root: Root directory of the project.
        spec: Spec identifier (used for logging, not path construction).

    Returns:
        Dict with ``title``, ``problem``, ``solution`` (may be empty strings).
    """
    empty: dict[str, str] = {"title": "", "problem": "", "solution": ""}
    spec_path = project_root / ".ai-engineering" / "specs" / "spec.md"
    if not spec_path.exists():
        return empty

    try:
        text = spec_path.read_text(encoding="utf-8")
    except OSError:
        return empty

    # Title from first H1: "# Spec NNN — <Title>"
    title = ""
    title_match = re.search(r"^# [^\n]+? — (.+)$", text, re.MULTILINE)
    if title_match:
        title = title_match.group(1).strip()

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
    pattern = rf"^## {heading}[ \t]*\n(.*?)(?=(?:^## )|\Z)"
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    if not match:
        return ""
    content = match.group(1).strip()
    paragraphs = content.split("\n\n")
    return paragraphs[0].strip() if paragraphs else ""


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
