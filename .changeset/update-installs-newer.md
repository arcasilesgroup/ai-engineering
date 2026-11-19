---
"ai-engineering": minor
---

`ai-eng update` now brings you up to date in one command. It reads the registry once (3 s); when a newer ai-eng exists it shows the version and the release notes, asks, installs it with the package manager that installed ai-eng (`bun add -g` or `npm install -g`), checks that the `ai-eng` on PATH is the new one, and runs it to sync the machine and the repo. With no terminal and no `--yes` it installs nothing and prints the command. Offline, it syncs exactly as before. Outside a repo it updates the machine side only.

Every human command now ends with up to two lines: a newer ai-eng on the registry, and a repo installed by an older ai-eng than the one running. The registry is read at most once a day, and a failed read is remembered too, so a bad network costs one 3 s wait a day instead of up to 30 s on every command. Claude Code and Codex get the same two lines at session start through a new `SessionStart` hook, read from the cache with no network. `AI_ENG_NO_UPDATE_NOTICES=1` or `[notices] enabled = false` still turns all of it off.
