"""spec-179 D-179-01 — ``auto-format.py`` skips sha-pinned framework scripts.

The PostToolUse auto-format hook reformats edited files with ruff. Files under
``.ai-engineering/scripts/`` are sha256-pinned in ``hooks-manifest.json`` for
integrity, so reformatting them with the consumer repo's ruff width (e.g. a
JS/Astro project's ruff default 88 vs the framework's 100) reflows them and
breaks hook integrity for the entire tree. The hook MUST skip any path under
``.ai-engineering/scripts/`` BEFORE invoking the formatter; ordinary project
files still format normally.

The module is loaded fresh per test via ``importlib`` (same pattern as
``test_auto_format_debounce.py``) so the per-path debounce map starts empty.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path, PurePosixPath, PureWindowsPath

import pytest

REPO = Path(__file__).resolve().parents[3]
HOOK_PATH = REPO / ".ai-engineering" / "scripts" / "hooks" / "auto-format.py"
HOOK_DIR = REPO / ".ai-engineering" / "scripts" / "hooks"


@pytest.fixture
def afmt(monkeypatch: pytest.MonkeyPatch):
    """Reload auto-format fresh so module state starts clean."""
    monkeypatch.delenv("AIENG_AUTOFORMAT_DEBOUNCE_SEC", raising=False)
    monkeypatch.syspath_prepend(str(HOOK_DIR))
    sys.modules.pop("aieng_autoformat_exclusion_test", None)
    spec = importlib.util.spec_from_file_location("aieng_autoformat_exclusion_test", HOOK_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._LAST_FORMAT_TIMES.clear()
    return module


def test_pinned_scripts_predicate_normalizes_separators(afmt) -> None:
    """R4: predicate matches the ``.ai-engineering/scripts/`` segment for
    absolute/relative/Windows inputs via ``as_posix``."""
    assert afmt._is_under_pinned_scripts(PurePosixPath("/p/.ai-engineering/scripts/hooks/x.py"))
    assert afmt._is_under_pinned_scripts(PurePosixPath(".ai-engineering/scripts/runtime-stop.py"))
    assert afmt._is_under_pinned_scripts(
        PureWindowsPath(r"C:\p\.ai-engineering\scripts\hooks\x.py")
    )
    assert not afmt._is_under_pinned_scripts(PurePosixPath("/p/src/main.py"))
    assert not afmt._is_under_pinned_scripts(PurePosixPath("/p/ai-engineering-helper.py"))


def test_main_skips_formatter_for_pinned_script(afmt, monkeypatch: pytest.MonkeyPatch) -> None:
    """A PostToolUse edit to a pinned script MUST NOT invoke the formatter."""
    called: list[tuple] = []
    monkeypatch.setitem(afmt._EXTENSION_FORMATTERS, ".py", lambda *a, **k: called.append(a))
    monkeypatch.setattr(
        afmt,
        "read_stdin",
        lambda: {
            "tool_name": "Edit",
            "tool_input": {"file_path": "/proj/.ai-engineering/scripts/hooks/memory-stop.py"},
        },
    )
    afmt.main()
    assert called == [], "formatter must not run for a sha-pinned script"


def test_main_formats_ordinary_python_file(
    afmt, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """An edit to an ordinary project ``.py`` still gets formatted (no regression)."""
    target = tmp_path / "src" / "mod.py"
    target.parent.mkdir(parents=True)
    target.write_text("x=1\n", encoding="utf-8")
    called: list[tuple] = []
    monkeypatch.setitem(afmt._EXTENSION_FORMATTERS, ".py", lambda *a, **k: called.append(a))
    monkeypatch.setattr(afmt, "_maybe_restage_after_format", lambda root: None)
    monkeypatch.setattr(
        afmt,
        "read_stdin",
        lambda: {"tool_name": "Edit", "tool_input": {"file_path": str(target)}},
    )
    afmt.main()
    assert called, "ordinary python file must still be formatted"
