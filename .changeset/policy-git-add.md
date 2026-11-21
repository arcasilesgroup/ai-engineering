---
"ai-engineering": patch
---

The command-scope policy no longer blocks `git add` of a file whose name contains "token", "secret" or "credential" (a design-token `tokens.json`, a `secrets-handling.md` page). `git add` copies files into the repository's index; it does not write the files it names, so those paths are now judged as reads, the way `git commit` already judged its message. A real write to such a path is still refused, and a secret staged by mistake is still stopped by the gitleaks commit floor.
