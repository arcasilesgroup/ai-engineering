# Copilot preToolUse deny-list hook.
# PowerShell stub for Windows compatibility.
# Fail-open: exit 0 always.

$ErrorActionPreference = "SilentlyContinue"
try {
    # TODO: implement deny logic for Windows
    exit 0
} catch {
    exit 0
}
