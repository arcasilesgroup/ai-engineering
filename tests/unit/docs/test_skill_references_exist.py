"""CI guard for skill-reference integrity in markdown docs.

Per spec-122-d D-122-31: every `/ai-<name>` reference in a markdown
document must resolve to a real skill at `.claude/skills/ai-<name>/`.
Ghost references (`/ai-implement`, `/ai-eval-gate`, `/ai-eval`) are
the canary failure mode -- a skill was renamed or deleted but the
docs still cite the old name.

Scope:
- Walks markdown files at the repo root (`CLAUDE.md`, `AGENTS.md`,
  `README.md`, `CONSTITUTION.md`, `GEMINI.md`).
- Walks `.github/copilot-instructions.md`.
- Walks `docs/` for human-facing documentation.
- Excludes `.ai-engineering/specs/` (historical specs may reference
  deleted skills as past state).
- Excludes `CHANGELOG.md` (historical entries by design).
- Excludes mirror trees (.gemini/, .codex/, .github/skills/) -- they
  are derived from .claude/skills/ and re-validated by sync_mirrors.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

# Files / directories to scan.
SCAN_PATHS = [
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONSTITUTION.md",
    REPO_ROOT / "GEMINI.md",
    REPO_ROOT / ".github" / "copilot-instructions.md",
]
SCAN_DIRS = [
    REPO_ROOT / "docs",
]

# Exclusions: paths whose contents legitimately reference deleted skills.
EXCLUDED_FILES = {
    REPO_ROOT / "CHANGELOG.md",
}
EXCLUDED_PATH_FRAGMENTS = (
    "/.ai-engineering/specs/",
    "/.git/",
    "/node_modules/",
    "/.venv/",
    "/.ruff_cache/",
)

# Match `/ai-foo`, `/ai-foo-bar`, etc. used as a skill invocation.
# Excludes:
#   - `/ai-engineering` (the framework name itself, not a skill)
#   - paths like `/ai-engineering/foo` (URL fragments)
# Capture the first segment so we can blacklist non-skill names.
SKILL_REF = re.compile(r"/ai-([a-z][a-z0-9-]*)(?![a-z0-9])")
NON_SKILL_NAMES = frozenset(
    {
        "engineering",  # the framework name, not a skill
    }
)


def _collect_target_files() -> list[Path]:
    files: list[Path] = []
    for p in SCAN_PATHS:
        if p.is_file():
            files.append(p)
    for d in SCAN_DIRS:
        if d.is_dir():
            files.extend(d.rglob("*.md"))
    return [
        f
        for f in files
        if f not in EXCLUDED_FILES and not any(frag in str(f) for frag in EXCLUDED_PATH_FRAGMENTS)
    ]


def _existing_skill_names() -> set[str]:
    """Set of skill names (without `ai-` prefix) under `.claude/skills/`."""
    names: set[str] = set()
    if not SKILLS_DIR.is_dir():
        return names
    for entry in SKILLS_DIR.iterdir():
        if not entry.is_dir():
            continue
        # Only count dirs with a SKILL.md (not _shared/, not stub dirs).
        if (entry / "SKILL.md").is_file() and entry.name.startswith("ai-"):
            names.add(entry.name[len("ai-") :])
    return names


def test_all_skill_references_resolve() -> None:
    """Every `/ai-<name>` reference resolves to `.claude/skills/ai-<name>/`."""
    skills = _existing_skill_names()
    files = _collect_target_files()
    assert files, "No target files found -- scan paths misconfigured?"
    assert skills, "No skills found under .claude/skills/ -- check SKILLS_DIR."

    bad: list[tuple[Path, int, str]] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            for m in SKILL_REF.finditer(line):
                name = m.group(1)
                if name in NON_SKILL_NAMES:
                    continue
                if name not in skills:
                    bad.append((f, lineno, m.group(0)))

    if bad:
        sample = "\n".join(f"  {b[0].relative_to(REPO_ROOT)}:{b[1]}: {b[2]}" for b in bad[:10])
        pytest.fail(
            f"Found {len(bad)} ghost skill references:\n{sample}\n"
            f"Existing skills: {sorted(skills)[:10]}..."
        )


def test_scan_finds_canonical_files() -> None:
    """Sanity check: the scan picks up CLAUDE.md / AGENTS.md."""
    files = _collect_target_files()
    file_names = {f.name for f in files}
    assert "CLAUDE.md" in file_names, "CLAUDE.md must be in scan set"
    assert "AGENTS.md" in file_names, "AGENTS.md must be in scan set"


def test_skill_dir_has_skills() -> None:
    """`.claude/skills/` actually contains skill dirs (catches mis-rooted test)."""
    skills = _existing_skill_names()
    assert len(skills) >= 30, (
        f"Expected at least 30 skills under .claude/skills/, found {len(skills)}"
    )
