"""Layer-isolation enforcement for ``adapters/host/`` (spec-139 M2.T5, D-139-09).

The resource-preflight probe lives in the adapter ring of the
Hexagonal architecture per D-139-09. This test guards the seam:

1. The package physically lives at
   ``src/ai_engineering/adapters/host/`` -- not under ``config/`` or
   any other inner-ring location.
2. The module imports the :class:`HostProbe` shape from
   :mod:`ai_engineering.config.concurrency` (single source of truth)
   but does NOT pull in any application or governance layer modules.
3. The :func:`ai_engineering.adapters.host.probe` symbol is importable
   without raising.

Adapters may import from inner rings (config, state, paths). The
inverse is forbidden; the `lint-imports` direction contract in
``test_hexagonal.py`` enforces that side of the seam.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOST_ADAPTER_DIR = _REPO_ROOT / "src" / "ai_engineering" / "adapters" / "host"

# Modules the host adapter must never import from -- these would couple
# the adapter to outer rings (CLI, governance) and invert the
# Hexagonal direction.
_BANNED_PREFIXES: tuple[str, ...] = (
    "ai_engineering.cli_commands",
    "ai_engineering.governance",
    "ai_engineering.installer",
    "ai_engineering.updater",
    "ai_engineering.policy",
    "ai_engineering.validator",
    "ai_engineering.vcs",
    "ai_engineering.ide",
    "ai_engineering.issues",
)


def _collect_imports(tree: ast.Module) -> list[str]:
    """Return the dotted names of every import in ``tree``."""
    names: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.append(node.module)
    return names


def _is_banned(module_name: str) -> bool:
    return any(
        module_name == banned or module_name.startswith(banned + ".") for banned in _BANNED_PREFIXES
    )


def test_host_adapter_directory_exists() -> None:
    """spec-139 D-139-09: the probe lives under ``adapters/host/``."""
    assert _HOST_ADAPTER_DIR.is_dir(), (
        f"missing host adapter package: {_HOST_ADAPTER_DIR}. "
        "spec-139 M2 places the probe under src/ai_engineering/adapters/host/."
    )
    probe_module = _HOST_ADAPTER_DIR / "probe.py"
    assert probe_module.is_file(), f"missing probe.py: {probe_module}"


def test_host_adapter_has_no_outer_ring_imports() -> None:
    """``adapters/host/*.py`` may import inner rings but not outer rings."""
    walked: list[Path] = []
    violations: list[tuple[Path, str]] = []
    for py_file in sorted(_HOST_ADAPTER_DIR.rglob("*.py")):
        if "__pycache__" in py_file.parts:
            continue
        walked.append(py_file)
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover — flake would catch first
            pytest.fail(f"could not parse {py_file}: {exc}")
        for module_name in _collect_imports(tree):
            if _is_banned(module_name):
                violations.append((py_file, module_name))

    # Vacuous-pass guard: the adapter package must contain real files.
    assert len(walked) >= 2, (
        f"expected ≥ 2 .py files in {_HOST_ADAPTER_DIR}, got {len(walked)}. "
        "M2 ships __init__.py + probe.py."
    )

    if violations:
        formatted = "\n".join(
            f"  {p.relative_to(_REPO_ROOT)} imports {mod!r}" for p, mod in violations
        )
        pytest.fail(
            "adapters/host/ imports forbidden outer-ring modules "
            f"(D-139-09 violation):\n{formatted}"
        )


def test_host_adapter_is_importable_without_domain_coupling() -> None:
    """`from ai_engineering.adapters.host import probe` is side-effect-free.

    A successful import without raising proves the package wires up
    cleanly. We also check that the symbol resolves to a callable,
    matching the contract published in ``__init__.py``.
    """
    from ai_engineering.adapters.host import HostProbe, probe

    # ``probe`` is the dispatching function; calling it must not raise
    # (fail-open contract). The return value is platform-dependent so
    # we only assert the type.
    snapshot = probe()
    assert isinstance(snapshot, HostProbe)
