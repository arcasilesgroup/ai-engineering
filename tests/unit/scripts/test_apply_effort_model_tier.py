"""apply_effort_model_tier migration script — spec-131 S3 (sub-003 T-3.5 RED).

The script walks every IDE mirror (.claude / .codex / .agents / .github)
and edits each SKILL.md frontmatter in place:

* Replace legacy ``effort: medium|high|max`` with the policy-mapped
  value from ``.ai-engineering/reference/model-dispatch-policy.md``.
* Insert ``model_tier:`` line after ``effort:`` when absent; replace
  when present.
* No-op when the file already matches the policy (idempotent).

The ``--check`` (dry-run) mode prints the diff to stdout and never
writes. Re-running with no flags is also idempotent: a second
invocation produces no further changes.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_script() -> object:
    """Import the migration script as a module despite the dotted directory.

    ``.ai-engineering/scripts/spec-131/apply_effort_model_tier.py`` cannot
    be imported via the normal package path because the directory carries
    a hyphen. Use ``importlib.util`` to load it directly so the tests
    exercise the real implementation rather than a stub.
    """
    repo_root = Path(__file__).resolve().parents[3]
    script_path = (
        repo_root / ".ai-engineering" / "scripts" / "spec-131" / "apply_effort_model_tier.py"
    )
    spec = importlib.util.spec_from_file_location("apply_effort_model_tier", script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {script_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["apply_effort_model_tier"] = module
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _write_skill_with_legacy(skill_dir: Path, *, legacy_effort: str = "medium") -> Path:
    skill_dir.mkdir(parents=True, exist_ok=True)
    md = skill_dir / "SKILL.md"
    md.write_text(
        f"---\nname: {skill_dir.name}\ndescription: fixture\neffort: {legacy_effort}\n"
        "---\n\n# Body\n",
        encoding="utf-8",
    )
    return md


def _write_policy(path: Path, rows: list[tuple[str, str, str]]) -> Path:
    body = [
        "# Policy",
        "",
        "## Mapping",
        "",
        "| Skill | effort | model_tier | Rationale |",
        "|---|---|---|---|",
    ]
    for skill, effort, tier in rows:
        body.append(f"| {skill} | {effort} | {tier} | n/a |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(body) + "\n", encoding="utf-8")
    return path


def _build_tree(tmp_path: Path) -> tuple[Path, Path]:
    """Build a synthetic 4-mirror tree under ``tmp_path``.

    Returns ``(repo_root, policy_path)``. The ``.github`` mirror omits
    ``ai-claude-only`` to simulate the live gap.
    """
    repo_root = tmp_path / "repo"
    for mirror in [".claude", ".codex", ".agents", ".github"]:
        for skill in ["ai-demo", "ai-claude-only"]:
            if mirror == ".github" and skill == "ai-claude-only":
                continue
            _write_skill_with_legacy(repo_root / mirror / "skills" / skill)
    policy = _write_policy(
        repo_root / "docs" / "model-dispatch-policy.md",
        [
            ("ai-demo", "mid", "sonnet"),
            ("ai-claude-only", "high", "opus"),
        ],
    )
    return repo_root, policy


# ---------------------------------------------------------------------------
# Test 1 — dry-run mode does not write.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_dry_run_does_not_write(tmp_path: Path) -> None:
    repo_root, policy = _build_tree(tmp_path)
    mod = _load_script()
    skill_md = repo_root / ".claude" / "skills" / "ai-demo" / "SKILL.md"
    original = skill_md.read_text(encoding="utf-8")
    pending = mod.apply_migration(repo_root, policy, check_only=True)
    assert pending, "dry-run should surface pending changes"
    assert skill_md.read_text(encoding="utf-8") == original, "dry-run must not modify any file"


# ---------------------------------------------------------------------------
# Test 2 — write mode applies the migration.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_write_mode_applies_migration(tmp_path: Path) -> None:
    repo_root, policy = _build_tree(tmp_path)
    mod = _load_script()
    mod.apply_migration(repo_root, policy, check_only=False)
    skill_md = repo_root / ".claude" / "skills" / "ai-demo" / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    assert "effort: mid" in content, content
    assert "model_tier: sonnet" in content, content
    assert "effort: medium" not in content, "legacy vocabulary must be replaced"


# ---------------------------------------------------------------------------
# Test 3 — write mode is idempotent (second run is a no-op).
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_write_mode_is_idempotent(tmp_path: Path) -> None:
    repo_root, policy = _build_tree(tmp_path)
    mod = _load_script()
    mod.apply_migration(repo_root, policy, check_only=False)
    # Capture the state after the first migration.
    after_first = {p: p.read_text(encoding="utf-8") for p in repo_root.rglob("SKILL.md")}
    pending = mod.apply_migration(repo_root, policy, check_only=False)
    assert not pending, "second run must report no pending changes"
    for p, text in after_first.items():
        assert p.read_text(encoding="utf-8") == text, f"{p} changed on second run"


# ---------------------------------------------------------------------------
# Test 4 — github mirror gap (ai-claude-only absence) tolerated.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_github_mirror_gap_tolerated(tmp_path: Path) -> None:
    repo_root, policy = _build_tree(tmp_path)
    mod = _load_script()
    mod.apply_migration(repo_root, policy, check_only=False)
    gap_path = repo_root / ".github" / "skills" / "ai-claude-only"
    assert not gap_path.exists(), "script must not regenerate the github gap"


# ---------------------------------------------------------------------------
# Test 5 — model_tier insertion happens when absent.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_model_tier_inserted_when_absent(tmp_path: Path) -> None:
    repo_root, policy = _build_tree(tmp_path)
    mod = _load_script()
    mod.apply_migration(repo_root, policy, check_only=False)
    skill_md = repo_root / ".claude" / "skills" / "ai-demo" / "SKILL.md"
    content = skill_md.read_text(encoding="utf-8")
    # ``model_tier:`` must appear adjacent to ``effort:`` (post-effort
    # ordering preserved by the script).
    lines = content.splitlines()
    effort_idx = next(i for i, ln in enumerate(lines) if ln.startswith("effort:"))
    assert lines[effort_idx + 1].startswith("model_tier:"), lines


# ---------------------------------------------------------------------------
# Test 6 — pre-existing model_tier value is updated when policy disagrees.
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_existing_model_tier_value_aligned_to_policy(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    skill_dir = repo_root / ".claude" / "skills" / "ai-demo"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: ai-demo\ndescription: fixture\neffort: high\nmodel_tier: opus\n---\n\n# Body\n",
        encoding="utf-8",
    )
    policy = _write_policy(
        repo_root / "docs" / "model-dispatch-policy.md",
        [("ai-demo", "mid", "sonnet")],
    )
    mod = _load_script()
    mod.apply_migration(repo_root, policy, check_only=False)
    content = (skill_dir / "SKILL.md").read_text(encoding="utf-8")
    assert "effort: mid" in content
    assert "model_tier: sonnet" in content
    assert "effort: high" not in content
    assert "model_tier: opus" not in content
