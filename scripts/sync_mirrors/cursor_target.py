"""Cursor surface generators.

spec-201 D-201-04: the Cursor 3.x discovery allowlist contains
``.agents/skills/``, so Cursor now reads the shared skill tree the
installer ships and ``.cursor/skills`` was hard-deleted — it shipped 54
skill directories with zero ``handlers/``, which stopped ``/ai-build`` at
preflight for every Cursor consumer. Agents stay at
``.cursor/agents/<name>.mdc`` (D-201-22).

spec-201 D-201-17 adds ``.cursor/hooks.json``. ``cursor-hook-bridge.py`` has
existed since spec-133 and has never fired once, because no ``hooks.json`` was
emitted anywhere in the tree — dead-by-bug, not dead-by-design.
"""

from __future__ import annotations

import json

from scripts.sync_mirrors.core import generate_cursor_agent

_BRIDGE_COMMAND = (
    "AIENG_HOOK_ENGINE=openai_compatible "
    "bash .ai-engineering/scripts/hooks/_lib/run-hook.sh "
    ".ai-engineering/scripts/hooks/cursor-hook-bridge.py"
)

# Ground truth from Cursor 3.12.17
# (`Contents/Resources/app/out/vs/workbench/workbench.desktop.main.js`):
#
# * `uWo` (config validator) requires a numeric, positive-integer `version` and
#   an object `hooks` whose keys are members of the 21-step `Nu` enum.
# * `sWo` lists the deny-capable steps: `beforeShellExecution`,
#   `beforeMCPExecution`, `beforeReadFile`, `beforeTabFileRead`,
#   `subagentStart`, `preToolUse`.
# * `jzi` projects the Claude config Cursor ALSO loads
#   (`<workspace>/.claude/settings.json`) onto Cursor steps:
#   PreToolUse->preToolUse, PostToolUse->postToolUse,
#   UserPromptSubmit->beforeSubmitPrompt, Stop->stop,
#   SubagentStop->subagentStop, SessionStart->sessionStart,
#   SessionEnd->sessionEnd, PreCompact->preCompact.
# * `_getHookKey` dedupes by the literal `command:` string, so a Cursor entry
#   whose command differs from the Claude entry does NOT dedupe — both fire.
#
# Those two facts together decide the step list. Every lifecycle step this repo
# cares about (`stop`, `sessionStart`, `sessionEnd`, `beforeSubmitPrompt`,
# `preCompact`) is ALREADY delivered to the canonical hooks through Cursor's
# native Claude-config projection. Registering them again here would
# double-fire them — double telemetry, double rotation, double instinct
# extraction — not add coverage. The two steps below have no Claude projection
# at all, so they are pure additions:
#
#   beforeShellExecution -> the deny lane. `--no-verify` plus the write-side
#                           injection guard. This is the D-201-17 gap.
#   beforeReadFile       -> the read-side lane. File content reaches
#                           `injection-read-guard.py` as tool_name="Read".
#
# `afterShellExecution` is deliberately NOT registered: the only read-side
# guard is `injection-read-guard.py`, whose `_is_external()` allowlist excludes
# Bash by design ("Bash output is scanned by the PreToolUse guard"), so the
# registration would land wired-and-dead — the precise failure mode this spec
# exists to close.
#
# Every matcher is `""` (match-all): Cursor's `pff` fails OPEN on an invalid
# regex, so a typo would silently disable filtering rather than the hook. The
# Python guards do their own tool filtering, exactly as Claude Code's
# `injection-read-guard` registration does.
_CURSOR_HOOKS_SPEC: tuple[tuple[str, int, str], ...] = (
    (
        "beforeShellExecution",
        15,
        "Deny --no-verify and prompt-injection attempts before the shell runs",
    ),
    (
        "beforeReadFile",
        10,
        "Scan file content for injected instructions before it enters context",
    ),
)

_CURSOR_HOOKS_VERSION = 1


def generate_cursor_hooks_json() -> str:
    """Deterministically build ``.cursor/hooks.json`` from one in-module table.

    Follows ``generate_copilot_hooks_json`` (D-159-06): one spec table, dual
    written to root + installer template by Surface 5c, byte-identical in both
    places. There is no "canonical hand-authored root" option for a file that
    did not exist before this spec.
    """
    hooks: dict[str, list[dict[str, object]]] = {}
    for step, timeout, comment in _CURSOR_HOOKS_SPEC:
        hooks[step] = [
            {
                "type": "command",
                "command": _BRIDGE_COMMAND,
                "matcher": "",
                "timeout": timeout,
                "comment": comment,
            }
        ]
    payload = {"version": _CURSOR_HOOKS_VERSION, "hooks": hooks}
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


__all__ = ["generate_cursor_agent", "generate_cursor_hooks_json"]
