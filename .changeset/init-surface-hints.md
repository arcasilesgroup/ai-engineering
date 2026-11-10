---
"ai-engineering": patch
---

Every ai-eng question now shows only the titles of its options, without a description beside them:

- **Surface picker (`init` and `config`):** only the surface names (Claude Code, Cursor, GitHub Copilot (CLI + VS Code)…). The capability notes, which ran to six lines for Copilot, are gone. `ai-eng doctor` still shows them, and `init` still warns after the pick when a surface cannot block tool calls.
- **Re-running `init` on a governed repo:** the choices read "Update ai-eng's files", "Change agent surfaces" and "Exit".
- **`uninstall`:** the choices read "This project", "Everything" and "Cancel". The block above the question still explains what each scope removes.
