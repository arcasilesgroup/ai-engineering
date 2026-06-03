"""spec-109 G-7 / D-109-08 — render_detection PATH-check qualifier (#490).

The pre-install detection banner marks tools with ✓/✗ based purely on PATH
availability. D-109-08 requires the ``Tools`` line to be qualified so the user
understands ✓ means "found on PATH", not "install will succeed". Before this
test the qualifier was unpinned: a refactor of ``render_detection`` could drop
the caveat with no gate failing. These tests pin the observable contract on
both the rich and plain rendering paths.
"""

from __future__ import annotations

import ai_engineering.installer.ui as ui


def test_plain_path_tools_line_carries_path_qualifier(capsys, monkeypatch):
    monkeypatch.setattr(ui, "_HAS_RICH", False)

    ui.render_detection("github", ["anthropic"], {"ruff": True, "ty": False})

    err = capsys.readouterr().err
    # The PATH-only caveat must be present (D-109-08), not a bare "Tools:" line.
    assert "PATH" in err, f"PATH-check qualifier missing from plain output:\n{err}"
    assert "ruff" in err and "ty" in err


def test_rich_path_tools_line_carries_path_qualifier(monkeypatch):
    captured: list[str] = []

    class _FakeConsole:
        def print(self, *args, **_kwargs):
            captured.append(str(args[0]) if args else "")

    monkeypatch.setattr(ui, "_HAS_RICH", True)
    monkeypatch.setattr(ui, "_console", _FakeConsole())

    ui.render_detection("github", ["anthropic"], {"ruff": True})

    blob = "\n".join(captured)
    assert "PATH" in blob, f"PATH-check qualifier missing from rich output:\n{blob}"
    # The clarification line that explains what ✓ means must survive refactors.
    assert "found on PATH" in blob, f"PATH clarification line missing:\n{blob}"
