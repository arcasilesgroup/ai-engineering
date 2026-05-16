#!/usr/bin/env python3
"""apply_effort_model_tier — spec-131 S3 (sub-003) frontmatter migration.

Walks every IDE mirror (``.claude`` / ``.codex`` / ``.gemini`` /
``.github``) and edits each ``SKILL.md`` frontmatter to:

* Replace legacy ``effort: medium|high|max`` with the policy-mapped
  value from ``docs/model-dispatch-policy.md``.
* Insert ``model_tier:`` line after ``effort:`` when absent; replace
  when present.

Usage::

    # Dry-run (CI safety / idempotency proof)
    python .ai-engineering/scripts/spec-131/apply_effort_model_tier.py --check

    # Write (one-shot migration)
    python .ai-engineering/scripts/spec-131/apply_effort_model_tier.py

Idempotency:
    Running the script twice in write mode produces no further file
    changes — a third run is the same as a second. This is what the
    integration test asserts.

Allow-list:
    ``.github/skills/`` deliberately omits ``ai-analyze-permissions``.
    The script tolerates this gap (does not regenerate the missing
    mirror).
"""

from __future__ import annotations

import argparse
import importlib
import re
import sys
from pathlib import Path

# Re-use the policy loader from the effort lint check so the SSOT lives
# in exactly one place (DRY §10.4). The script is invoked from the repo
# root so ``tools/`` resolves via ``sys.path``. We defer the import via
# ``importlib`` instead of a top-level ``from … import …`` because
# ``tools/`` is not on ``sys.path`` at module-load time — the path
# extension below must run first. Using ``importlib`` keeps the import
# call at module scope (no E402 trigger) and avoids the no-suppression
# violation flagged in spec-131 closure sweep.
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "tools"))

load_policy = importlib.import_module("skill_lint.checks.effort").load_policy

# IDE mirrors walked by the script. Order matters only for log
# determinism — the migration shape is identical per mirror.
_MIRRORS = (".claude", ".codex", ".gemini", ".github")


_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
_EFFORT_LINE_RE = re.compile(r"^effort:\s*.+?\s*$", re.MULTILINE)
_MODEL_TIER_LINE_RE = re.compile(r"^model_tier:\s*.+?\s*$", re.MULTILINE)


def _migrate_frontmatter(text: str, *, effort: str, tier: str) -> str:
    """Return ``text`` with ``effort:`` + ``model_tier:`` aligned to policy.

    Strategy:

    1. Locate the YAML frontmatter via ``_FRONTMATTER_RE``.
    2. Substitute the ``effort:`` line (or insert one before the closing
       ``---`` if absent).
    3. Substitute the ``model_tier:`` line (or insert it directly after
       the ``effort:`` line if absent).

    Result is byte-equivalent to the input when both fields already match
    the policy — which is the idempotency contract.
    """
    fm_match = _FRONTMATTER_RE.search(text)
    if not fm_match:
        # No frontmatter — caller is expected to skip the file rather
        # than ship malformed YAML. Return text unchanged.
        return text
    fm_block = fm_match.group(1)

    # ── effort: line ────────────────────────────────────────────────
    new_effort_line = f"effort: {effort}"
    if _EFFORT_LINE_RE.search(fm_block):
        fm_block = _EFFORT_LINE_RE.sub(new_effort_line, fm_block, count=1)
    else:
        # Append before closing fence (after the last frontmatter line).
        fm_block = fm_block.rstrip() + "\n" + new_effort_line

    # ── model_tier: line ────────────────────────────────────────────
    new_tier_line = f"model_tier: {tier}"
    if _MODEL_TIER_LINE_RE.search(fm_block):
        fm_block = _MODEL_TIER_LINE_RE.sub(new_tier_line, fm_block, count=1)
    else:
        # Insert immediately after the ``effort:`` line so the two fields
        # stay adjacent.
        fm_block = _EFFORT_LINE_RE.sub(
            f"{new_effort_line}\n{new_tier_line}",
            fm_block,
            count=1,
        )

    new_fm = f"---\n{fm_block}\n---"
    return text[: fm_match.start()] + new_fm + text[fm_match.end() :]


def _process_skill(
    skill_md: Path,
    policy: dict[str, tuple[str, str]],
    *,
    check_only: bool,
) -> bool:
    """Apply (or report) the migration for a single SKILL.md.

    Returns ``True`` when the file requires (or required) a write.
    Falsy when the file already matches the policy. Files for skills
    not listed in the policy are silently skipped so the script never
    invents a mapping.
    """
    skill_slug = skill_md.parent.name
    if skill_slug not in policy:
        return False
    effort, tier = policy[skill_slug]
    original = skill_md.read_text(encoding="utf-8")
    migrated = _migrate_frontmatter(original, effort=effort, tier=tier)
    if migrated == original:
        return False
    if not check_only:
        skill_md.write_text(migrated, encoding="utf-8")
    return True


def apply_migration(
    repo_root: Path,
    policy_path: Path,
    *,
    check_only: bool = False,
) -> list[Path]:
    """Walk every IDE mirror and apply the migration.

    Returns the list of ``SKILL.md`` paths that needed (or would have
    needed, in ``check_only`` mode) an update. Empty list = idempotent.

    The signature deliberately accepts ``repo_root`` + ``policy_path``
    (paths, not loaders) so the unit tests can stage a synthetic tree.
    """
    policy = load_policy(policy_path)
    if not policy:
        msg = f"empty policy at {policy_path}"
        raise FileNotFoundError(msg)
    pending: list[Path] = []
    for mirror in _MIRRORS:
        skills_dir = repo_root / mirror / "skills"
        if not skills_dir.is_dir():
            continue
        for skill_dir in sorted(skills_dir.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.is_file():
                continue
            if _process_skill(skill_md, policy, check_only=check_only):
                pending.append(skill_md)
    return pending


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="apply_effort_model_tier")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=_REPO_ROOT,
        help="Path to the repo root (default: detected from script location).",
    )
    parser.add_argument(
        "--policy-path",
        type=Path,
        default=_REPO_ROOT / "docs" / "model-dispatch-policy.md",
        help="Path to docs/model-dispatch-policy.md.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Dry-run: report pending updates without writing.",
    )
    args = parser.parse_args(argv)
    pending = apply_migration(args.repo_root, args.policy_path, check_only=args.check)
    if pending:
        verb = "would update" if args.check else "updated"
        for path in pending:
            sys.stdout.write(f"{verb}: {path.relative_to(args.repo_root)}\n")
        sys.stdout.write(f"{verb}: {len(pending)} SKILL.md file(s)\n")
        # In --check mode, exit 1 when changes are pending so CI can
        # gate on idempotency. In write mode, the migration is the
        # success path — exit 0.
        return 1 if args.check else 0
    sys.stdout.write("no pending changes — policy is in sync\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
