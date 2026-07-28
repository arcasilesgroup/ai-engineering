"""The two engine-detection paths must agree (spec-201 D-201-06).

Before spec-201 the framework had two disagreeing answers to "which
engine am I running under?":

* ``_lib/hook_context.get_hook_context`` ran a five-step detection ladder
  that terminated at the literal ``unknown``.
* ``_lib/hook-common.py`` hardcoded ``os.environ.get("AIENG_HOOK_ENGINE")
  or "claude_code"`` at four separate emit sites.

On a foreign host that split produced the worst possible outcome: some
events were dropped (``unknown`` was outside the enum) and the rest were
**mislabelled as Claude Code** and accepted. Multi-harness attribution is
impossible until the two agree, so this module pins the agreement itself
rather than either implementation's internals.

Ordering note (TRAP 3): the reconciliation to ``unknown`` is only safe
because ``openai_compatible`` and ``unknown`` were admitted to both enum
twins first. Reversing that order converts mislabelling into 100% event
loss on every non-Claude harness.
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"
HOOK_CONTEXT_PATH = HOOKS_DIR / "_lib" / "hook_context.py"
HOOK_COMMON_PATH = HOOKS_DIR / "_lib" / "hook-common.py"

_ENGINE_ENV_VARS = (
    "AIENG_HOOK_ENGINE",
    "AIENG_HOOK_ENGINE_DEFAULT",
    "CLAUDE_PROJECT_DIR",
    "ANTIGRAVITY_PROJECT_DIR",
)

_EVENTS_REL = Path(".ai-engineering") / "state" / "framework-events.ndjson"


@pytest.fixture
def ctx():
    """Load ``_lib/hook_context.py`` under a fresh module name."""
    sys.modules.pop("aieng_hook_context_reconciliation", None)
    spec = importlib.util.spec_from_file_location(
        "aieng_hook_context_reconciliation", HOOK_CONTEXT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["aieng_hook_context_reconciliation"] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def hc(monkeypatch: pytest.MonkeyPatch):
    """Load ``_lib/hook-common.py`` by path (the filename is hyphenated)."""
    monkeypatch.syspath_prepend(str(HOOKS_DIR))
    spec = importlib.util.spec_from_file_location(
        "aieng_hook_common_reconciliation", HOOK_COMMON_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def bare_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A cwd with no IDE marker dir and no engine env var of any kind."""
    for var in _ENGINE_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    (tmp_path / ".ai-engineering" / "state").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".ai-engineering" / "runtime").mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def _last_event(project_root: Path) -> dict:
    path = project_root / _EVENTS_REL
    assert path.exists(), f"no event was written to {path}"
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert lines, f"{path} is empty"
    return json.loads(lines[-1])


# ---------------------------------------------------------------------------
# (a) the reconciled default
# ---------------------------------------------------------------------------


def test_detect_engine_defaults_to_unknown(ctx, bare_host: Path) -> None:
    """No env var, no marker dir -> ``unknown``, never a guessed ``claude_code``."""
    assert ctx.detect_engine() == "unknown"


def test_get_hook_context_delegates_to_detect_engine(
    ctx, bare_host: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One ladder, two callers — ``get_hook_context`` must not re-implement it."""
    monkeypatch.setattr(sys, "stdin", io.StringIO(""))
    assert ctx.get_hook_context().engine == ctx.detect_engine()


# ---------------------------------------------------------------------------
# (b) hook-common's emit paths resolve the SAME engine
# ---------------------------------------------------------------------------


def test_hook_common_resolve_engine_matches_detect_engine(ctx, hc, bare_host: Path) -> None:
    assert hc._resolve_engine() == ctx.detect_engine() == "unknown"


@pytest.mark.parametrize(
    "emitter",
    ["heartbeat", "hook_error", "integrity_violation", "storm_control"],
)
def test_all_four_emit_paths_stamp_the_reconciled_engine(hc, bare_host: Path, emitter: str) -> None:
    """The four sites that hardcoded ``claude_code`` must stamp ``unknown``."""
    if emitter == "heartbeat":
        hc._emit_hook_heartbeat(
            component="hook.test", hook_kind="pre-tool-use", duration_ms=1, outcome="success"
        )
    elif emitter == "hook_error":
        hc._emit_hook_error(
            component="hook.test", hook_kind="pre-tool-use", exc=RuntimeError("boom")
        )
    elif emitter == "integrity_violation":
        hc._emit_integrity_violation(
            component="hook.test", hook_kind="pre-tool-use", reason="sha mismatch", mode="warn"
        )
    else:
        hc._emit_error_storm_control(
            bare_host,
            component="hook.test",
            error_code="hook_execution_failed",
            fingerprint="fp",
            occurrences=5,
            hook_kind="pre-tool-use",
        )

    assert _last_event(bare_host)["engine"] == "unknown"


def _fallback_string_literals(tree: ast.AST) -> set[str]:
    """String constants used as an ``or``-fallback anywhere in the module.

    ``"claude_code"`` legitimately remains in ``_ALLOWED_ENGINES`` and in
    prose, so a whole-file substring scan would be permanently red. The
    defect has one precise shape — ``<expr> or "<engine>"`` — and that is
    what this extracts.
    """
    literals: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.BoolOp):
            literals |= {
                operand.value
                for operand in node.values
                if isinstance(operand, ast.Constant) and isinstance(operand.value, str)
            }
    return literals


def test_no_hardcoded_claude_code_default_remains() -> None:
    """The four ``or "claude_code"`` fallbacks are the defect; none may survive."""
    tree = ast.parse(HOOK_COMMON_PATH.read_text(encoding="utf-8"))
    fallbacks = _fallback_string_literals(tree)
    assert "claude_code" not in fallbacks, (
        "hook-common.py still falls back to claude_code; a foreign harness's "
        "events get mislabelled as Claude Code and multi-harness attribution is lost"
    )
    assert "unknown" in fallbacks, (
        "the degraded path must terminate at the same `unknown` the detection "
        "ladder produces, or the two paths disagree again"
    )


# ---------------------------------------------------------------------------
# (c) explicit opt-in wins on BOTH paths
# ---------------------------------------------------------------------------


def test_explicit_engine_env_wins_on_both_paths(
    ctx, hc, bare_host: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AIENG_HOOK_ENGINE", "openai_compatible")
    assert ctx.detect_engine() == "openai_compatible"
    assert hc._resolve_engine() == "openai_compatible"


def test_engine_default_env_is_honoured_on_both_paths(
    ctx, hc, bare_host: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``AIENG_HOOK_ENGINE_DEFAULT`` is the documented terminal override."""
    monkeypatch.setenv("AIENG_HOOK_ENGINE_DEFAULT", "openai_compatible")
    assert ctx.detect_engine() == "openai_compatible"
    assert hc._resolve_engine() == "openai_compatible"


# ---------------------------------------------------------------------------
# (d) no regression on the dominant surface
# ---------------------------------------------------------------------------


def test_claude_project_dir_still_resolves_claude_code(
    ctx, hc, bare_host: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", str(bare_host))
    assert ctx.detect_engine() == "claude_code"
    assert hc._resolve_engine() == "claude_code"


def test_claude_marker_dir_still_resolves_claude_code(ctx, hc, bare_host: Path) -> None:
    (bare_host / ".claude").mkdir()
    assert ctx.detect_engine() == "claude_code"
    assert hc._resolve_engine() == "claude_code"


def test_codex_marker_dir_still_resolves_codex(ctx, hc, bare_host: Path) -> None:
    (bare_host / ".codex").mkdir()
    assert ctx.detect_engine() == "codex"
    assert hc._resolve_engine() == "codex"
