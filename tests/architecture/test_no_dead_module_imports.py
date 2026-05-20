"""Spec-146 guard for hard-deleted dead modules."""

from __future__ import annotations

import ast
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = PROJECT_ROOT / "src" / "ai_engineering"

DELETED_FILES = (
    "src/ai_engineering/state/agentsview.py",
    "src/ai_engineering/state/outbox.py",
    "src/ai_engineering/governance/policy_engine.py",
    "src/ai_engineering/cli_ui_skill_ref.py",
)
DELETED_MODULES = {
    "ai_engineering.state.agentsview",
    "ai_engineering.state.outbox",
    "ai_engineering.governance.policy_engine",
    "ai_engineering.cli_ui_skill_ref",
}


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def test_deleted_module_files_are_absent() -> None:
    for relative in DELETED_FILES:
        assert not (PROJECT_ROOT / relative).exists(), f"{relative} should stay hard-deleted"


def test_production_code_does_not_import_deleted_modules() -> None:
    offenders: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        imported = _imported_modules(path)
        bad = DELETED_MODULES & imported
        if bad:
            offenders.append(f"{path.relative_to(PROJECT_ROOT)} -> {sorted(bad)}")
    assert offenders == []


def test_governance_package_no_longer_reexports_deleted_policy_engine() -> None:
    init_source = (
        PROJECT_ROOT / "src" / "ai_engineering" / "governance" / "__init__.py"
    ).read_text(encoding="utf-8")

    assert "policy_engine" not in init_source
    assert "Decision" not in init_source
    assert "evaluate" not in init_source
