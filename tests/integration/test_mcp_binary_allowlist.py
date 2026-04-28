"""GREEN tests for spec-107 G-1 — MCP binary allowlist (D-107-01).

The MCP-health hook resolves ``AIE_MCP_CMD_<SERVER>`` via ``shlex.split``
and then validates the first token against ``_ALLOWED_MCP_BINARIES``.
Anything outside the canonical 8-runtime allowlist must be rejected
unless a matching active risk-acceptance exists in
``decision-store.json``. These tests exercise the *naming* check only;
the risk-accept escape hatch is covered by
``test_mcp_binary_risk_accept.py``.

Test surface:
- 8 allowed binaries (npx, node, python3, bunx, deno, cargo, go, dotnet)
  → ``_binary_allowed`` returns True silently.
- 5 malicious / unmanaged binaries (bash, sh, curl, wget, python without
  the version suffix) → ``_binary_allowed`` returns False AND emits a
  ``control_outcome`` event with ``control="binary-rejected"``.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
HOOK_PATH = REPO_ROOT / ".ai-engineering" / "scripts" / "hooks" / "mcp-health.py"


def _load_hook_module():
    """Load ``mcp-health.py`` as a module so we can call private helpers.

    The hook's filename contains a hyphen and is intentionally not a
    proper Python module — production callers spawn it as a script. For
    direct testing we use ``importlib.util.spec_from_file_location`` so
    the helper functions become callable without re-implementing them.
    """
    spec = importlib.util.spec_from_file_location("_mcp_health_test_module", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hook_module():
    return _load_hook_module()


def _events_path(project_root: Path) -> Path:
    return project_root / ".ai-engineering" / "state" / "framework-events.ndjson"


def _read_events(project_root: Path) -> list[dict]:
    path = _events_path(project_root)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


@pytest.fixture()
def project_root(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    (root / ".ai-engineering" / "state").mkdir(parents=True)
    return root


@pytest.mark.parametrize(
    "binary",
    [
        "npx",
        "node",
        "python3",
        "bunx",
        "deno",
        "cargo",
        "go",
        "dotnet",
    ],
)
def test_canonical_binaries_allowed_silently(hook_module, project_root: Path, binary: str) -> None:
    """All 8 canonical runtimes must be permitted without telemetry.

    Spec-107 D-107-01: in-allowlist hits short-circuit before the
    decision-store lookup and emit zero events. This keeps the hot path
    free of I/O for the common case.
    """
    permitted = hook_module._binary_allowed(
        binary,
        project_root=project_root,
        server_name="example",
        cmd_kind="probe",
    )
    assert permitted is True, (
        f"binary {binary!r} should be in _ALLOWED_MCP_BINARIES but was rejected"
    )
    events = _read_events(project_root)
    assert events == [], (
        f"in-allowlist hit must emit zero telemetry events; got {len(events)}: {events!r}"
    )


@pytest.mark.parametrize(
    "binary",
    [
        "bash",
        "sh",
        "curl",
        "wget",
        # Bare ``python`` without ``3`` — Python 2 / unmanaged interpreter.
        "python",
    ],
)
def test_unallowed_binaries_rejected_and_logged(
    hook_module, project_root: Path, binary: str
) -> None:
    """Binaries outside the allowlist (no DEC) must be denied + audit-logged.

    Spec-107 D-107-01 step 3: ``_binary_allowed`` returns False, writes a
    canonical WARN to stderr, and emits a ``control_outcome`` event with
    ``control="binary-rejected"`` so a compromise attempt is visible to
    auditors via ``framework-events.ndjson``.
    """
    permitted = hook_module._binary_allowed(
        binary,
        project_root=project_root,
        server_name="example",
        cmd_kind="probe",
    )
    assert permitted is False, (
        f"binary {binary!r} is outside the allowlist and should have been rejected"
    )
    events = _read_events(project_root)
    rejected = [
        e
        for e in events
        if e.get("kind") == "control_outcome"
        and e.get("detail", {}).get("control") == "binary-rejected"
        and e.get("detail", {}).get("binary") == binary
    ]
    assert len(rejected) == 1, (
        f"expected 1 binary-rejected event for {binary!r}, got "
        f"{len(rejected)}: {rejected!r} (all events: {events!r})"
    )
    detail = rejected[0]["detail"]
    assert detail.get("category") == "mcp-sentinel"
    assert detail.get("server") == "example"
    assert detail.get("cmd_kind") == "probe"


def test_constant_contents_match_spec(hook_module) -> None:
    """The canonical 8-binary set must exactly match D-107-01."""
    expected = frozenset({"npx", "node", "python3", "bunx", "deno", "cargo", "go", "dotnet"})
    assert expected == hook_module._ALLOWED_MCP_BINARIES, (
        "Allowlist drift detected. Edits to _ALLOWED_MCP_BINARIES must be "
        "approved via spec amendment + risk acceptance flow, not direct "
        "code change."
    )
