"""spec-139 M8 D-139-06 regression guard — compose determinism.

Forbids the two residual LLM hot-path patterns from re-entering the
committed skill corpus:

1. `commit_compose.py` invocations WITHOUT a `--desc` flag. The legacy
   `<DESC>` placeholder fallback is deprecated for the canonical chain
   (`/ai-commit`, `/ai-build`, `/ai-autopilot`, `/ai-pr`); the chain
   must derive `--desc` deterministically from the active plan task
   title.
2. `pr_body_compose.py` invocations WITH `--bullets-prompt` as a
   hard-coded command line in skill markdown. The summary section is
   now sourced from spec.md frontmatter `summary:` and the LLM call is
   only allowed as a documented legacy fallback for specs that predate
   the field.

Scope of the scan covers every committed skill markdown surface plus
the project-template mirrors so a new IDE adapter cannot ship a
regression silently.

This test is intentionally a grep — the cost of the guard must stay
near zero so it always runs in CI even on tiny diffs.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# Repo root resolves to ``/.../ai-engineering`` (the tests live at
# ``tests/unit/skills/test_*.py``).
REPO_ROOT = Path(__file__).resolve().parents[3]

# Every committed skill surface plus the project templates. Each entry
# is a directory root; the scanner walks `*.md` recursively. Missing
# directories are tolerated so partial IDE rollouts do not break CI.
# spec-201 D-201-04: skill trees collapse to .claude and .agents only.
SKILL_ROOTS = [
    REPO_ROOT / ".claude" / "skills",
    REPO_ROOT / ".agents" / "skills",
    REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / ".claude" / "skills",
    REPO_ROOT / "src" / "ai_engineering" / "templates" / "project" / ".agents" / "skills",
]

# Pattern 1: an invocation of ``commit_compose.py`` followed (on the
# same logical command line) by no ``--desc`` flag. Skill markdown
# wraps commands in fenced code blocks or inline backticks; we walk
# line-by-line and consider continuations within a single invocation.
COMMIT_COMPOSE_RE = re.compile(r"commit_compose\.py[^`\n]*")

# Pattern 2: ``pr_body_compose.py`` invocations that hard-code
# ``--bullets-prompt`` as a flag (regardless of value or placeholder).
PR_BODY_COMPOSE_BAD_RE = re.compile(r"pr_body_compose\.py[^`\n]*--bullets-prompt")

# Tokens that mark a documented legacy fallback discussion rather than
# a live invocation. When a line contains any of these tokens we skip
# the regression check — the surrounding prose is teaching the operator
# about the deprecated path, not invoking it.
LEGACY_DISCUSSION_TOKENS = (
    "legacy",
    "deprecated",
    "fall back",
    "fallback",
    "advisory warning",
    "predate",
    "only fires",
    "DO NOT pass",
    "do NOT pass",
    "Never rely",
    "never rely",
    "no longer fills",
)


def _iter_skill_markdown() -> list[Path]:
    """Return every `*.md` file under the configured skill roots."""
    files: list[Path] = []
    for root in SKILL_ROOTS:
        if not root.is_dir():
            continue
        files.extend(sorted(root.rglob("*.md")))
    return files


def _line_is_legacy_discussion(line: str) -> bool:
    """True when the line is teaching about the legacy path, not invoking it."""
    return any(token in line for token in LEGACY_DISCUSSION_TOKENS)


def test_commit_compose_invocations_pass_desc() -> None:
    """Every committed `commit_compose.py` invocation must carry `--desc`."""
    violations: list[tuple[Path, int, str]] = []
    for md_file in _iter_skill_markdown():
        try:
            text = md_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            match = COMMIT_COMPOSE_RE.search(line)
            if not match:
                continue
            invocation = match.group(0)
            if "--desc" in invocation:
                continue
            if _line_is_legacy_discussion(line):
                continue
            violations.append((md_file, lineno, line.strip()))

    if violations:
        unique_files = sorted({str(v[0].relative_to(REPO_ROOT)) for v in violations})
        sample = "\n".join(
            f"  {v[0].relative_to(REPO_ROOT)}:{v[1]}: {v[2][:140]}" for v in violations[:5]
        )
        pytest.fail(
            f"Found {len(violations)} commit_compose.py invocation(s) without "
            f"--desc across {len(unique_files)} file(s) (spec-139 M8 D-139-06).\n"
            f"First 5 violators:\n{sample}\n\n"
            "Fix: derive --desc deterministically from the active plan.md task "
            "title (see .claude/skills/ai-commit/SKILL.md for the helper snippet)."
        )


def test_pr_body_compose_does_not_hardcode_bullets_prompt() -> None:
    """`pr_body_compose.py` must not be invoked with `--bullets-prompt` in skill md.

    The summary section is now sourced from spec.md frontmatter
    ``summary:``. The ``--bullets-prompt`` flag remains on the script
    for legacy specs that predate the field but skill markdown must
    not bake it into the canonical invocation.
    """
    violations: list[tuple[Path, int, str]] = []
    for md_file in _iter_skill_markdown():
        try:
            text = md_file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not PR_BODY_COMPOSE_BAD_RE.search(line):
                continue
            if _line_is_legacy_discussion(line):
                continue
            violations.append((md_file, lineno, line.strip()))

    if violations:
        unique_files = sorted({str(v[0].relative_to(REPO_ROOT)) for v in violations})
        sample = "\n".join(
            f"  {v[0].relative_to(REPO_ROOT)}:{v[1]}: {v[2][:140]}" for v in violations[:5]
        )
        pytest.fail(
            f"Found {len(violations)} pr_body_compose.py invocation(s) with "
            f"--bullets-prompt across {len(unique_files)} file(s) "
            "(spec-139 M8 D-139-06).\n"
            f"First 5 violators:\n{sample}\n\n"
            "Fix: remove --bullets-prompt; the Summary section is now sourced "
            "from spec.md frontmatter `summary:` (see "
            ".ai-engineering/reference/spec-schema.md)."
        )


def test_active_spec_has_summary_field() -> None:
    """The active `.ai-engineering/specs/spec.md` must declare `summary:`.

    Defence-in-depth against accidental approval of a spec without the
    field during the soft-rollout window. The spec_lint advisory will
    flip to BLOCKER on 2026-06-16; this test catches drift before then.
    """
    spec_path = REPO_ROOT / ".ai-engineering" / "specs" / "spec.md"
    if not spec_path.is_file():
        pytest.skip("no active spec.md in repo")
    text = spec_path.read_text(encoding="utf-8")
    if text.lstrip().startswith("# No active spec"):
        pytest.skip("active spec.md is the placeholder")
    # Walk only the leading frontmatter block.
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        pytest.fail("active spec.md is missing its YAML frontmatter fence")
    has_summary = False
    for raw in lines[1:]:
        if raw.strip() == "---":
            break
        if raw.lstrip().startswith("summary:"):
            value = raw.partition(":")[2].strip()
            if value:
                has_summary = True
            break
    assert has_summary, (
        "active .ai-engineering/specs/spec.md must declare a non-empty `summary:` "
        "field in frontmatter (spec-139 M8 D-139-06; see "
        ".ai-engineering/reference/spec-schema.md)."
    )
