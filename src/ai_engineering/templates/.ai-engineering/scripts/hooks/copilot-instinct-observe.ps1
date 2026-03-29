# Copilot wrapper for instinct-observe.py.
# Usage: copilot-instinct-observe.ps1 pre|post
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"

try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    if ($args.Count -gt 0) {
        $Phase = $args[0]
    } else {
        $Phase = "post"
    }
    $InputJson = [Console]::In.ReadToEnd()
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        exit 0
    }

    if ($Phase -eq "pre") {
        $env:CLAUDE_HOOK_EVENT_NAME = "PreToolUse"
        $HookEvent = "PreToolUse"
    } else {
        $env:CLAUDE_HOOK_EVENT_NAME = "PostToolUse"
        $HookEvent = "PostToolUse"
    }
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"
    $env:PROJECT_DIR = $ProjectDir
    $env:HOOK_EVENT = $HookEvent
    $env:COPILOT_INPUT_JSON = $InputJson
    $PythonScript = @'
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.instincts import append_instinct_observation

_FIRST_CAP_RE = re.compile(r"(.)([A-Z][a-z]+)")
_ALL_CAP_RE = re.compile(r"([a-z0-9])([A-Z])")


def _snake_case(key: str) -> str:
    step1 = _FIRST_CAP_RE.sub(r"\1_\2", key)
    return _ALL_CAP_RE.sub(r"\1_\2", step1).lower()


def _normalize(value):
    if isinstance(value, dict):
        normalized = {}
        for key, item in value.items():
            if key == "toolArgs":
                name = "tool_input"
            elif key == "toolName":
                name = "tool_name"
            else:
                name = _snake_case(key)
            normalized[name] = _normalize(item)
        return normalized
    if isinstance(value, list):
        return [_normalize(item) for item in value]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return value
        return _normalize(parsed)
    return value


raw = os.environ.get("COPILOT_INPUT_JSON", "")
try:
    payload = json.loads(raw) if raw.strip() else {}
except Exception:
    payload = {}

append_instinct_observation(
    Path(os.environ["PROJECT_DIR"]),
    engine="github_copilot",
    hook_event=os.environ["HOOK_EVENT"],
    data=_normalize(payload),
    session_id=os.environ.get("COPILOT_SESSION_ID") or os.environ.get("GITHUB_COPILOT_SESSION_ID"),
)
'@
    $PythonScript | & python - 2>$null | Out-Null
    exit 0
} catch {
    exit 0
}
