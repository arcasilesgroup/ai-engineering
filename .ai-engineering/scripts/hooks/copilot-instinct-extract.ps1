# Copilot wrapper for instinct-extract.py.
# Fail-open: exit 0 always.

$ErrorActionPreference = "Stop"
try {
    $ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $ProjectDir = [string](Resolve-Path (Join-Path $ScriptDir "../../.."))
    if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
        exit 0
    }
    $env:CLAUDE_HOOK_EVENT_NAME = "Stop"
    if (-not $env:CLAUDE_PROJECT_DIR) { $env:CLAUDE_PROJECT_DIR = $ProjectDir }
    $env:AIENG_HOOK_ENGINE = "github_copilot"
    $env:PROJECT_DIR = $ProjectDir
    $PythonScript = @'
import os, sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["PROJECT_DIR"]) / ".ai-engineering" / "scripts" / "hooks"))
from _lib.instincts import extract_instincts
from _lib.observability import emit_framework_operation

project_root = Path(os.environ["PROJECT_DIR"])
if extract_instincts(project_root):
    emit_framework_operation(
        project_root,
        operation="instinct-extract",
        component="hook.instinct-extract",
        source="hook",
        metadata={"engine": os.environ.get("AIENG_HOOK_ENGINE", "github_copilot")},
    )
'@
    $PythonScript | & python - 2>$null | Out-Null
    exit 0
} catch {
    exit 0
}
