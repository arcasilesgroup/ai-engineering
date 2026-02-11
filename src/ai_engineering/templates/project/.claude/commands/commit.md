Before executing, verify these preconditions:

1. Current branch is NOT `main` or `master` (abort with warning if so).
2. Working tree has staged or unstaged changes (abort if nothing to commit).
3. Active spec is read from `.ai-engineering/context/specs/_active.md`.

Read and execute the workflow skill defined in `.ai-engineering/skills/workflows/commit.md`.

Arguments: no arguments = default flow. `--only` = restricted variant (if defined).

Follow the complete procedure. Do not skip steps. Apply all governance notes. Read the Command Contract in `.ai-engineering/manifest.yml` under `commands:` for the authoritative step sequence.

$ARGUMENTS
