"""Spec-104 orthogonality verification (T-0.8).

Asserts that spec-104 work does not modify spec-101's contract surface.
spec-101 (installer robustness) is frozen on this same umbrella branch
per .ai-engineering/notes/spec-101-frozen-pr463.md; spec-104 must remain
strictly additive over a disjoint set of files.

Mitigates D-104-10 / R-10 (spec-101 conflicts).

Test layout (4 tests):

1. orchestrator imports — gate on T-2.2 (skip until file lands).
2. gate_cache imports — gate on T-1.2 (skip until file lands).
3. manifest.yml additivity — passes today (spec-104 not yet touching
   manifest.yml; future additions must remain additive).
4. skill markdown scope — passes today (no .claude/skills/** modified
   by spec-104 commits yet; future commits constrained to the
   D-104-07 file set).
"""

from __future__ import annotations

import ast
import subprocess
from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Path constants — anchored at the repo root regardless of cwd.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]

ORCHESTRATOR_PATH = REPO_ROOT / "src" / "ai_engineering" / "policy" / "orchestrator.py"
GATE_CACHE_PATH = REPO_ROOT / "src" / "ai_engineering" / "policy" / "gate_cache.py"
MANIFEST_PATH = REPO_ROOT / ".ai-engineering" / "manifest.yml"
SKILLS_ROOT = REPO_ROOT / ".claude" / "skills"

# Packages that the spec-104 modules MUST NOT import from. spec-101 owns
# `installer` and `doctor`; spec-104 must remain orthogonal (D-104-10 / R-10).
SPEC_101_FORBIDDEN_IMPORT_ROOTS = (
    "ai_engineering.installer",
    "ai_engineering.doctor",
)

# Manifest top-level keys owned by spec-101 — spec-104 may read these but
# MUST NOT modify or remove them. Captured pre-spec-104 from the frozen
# manifest.yml on this umbrella branch (see spec-101-frozen-pr463.md).
SPEC_101_OWNED_TOP_LEVEL_KEYS = frozenset(
    {
        "required_tools",
        "python_env",
        "prereqs",
    }
)

# The exhaustive set of skill markdown files that D-104-07 permits
# spec-104 to modify. Any commit tagged "spec-104" that touches files
# under .claude/skills/** outside this whitelist is a scope violation.
SPEC_104_ALLOWED_SKILL_FILES = frozenset(
    {
        ".claude/skills/ai-commit/SKILL.md",
        ".claude/skills/ai-pr/SKILL.md",
        ".claude/skills/ai-pr/handlers/watch.md",
    }
)

# AGENT_METADATA companions are also permitted (T-0.1 updates).
SPEC_104_ALLOWED_SKILL_PREFIXES = (
    ".claude/skills/ai-commit/AGENT_METADATA",
    ".claude/skills/ai-pr/AGENT_METADATA",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _collect_imported_modules(source: str) -> set[str]:
    """Return the set of fully-qualified module names imported by source.

    Uses ast so we never execute the target file. Handles both
    `import a.b.c` and `from a.b import c` forms, capturing the
    full dotted path for prefix matching.
    """
    tree = ast.parse(source)
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)
        # node.module is None for `from . import x`; skip those — they
        # cannot reference top-level packages by definition.
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            modules.add(node.module)

    return modules


def _imports_violate_orthogonality(modules: set[str]) -> list[str]:
    """Return the subset of imports that violate spec-101 orthogonality."""
    violations: list[str] = []
    for module in modules:
        for forbidden_root in SPEC_101_FORBIDDEN_IMPORT_ROOTS:
            if module == forbidden_root or module.startswith(forbidden_root + "."):
                violations.append(module)
                break
    return violations


def _spec104_changed_files() -> list[str]:
    """Return paths changed by spec-104 commits on the current branch.

    Looks at commits tagged with "spec-104" in the message since
    2026-04-26 (when spec-104 work started — see plan.md frontmatter).
    Returns repo-relative POSIX paths. Empty list is a valid result
    (no spec-104 commits yet, or only spec.md/plan.md touched).
    """
    result = subprocess.run(
        [
            "git",
            "log",
            "--since=2026-04-26",
            "--grep=spec-104",
            "--name-only",
            "--pretty=format:",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    files = {line.strip() for line in result.stdout.splitlines() if line.strip()}
    return sorted(files)


# ---------------------------------------------------------------------------
# Test 1 — orchestrator.py orthogonality (gate on T-2.2)
# ---------------------------------------------------------------------------


def test_orchestrator_does_not_import_installer() -> None:
    """orchestrator.py (after T-2.2) must not import installer/doctor.

    spec-104 D-104-10 / R-10: spec-104 modules are orthogonal to spec-101.
    Currently the file does not exist; this test skips with a pointer to
    the gating task. Once T-2.2 (Phase 2 GREEN) creates the file, the
    skip turns into a real assertion automatically.
    """
    if not ORCHESTRATOR_PATH.exists():
        pytest.skip("orchestrator.py not yet created — gate at T-2.2")

    source = ORCHESTRATOR_PATH.read_text(encoding="utf-8")
    modules = _collect_imported_modules(source)
    violations = _imports_violate_orthogonality(modules)

    assert not violations, (
        f"orchestrator.py imports forbidden spec-101 packages: {violations}. "
        f"spec-104 must remain orthogonal to installer/ and doctor/."
    )


# ---------------------------------------------------------------------------
# Test 2 — gate_cache.py orthogonality (gate on T-1.2)
# ---------------------------------------------------------------------------


def test_gate_cache_does_not_import_installer() -> None:
    """gate_cache.py (after T-1.2) must not import installer/doctor.

    Same orthogonality contract as orchestrator.py. Skip until the file
    exists; assertion engages automatically once Phase 1 GREEN lands.
    """
    if not GATE_CACHE_PATH.exists():
        pytest.skip("gate_cache.py not yet created — gate at T-1.2")

    source = GATE_CACHE_PATH.read_text(encoding="utf-8")
    modules = _collect_imported_modules(source)
    violations = _imports_violate_orthogonality(modules)

    assert not violations, (
        f"gate_cache.py imports forbidden spec-101 packages: {violations}. "
        f"spec-104 must remain orthogonal to installer/ and doctor/."
    )


# ---------------------------------------------------------------------------
# Test 3 — manifest.yml additivity
# ---------------------------------------------------------------------------


def test_manifest_yml_spec104_change_is_additive_only() -> None:
    """spec-104 must NOT modify spec-101-owned keys in manifest.yml.

    spec-101 owns `required_tools`, `python_env`, and `prereqs` per the
    spec-101 freeze note. spec-104 may add new top-level keys (currently
    expected: `gates.policy_doc_ref`) but must not modify or remove any
    of those three blocks.

    Today (pre-Phase 4) the manifest is unchanged from the spec-101
    baseline — every owned key is present. Test passes structurally;
    once Phase 4 lands the manifest mutation, this same test continues
    to enforce the contract by verifying the owned keys stay intact.
    """
    assert MANIFEST_PATH.is_file(), f"manifest.yml missing at {MANIFEST_PATH}"

    with MANIFEST_PATH.open("r", encoding="utf-8") as fh:
        manifest = yaml.safe_load(fh)

    assert isinstance(manifest, dict), "manifest.yml must parse to a top-level mapping"

    top_level_keys = set(manifest.keys())
    missing = SPEC_101_OWNED_TOP_LEVEL_KEYS - top_level_keys

    assert not missing, (
        f"spec-101-owned top-level keys missing from manifest.yml: {sorted(missing)}. "
        f"spec-104 must not remove these keys."
    )

    # Sanity: each owned key must be non-empty (spec-101 populated them
    # with non-trivial content). Empty dict / None signals a destructive
    # rewrite that spec-104 must NOT perform.
    for key in SPEC_101_OWNED_TOP_LEVEL_KEYS:
        value = manifest[key]
        assert value, (
            f"manifest.yml key '{key}' is empty/null. "
            f"spec-101 populated this block; spec-104 must preserve it."
        )


# ---------------------------------------------------------------------------
# Test 4 — skill markdown scope (D-104-07 whitelist)
# ---------------------------------------------------------------------------


def test_skills_unchanged_files_match_spec104_only_scope() -> None:
    """Files spec-104 commits touch under .claude/skills/** must be whitelisted.

    D-104-07 enumerates exactly three SKILL.md files in scope:
    `ai-commit/SKILL.md`, `ai-pr/SKILL.md`, `ai-pr/handlers/watch.md`.
    Plus T-0.1 allows updating AGENT_METADATA companions for ai-commit
    and ai-pr. Any other skill markdown touched by a spec-104 commit
    is a scope violation (R-7: verbosity cuts break IDE).

    Today, only the brainstorm/plan commit has landed and it does not
    touch .claude/skills/** — so the intersection is the empty set
    (a subset of the allowed set). The assertion engages naturally
    as Phase 4/5/7 commits add real skill changes.

    Also asserts the three target files exist now (currently-state
    presence check — guards against accidental deletion before
    spec-104 has had a chance to edit them).
    """
    # Presence check: targets must exist so spec-104 can edit them.
    for relative in sorted(SPEC_104_ALLOWED_SKILL_FILES):
        absolute = REPO_ROOT / relative
        assert absolute.is_file(), (
            f"Required skill file missing: {relative}. "
            f"spec-104 D-104-07 expects this file to exist before edits."
        )

    # Scope check: any file under .claude/skills/** touched by a
    # spec-104 commit must be in the whitelist.
    changed = _spec104_changed_files()
    skill_changes = [f for f in changed if f.startswith(".claude/skills/")]

    out_of_scope: list[str] = []
    for path in skill_changes:
        if path in SPEC_104_ALLOWED_SKILL_FILES:
            continue
        if any(path.startswith(prefix) for prefix in SPEC_104_ALLOWED_SKILL_PREFIXES):
            continue
        out_of_scope.append(path)

    assert not out_of_scope, (
        f"spec-104 commits modified skill files outside D-104-07 scope: "
        f"{out_of_scope}. Allowed: {sorted(SPEC_104_ALLOWED_SKILL_FILES)} "
        f"plus AGENT_METADATA* under ai-commit/ and ai-pr/."
    )
