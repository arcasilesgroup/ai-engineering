"""Architecture guard: M6 throttled-rotation wiring exists on every runtime surface.

spec-139 M6.T5 (second test). The throttled rotation wrapper
(``runtime-rotate-throttled.py``) MUST be wired into the SessionEnd
(or engine-equivalent end-of-session) hook of every active conversational
runtime surface:

| IDE / runtime  | Config file              | Event name      |
|----------------|--------------------------|-----------------|
| Claude Code    | ``.claude/settings.json``| ``SessionEnd``  |
| OpenAI Codex   | ``.codex/hooks.json``    | ``Stop``        |

Out of scope (documented N/A or deferred per spec-139 M6.T3):

* ``.github/`` — GitHub Copilot has no conversational SessionEnd primitive.
* ``.opencode/`` and ``.cursor/`` — deferred until those mirror directories
  materialise (spec-128 Wave 4 follow-up).

The guard validates the **canonical script name** appears in the command
string; we deliberately do NOT pin the exact argv form so future routing
changes (e.g. running through ``codex-hook-bridge.py``) remain refactor-safe.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# Each surface wires the throttle wrapper under a different event name.
# Stored as a 3-tuple so a missing entry produces a single, specific
# failure rather than a parametrize collapse.
SURFACES: list[tuple[str, Path, str]] = [
    ("claude_code", REPO / ".claude" / "settings.json", "SessionEnd"),
    ("codex", REPO / ".codex" / "hooks.json", "Stop"),
]
WRAPPER_BASENAME = "runtime-rotate-throttled.py"


def _walk_commands(hooks_block: object) -> list[str]:
    """Flatten an IDE hooks block into a list of command strings.

    The committed hook-config surfaces share the same nested shape:

        {
          "<event>": [
            { "matcher": "...", "hooks": [ {"type": "command", "command": "..."}, ... ] },
            ...
          ]
        }

    The walker is defensive about shape mismatches because each IDE has a
    slightly different schemas. We collect every ``"command"`` string
    we can reach and return them flat.
    """
    out: list[str] = []
    if not isinstance(hooks_block, list):
        return out
    for matcher in hooks_block:
        if not isinstance(matcher, dict):
            continue
        nested = matcher.get("hooks")
        if not isinstance(nested, list):
            continue
        for h in nested:
            if not isinstance(h, dict):
                continue
            cmd = h.get("command")
            if isinstance(cmd, str):
                out.append(cmd)
    return out


@pytest.mark.parametrize("name,config_path,event_name", SURFACES, ids=[s[0] for s in SURFACES])
def test_runtime_rotate_throttled_wired_on_surface(
    name: str, config_path: Path, event_name: str
) -> None:
    """Each active runtime surface wires ``runtime-rotate-throttled.py``."""
    assert config_path.is_file(), f"{name}: config file missing at {config_path}"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    hooks_root = config.get("hooks") if isinstance(config, dict) else None
    assert isinstance(hooks_root, dict), (
        f"{name}: ``hooks`` block missing or malformed at {config_path}"
    )
    event_block = hooks_root.get(event_name)
    assert event_block is not None, (
        f"{name}: no ``{event_name}`` registration in {config_path.relative_to(REPO)}"
    )
    commands = _walk_commands(event_block)
    matching = [c for c in commands if WRAPPER_BASENAME in c]
    assert matching, (
        f"{name}: ``{WRAPPER_BASENAME}`` not wired into ``{event_name}`` "
        f"in {config_path.relative_to(REPO)}. Commands seen: {commands}"
    )


def test_runtime_rotate_throttled_appears_exactly_once_per_surface() -> None:
    """Defence-in-depth: the wrapper is wired exactly once per surface.

    Double-wiring would re-rotate twice per SessionEnd (defeating the
    throttle in the worst case where the sentinel write races between
    the two invocations). A single registration per surface is the
    invariant.
    """
    for name, config_path, _event in SURFACES:
        config = json.loads(config_path.read_text(encoding="utf-8"))
        hooks_root = config.get("hooks", {})
        # Collect ALL commands across every event — a stray registration
        # under PreToolUse or similar would also be a bug.
        all_commands: list[str] = []
        for event_block in (hooks_root or {}).values():
            all_commands.extend(_walk_commands(event_block))
        hits = [c for c in all_commands if WRAPPER_BASENAME in c]
        assert len(hits) == 1, (
            f"{name}: expected exactly one ``{WRAPPER_BASENAME}`` invocation "
            f"across the whole config, found {len(hits)}: {hits}"
        )


def test_codex_invocation_carries_aieng_hook_engine_label() -> None:
    """Codex routing convention: the wrapper invocation pins ``AIENG_HOOK_ENGINE=codex``.

    The codex surface uses ``AIENG_HOOK_ENGINE=<engine>`` as a literal
    prefix on every hook command (see ``.codex/hooks.json`` peer entries).
    This keeps the hook_context engine detection deterministic when the
    bridge is bypassed. We assert the convention is preserved for the
    rotation wrapper so audit telemetry tags the right engine.
    """
    cfg = json.loads((REPO / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    commands = _walk_commands(cfg.get("hooks", {}).get("Stop"))
    rotates = [c for c in commands if WRAPPER_BASENAME in c]
    assert rotates, "codex: rotation wrapper not wired into Stop"
    for cmd in rotates:
        assert "AIENG_HOOK_ENGINE=codex" in cmd, (
            f"codex: rotation command missing engine label: {cmd!r}"
        )
