"""Lock the three `ALLOWED_EVENT_KINDS` sites against drift (spec-137 D-137-01).

`ALLOWED_EVENT_KINDS` is declared in three places that the brief flagged
as a drift surface:

1. ``tools/skill_domain/event_schema.py`` (authoritative Pydantic-side).
2. ``.ai-engineering/scripts/hooks/_lib/observability.py`` (stdlib mirror).
3. ``.ai-engineering/scripts/hooks/_lib/hook-common.py`` (validation mirror).

The hook-side files cannot import the package-side authority because
they run before ``uv sync`` (the stdlib-only constraint). The contract
the test enforces is therefore *membership equality*, not import
identity: every kind in the authority must appear in both mirrors and
vice versa. If a future PR adds a kind to one site and forgets the
others, this test fails loud.
"""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

AUTHORITY = REPO_ROOT / "tools" / "skill_domain" / "event_schema.py"
MIRROR_OBSERVABILITY = (
    REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "observability.py"
)
MIRROR_HOOK_COMMON = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "_lib" / "hook-common.py"


def _load_kinds_from_authority() -> frozenset[str]:
    """Import the authoritative frozenset via importlib (Pydantic-free)."""
    spec = importlib.util.spec_from_file_location("_test_event_schema_authority", str(AUTHORITY))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    kinds = module.ALLOWED_EVENT_KINDS
    assert isinstance(kinds, frozenset)
    return kinds


def _extract_frozenset_literal(path: Path, name: str) -> frozenset[str]:
    """Parse the file and extract the named frozenset literal as a Python set.

    We avoid importing the mirror modules because they have stdlib-only
    constraints and (in the case of `hook-common.py`) hyphenated module
    names that importlib cannot resolve cleanly.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return _frozenset_from_ast_value(node.value)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            if node.value is None:
                continue
            return _frozenset_from_ast_value(node.value)
    raise AssertionError(f"Did not find {name} in {path}")


def _frozenset_from_ast_value(value: ast.expr) -> frozenset[str]:
    if isinstance(value, ast.Call):
        func = value.func
        if isinstance(func, ast.Name) and func.id == "frozenset" and value.args:
            arg = value.args[0]
            if isinstance(arg, (ast.Set, ast.List, ast.Tuple)):
                return frozenset(
                    elt.value
                    for elt in arg.elts
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                )
    if isinstance(value, (ast.Set, ast.List, ast.Tuple)):
        return frozenset(
            elt.value
            for elt in value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        )
    raise AssertionError(f"Unsupported literal shape: {ast.dump(value)}")


def test_three_frozensets_agree_on_kind_membership() -> None:
    """Authority and both mirrors must hold identical kind membership."""
    authority = _load_kinds_from_authority()
    mirror_observability = _extract_frozenset_literal(MIRROR_OBSERVABILITY, "_ALLOWED_KINDS")
    mirror_hook_common = _extract_frozenset_literal(MIRROR_HOOK_COMMON, "_ALLOWED_KINDS")

    drift_observability = authority.symmetric_difference(mirror_observability)
    drift_hook_common = authority.symmetric_difference(mirror_hook_common)

    assert not drift_observability, (
        f"observability.py mirror has drifted from authoritative ALLOWED_EVENT_KINDS: "
        f"{drift_observability}"
    )
    assert not drift_hook_common, (
        f"hook-common.py mirror has drifted from authoritative ALLOWED_EVENT_KINDS: "
        f"{drift_hook_common}"
    )


def test_authority_has_fourteen_declared_kinds() -> None:
    """spec-137 surveyed 13 kinds; spec-139 M2 added ``host_capacity`` (14)."""
    authority = _load_kinds_from_authority()
    assert len(authority) == 14, (
        f"expected 14 declared kinds; got {len(authority)}: {sorted(authority)}"
    )
