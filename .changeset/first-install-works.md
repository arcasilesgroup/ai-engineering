---
"ai-engineering": patch
---

First install works on Windows, and for anyone who already had a settings file.

- `ai-eng init` now merges its hooks into an existing `~/.claude/settings.json`, `~/.codex/hooks.json` or `~/.copilot/hooks/ai-eng.json`. 3.0.0 refused to touch any existing settings file, so every person who already used the host got no hooks at all, and `uninstall` could not take them back out.
- A denial on Claude Code no longer ends the whole turn. The deny carried `continue: false`, which Claude Code reads even on exit 2 and which stops the agent entirely; it now exits 2 with the reason on stderr, so the agent reads why and goes on. On `Stop` this also makes the checkpoint gate keep the turn going instead of ending it.
- On Windows, hook lines call `ai-eng.cmd` (npm) or `ai-eng.exe` (bun) instead of a bare `ai-eng`, which PowerShell resolves to `ai-eng.ps1` and the default Restricted execution policy refuses to run. Claude's lines also carry the exit status through PowerShell, which otherwise turned a denial into an allow.
- On Windows, `init` and `update` remove npm's `ai-eng.ps1` for this package, so a bare `ai-eng` works in PowerShell too: for Cursor, whose shared repo hook has no per-OS line, and for a person typing `ai-eng init`.
- The Copilot hook file gains a `powershell` line beside the POSIX one: the old guard was POSIX-only, and Copilot fails closed, so every tool call was denied on Windows. The same guarded file now serves the repo and the machine scope.
- VS Code Copilot is covered by the Copilot surface (it reads the same hook files): pick "GitHub Copilot (CLI + VS Code)", or pass `--surface vscode`.
- New `first-install` CI job: installs the package, inits each surface and runs every written hook line in PowerShell 5.1 (also under the Restricted policy), pwsh, cmd and Git Bash on Windows, Linux and macOS.
