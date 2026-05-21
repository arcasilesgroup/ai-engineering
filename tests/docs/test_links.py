"""Reference-link resolution + sub-005 acceptance gates for docs surface.

Per spec-131 sub-005 M7 acceptance. Walks every .md file under the
repo (excluding generated / scratch directories) and asserts:

- relative file links resolve via Path.resolve() + .exists()
- anchored links (file.md#anchor) resolve to a real heading in the
  target file (slug match)
- http(s) links optionally validated (gated by AIENG_DOCS_NETWORK=1;
  default OFF for offline / hermetic CI)

Also embeds the per-file structural assertions for the 5 sub-005
surfaces (getting-started, README, CONTRIBUTING, CHANGELOG, ai-ide-
audit) and the anonymous-content gate (D-131-15).

Skill / agent slug references (`/ai-<name>`) are checked by
tests/unit/docs/test_skill_references_exist.py — this module defers
to that test and does not re-implement.
"""

from __future__ import annotations

import functools
import os
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

# Files / dirs to exclude from the walker. Match by substring on the
# absolute path so any depth is excluded uniformly.
#
# Rationale per sub-005 plan §Out-of-scope: the walker enforces link
# integrity on contributor-facing markdown. Skips:
#   - generated payload mirrors (.github/copilot-instructions.md,
#     .gemini/, .codex/ — enforced by tools/skill_lint/md_mirror.py).
#     .agent/ (Antigravity) and .opencode/ are lean SKILL.md-only
#     mirror surfaces (scripts/sync_mirrors/{antigravity,opencode}_target.py
#     copy SKILL.md but NOT sibling reference files like discover.md /
#     sync.md / references/). Canonical SKILL.md bodies carry relative
#     sibling links that resolve under .claude/ (which IS walked) but
#     cannot resolve in a lean mirror by design — excluding them avoids
#     testing a non-contract.
#   - .ai-engineering/specs/ (working specs; upstream issues live
#     there, sub-005 cannot fix outside its allowlist)
#   - drafts, runtime, state, observations (scratch / generated)
#   - templates (bundled assets shipped to consumer projects)
EXCLUDED_PATH_FRAGMENTS = (
    "/.git/",
    "/node_modules/",
    "/.venv/",
    "/.ruff_cache/",
    "/.pytest_cache/",
    "/.mypy_cache/",
    # `.ai-engineering/` is the workspace governance root — scaffolding +
    # runtime, not contributor-facing docs. Its link integrity is enforced
    # by template tests, not by the front-door walker.
    "/.ai-engineering/",
    "/templates/",
    "/src/ai_engineering/templates/",
    "/dist/",
    "/build/",
    "/.github/ISSUE_TEMPLATE/",
    "/.github/copilot-instructions.md",
    "/.gemini/",
    "/.codex/",
    # Lean SKILL.md-only generated mirror surfaces (no sibling refs).
    "/.agent/",
    "/.opencode/",
)

# Matches inline markdown links: [text](target). Greedy on text so it
# tolerates nested brackets that github-flavoured allows.
LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)\s]+)\)")

SUB005_FILES = [
    REPO_ROOT / "docs" / "getting-started.md",
    REPO_ROOT / "README.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "CHANGELOG.md",
    REPO_ROOT / ".claude" / "skills" / "ai-ide-audit" / "SKILL.md",
    REPO_ROOT / ".claude" / "skills" / "ai-ide-audit" / "references" / "capability-matrix.md",
    REPO_ROOT / ".claude" / "skills" / "ai-ide-audit" / "references" / "evidence-collection.md",
]

# Patterns derived from operator memory feedback_anonymous_feedback.md
# (D-131-15). Each regex matches a forbidden surface.
PII_PATTERNS = [
    r"/Users/[a-z][a-z0-9_-]+/",  # macOS home paths
    r"/home/(?!runner/)[a-z][a-z0-9_-]+/",  # Linux home paths (whitelist CI runner)
    r"C:\\Users\\[A-Za-z][A-Za-z0-9_-]+\\",  # Windows home paths
    r"the operator (said|reported|noted|asked|wants|requested)",
    r"the user (said|reported|noted|asked|wants|requested)",
    r"in conversation with",
]


@functools.cache
def _walk_md_files() -> tuple[Path, ...]:
    files: list[Path] = []
    for p in REPO_ROOT.rglob("*.md"):
        s = str(p)
        if any(frag in s for frag in EXCLUDED_PATH_FRAGMENTS):
            continue
        files.append(p)
    return tuple(sorted(files))


def _slugify(heading: str) -> str:
    """GitHub-flavoured anchor slug."""
    s = heading.lower().strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"\s+", "-", s)
    return s


def _file_headings(p: Path) -> set[str]:
    headings: set[str] = set()
    if not p.exists():
        return headings
    try:
        body = p.read_text(errors="ignore")
    except OSError:
        return headings
    for line in body.splitlines():
        m = re.match(r"^#+\s+(.+?)\s*$", line)
        if m:
            headings.add(_slugify(m.group(1)))
    return headings


# ---------------------------------------------------------------------------
# Generic link walker
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "md_path",
    _walk_md_files(),
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_no_broken_links(md_path: Path) -> None:
    body = md_path.read_text(errors="ignore")
    for _text, target in LINK_RE.findall(body):
        # Skip anchors, mailto, network, badges (svg/png url at root), and
        # github issue / PR shortlinks like '#509' wrapped in markdown.
        if target.startswith(("http://", "https://", "mailto:", "tel:")):
            continue
        if target.startswith("#"):
            anchor = target.lstrip("#").lower()
            assert anchor in _file_headings(md_path), (
                f"{md_path}: anchor #{anchor} not found in own headings"
            )
            continue
        # Relative file path with optional anchor
        file_part, _, anchor = target.partition("#")
        if not file_part:
            file_part = md_path.name
        # Strip query params / fragments rare in markdown links
        file_part = file_part.split("?", 1)[0]
        resolved = (md_path.parent / file_part).resolve()
        # Allow link to a directory (rare; treat as exists)
        assert resolved.exists(), (
            f"{md_path}: link target '{target}' resolves to missing path {resolved}"
        )
        # Anchor lookups in source files are best-effort only
        # for non-markdown destinations (e.g. source code).
        if anchor and resolved.suffix == ".md":
            anchors = _file_headings(resolved)
            assert anchor.lower() in anchors, f"{md_path}: anchor #{anchor} not in {resolved}"


@pytest.mark.skipif(
    os.environ.get("AIENG_DOCS_NETWORK") != "1",
    reason="set AIENG_DOCS_NETWORK=1 to enable HTTP checks",
)
def test_http_links_resolve() -> None:
    import requests

    for md_path in _walk_md_files():
        body = md_path.read_text(errors="ignore")
        for _text, target in LINK_RE.findall(body):
            if not target.startswith(("http://", "https://")):
                continue
            r = requests.head(target, timeout=5, allow_redirects=True)
            assert r.status_code < 400, f"{md_path}: {target} returned {r.status_code}"


# ---------------------------------------------------------------------------
# T-5.A — docs/getting-started.md acceptance
# ---------------------------------------------------------------------------


def test_getting_started_absent_per_spec_136() -> None:
    """spec-136 D-136-13: docs/getting-started.md hard-deleted.

    README + `ai-eng install --help` carry the onboarding flow now.
    Asserts the file is absent so a regression accidentally re-creating
    it lights up the gate.
    """
    p = REPO_ROOT / "docs" / "getting-started.md"
    assert not p.exists(), (
        "docs/getting-started.md was hard-deleted by spec-136 D-136-13; "
        "consumer onboarding now lives in README.md + ai-eng install --help"
    )


# ---------------------------------------------------------------------------
# T-5.B — README.md rewrite acceptance
# ---------------------------------------------------------------------------


def test_readme_minimal() -> None:
    body = (REPO_ROOT / "README.md").read_text()
    # No skill list / agent list / runbook table
    assert "/ai-brainstorm | Define" not in body
    assert "| brainstorm, plan" not in body
    assert "| Agent | Role |" not in body
    # No legacy 7-step chain
    assert "ai-start --> /ai-brainstorm --> /ai-plan --> /ai-build" not in body, (
        "Legacy 7-step chain still present in README"
    )
    assert "ai-verify --> /ai-pr" not in body
    # No upgrade-spec section
    assert "## Upgrade reference" not in body
    # Required links
    assert "AGENTS.md" in body
    assert "CONSTITUTION.md" in body
    assert "CHANGELOG.md" in body
    assert "CONTRIBUTING.md" in body
    # spec-136 D-136-13: docs/getting-started.md hard-deleted; README
    # carries the install/onboarding flow inline now.
    assert "docs/getting-started.md" not in body, (
        "docs/getting-started.md was deleted; README must not link to it"
    )
    # Length cap
    line_count = len(body.splitlines())
    assert line_count <= 120, f"README too long: {line_count} lines (cap 120)"
    # The deleted root-level GETTING_STARTED.md must be gone
    assert not (REPO_ROOT / "GETTING_STARTED.md").exists(), (
        "Legacy GETTING_STARTED.md still present at repo root"
    )


# ---------------------------------------------------------------------------
# T-5.C — CONTRIBUTING.md update acceptance
# ---------------------------------------------------------------------------


def test_contributing_minimal() -> None:
    body = (REPO_ROOT / "CONTRIBUTING.md").read_text()
    # No 7-step chain duplication
    assert "ai-start --> /ai-brainstorm --> /ai-plan" not in body
    # Required sections
    for section in (
        "## Development setup",
        "## Code style",
        "## Testing",
        "## Pull request process",
        "## Project structure",
    ):
        assert section in body, f"missing section {section}"
    # Project structure is a paragraph, not a code-fenced tree
    structure_idx = body.index("## Project structure")
    next_section = body.find("\n## ", structure_idx + 1)
    structure_block = body[structure_idx : next_section if next_section != -1 else None]
    assert "├──" not in structure_block, "CONTRIBUTING.md still carries the legacy code-fenced tree"
    # Link to AGENTS.md for canonical content
    assert "AGENTS.md" in body
    # Length cap
    line_count = len(body.splitlines())
    assert line_count <= 150, f"CONTRIBUTING too long: {line_count} lines"


# ---------------------------------------------------------------------------
# T-5.D — CHANGELOG.md spec-131 entry acceptance
# ---------------------------------------------------------------------------


def test_changelog_spec_131_entry() -> None:
    body = (REPO_ROOT / "CHANGELOG.md").read_text()
    unreleased_idx = body.index("## [Unreleased]")
    spec_131_idx = body.index("### spec-131 — DX Excellence Refactor")
    # spec-131 entry sits inside [Unreleased]
    assert unreleased_idx < spec_131_idx
    # spec-131 is ABOVE the older spec-131 S1 entry (newest at top of unreleased)
    spec_131_s1_idx = body.index("### spec-131 S1 — Markdown Canon Reset")
    assert spec_131_idx < spec_131_s1_idx, (
        "spec-131 summary entry must sit above the spec-131 S1 sub-entry"
    )
    # Block contents
    spec_131_block = body[spec_131_idx:spec_131_s1_idx]
    block_lower = spec_131_block.lower()
    assert "byte-equivalent" in block_lower, "byte-equivalent missing"
    assert "CONSTITUTION" in spec_131_block, "CONSTITUTION reference missing"
    assert "/ai-build" in spec_131_block, "/ai-build reference missing"
    assert "/ai-autopilot" in spec_131_block, "/ai-autopilot reference missing"
    assert "trusted-script lane" in block_lower or "trusted script" in block_lower
    assert "Antigravity" in spec_131_block, "Antigravity reference missing"
    assert "effort:" in spec_131_block or "model_tier:" in spec_131_block
    # Non-Goal #10: no promises of compat shims. The block may explain
    # the anti-shim policy ("no compat shims", "without compat shims")
    # but must not promise any. Catch shipped-shim phrasing only.
    for promise in (
        "added a compat shim",
        "ships a compat shim",
        "shipped a compat shim",
        "backwards-compatibility shim added",
        "added a backwards-compat shim",
    ):
        assert promise not in block_lower, (
            f"CHANGELOG spec-131 block promises a compat shim: '{promise}'"
        )


# ---------------------------------------------------------------------------
# T-5.E — Antigravity row in /ai-ide-audit capability matrix
# ---------------------------------------------------------------------------


def test_ai_ide_audit_antigravity_row() -> None:
    matrix_md = (
        REPO_ROOT / ".claude" / "skills" / "ai-ide-audit" / "references" / "capability-matrix.md"
    ).read_text()
    assert "Antigravity" in matrix_md
    assert "GEMINI.md" in matrix_md
    assert "AGENTS.md" in matrix_md
    assert "advisory" in matrix_md.lower()


def test_ai_ide_audit_skill_lists_antigravity() -> None:
    skill_md = (REPO_ROOT / ".claude" / "skills" / "ai-ide-audit" / "SKILL.md").read_text()
    assert "antigravity" in skill_md.lower(), "canonical SKILL.md missing Antigravity"


def test_ai_ide_audit_mirrors_carry_antigravity() -> None:
    for mirror in (".github", ".codex", ".gemini"):
        skill_md = (REPO_ROOT / mirror / "skills" / "ai-ide-audit" / "SKILL.md").read_text()
        assert "antigravity" in skill_md.lower(), f"{mirror} mirror SKILL.md missing Antigravity"


def test_ai_ide_audit_evidence_collection_lists_antigravity() -> None:
    ev_md = (
        REPO_ROOT / ".claude" / "skills" / "ai-ide-audit" / "references" / "evidence-collection.md"
    ).read_text()
    assert "Antigravity" in ev_md, "evidence-collection missing Antigravity surface row"


# ---------------------------------------------------------------------------
# T-5.G — Anonymous-content review gate (D-131-15)
# ---------------------------------------------------------------------------


def _scope_changelog_to_spec131(body: str) -> str:
    """Restrict the PII scan to the spec-131 block only.

    Older CHANGELOG entries are out of sub-005 scope and may legitimately
    reference older path styles or third-party project names.
    """
    try:
        start = body.index("### spec-131 — DX Excellence Refactor")
    except ValueError:
        return ""
    # Scope ends at the next sibling spec entry (### spec- prefix)
    after = body[start + 1 :]
    m = re.search(r"\n### (?:spec-(?!131\s—)|\[)", after)
    end = start + 1 + (m.start() if m else len(after))
    return body[start:end]


@pytest.mark.parametrize(
    "path",
    SUB005_FILES,
    ids=lambda p: str(p.relative_to(REPO_ROOT)),
)
def test_anonymous_content(path: Path) -> None:
    if not path.exists():
        pytest.skip(f"{path} not yet created — earlier task pending")
    body = path.read_text()
    if path.name == "CHANGELOG.md":
        body = _scope_changelog_to_spec131(body)
    for pat in PII_PATTERNS:
        m = re.search(pat, body, re.IGNORECASE)
        assert m is None, (
            f"{path}: anonymous-content violation matched /{pat}/ — "
            f"found '{m.group(0) if m else ''}'"
        )


# ---------------------------------------------------------------------------
# T-5.J — North Star preamble in sub-005 plan
# ---------------------------------------------------------------------------


def test_sub005_plan_has_north_star_preamble() -> None:
    p = REPO_ROOT / ".ai-engineering" / "runtime" / "autopilot" / "sub-005" / "plan.md"
    if not p.exists():
        pytest.skip("sub-005 plan not present in this checkout")
    body = p.read_text()
    assert "North Star" in body or "north star" in body.lower()
    head = "\n".join(body.splitlines()[:80])
    assert "north star" in head.lower(), (
        "North Star preamble must appear in the first 80 lines of plan.md"
    )


# ---------------------------------------------------------------------------
# T-5.K — Canonical spec slot verification
# ---------------------------------------------------------------------------


def test_spec_canonical_slot_carries_spec_marker() -> None:
    """The canonical slot must always carry a `spec: spec-NNN` marker.

    spec-136 D-136-01 succeeded spec-132 in the slot. The contract is
    "any active spec lives here", not "spec-132 specifically".
    """
    p = REPO_ROOT / ".ai-engineering" / "specs" / "spec.md"
    body = p.read_text()
    import re

    assert re.search(r"^spec: spec-\d+", body, re.MULTILINE), (
        "canonical slot must declare an active spec via `spec: spec-NNN`"
    )
    spec_131_archive = (
        REPO_ROOT / ".ai-engineering" / "specs" / "archive" / "spec-131-dx-excellence-refactor.md"
    )
    assert spec_131_archive.exists(), "spec-131 archive missing adjacent to canonical slot"
