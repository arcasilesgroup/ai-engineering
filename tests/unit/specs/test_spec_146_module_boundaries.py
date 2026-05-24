"""Spec-146 module-boundary preservation and split contracts."""

from __future__ import annotations

import importlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
# spec-153 W3: reaped from specs/ root into the uniform per-spec archive
# directory (D-153-07).
INVENTORY = (
    PROJECT_ROOT
    / ".ai-engineering"
    / "specs"
    / "archive"
    / "spec-146-framework-simplification-less-is-more"
    / "caller-inventory.md"
)

PRESERVED_MODULES = (
    "src/ai_engineering/state/trace_context.py",
    "src/ai_engineering/state/capabilities.py",
    "src/ai_engineering/state/context_packs.py",
    "src/ai_engineering/state/relevance.py",
)


def test_production_used_state_modules_are_preserved() -> None:
    inventory = INVENTORY.read_text(encoding="utf-8")

    for relative in PRESERVED_MODULES:
        assert (PROJECT_ROOT / relative).is_file(), f"{relative} must not be deleted"
    for name in ("trace_context.py", "capabilities.py", "context_packs.py", "relevance.py"):
        assert f"`{name}`" in inventory
        assert "Preserve" in inventory


def test_policy_orchestrator_flattens_state_service_callsite() -> None:
    source = (PROJECT_ROOT / "src" / "ai_engineering" / "policy" / "orchestrator.py").read_text(
        encoding="utf-8"
    )

    assert "from ai_engineering.state.service import StateService" not in source
    assert "from ai_engineering.state.repository import DurableStateRepository" in source


def test_installer_mechanisms_are_split_but_package_root_reexports() -> None:
    mechanisms = importlib.import_module("ai_engineering.installer.mechanisms")

    expected_modules = {
        "ai_engineering.installer.mechanisms.python_tools": ("UvToolMechanism",),
        "ai_engineering.installer.mechanisms.node_tools": ("NpmDevMechanism",),
        "ai_engineering.installer.mechanisms.language_tools": (
            "CargoInstallMechanism",
            "GoInstallMechanism",
            "SdkmanMechanism",
        ),
        "ai_engineering.installer.mechanisms.windows_tools": ("WingetMechanism",),
    }
    for module_name, class_names in expected_modules.items():
        module = importlib.import_module(module_name)
        for class_name in class_names:
            assert getattr(mechanisms, class_name) is getattr(module, class_name)
