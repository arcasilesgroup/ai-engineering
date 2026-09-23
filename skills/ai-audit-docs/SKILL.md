---
name: ai-audit-docs
description: >-
  Audits documentation files against actual repo state. Detects dead references (links to
  nonexistent files/URLs), false claims (doc says feature X exists but the code doesn't),
  outdated version numbers, and references to commands that don't exist. Input: path to docs
  dir or specific files (defaults to docs/ README.md AGENTS.md). Output: ranked markdown
  table of findings with severity and location. Report-only, NO auto-fix.
  Trigger phrases: "audit docs", "check documentation", "verify docs", "docs review",
  "documentation audit".
license: MIT
---

# Audit docs against repo reality

## Lifecycle

Lane: light
Writes: nothing — report-only, never modifies files
Read by: humans (consumed as a findings table)
Dies: on completion
Next: ai-verify (to validate fixes if user acts on findings)

## What it produces

A ranked markdown table of findings. Every finding names the doc file, the line, the
severity, and the broken claim.

| Severity | Meaning |
|----------|---------|
| critical | Doc points users at something that does not exist — they will hit a wall |
| warning  | Claim is outdated or inaccurate but the doc is still roughly usable |
| info     | Cosmetic: stale version number, unused anchor, minor nit |

## Steps

1. **Determine scope.** If the user gave a path, audit that. Otherwise default to
   `README.md`, `AGENTS.md`, and any `docs/` directory at the repo root. Glob for
   `**/*.md` under docs if the directory exists. Never audit vendored or generated files
   (`node_modules/`, `dist/`, `*.generated.*`).

2. **Read every target doc.** Extract all of these per file:

   - **File links:** markdown links pointing at local paths (e.g. `./path`,
     `../path`, `path/to/file`). Skip anchors (`#section`) and
     bare URLs — those are checked in step 3.
   - **External URLs:** bare `http://` / `https://` links. Collect for batch HEAD-check.
   - **Command references:** inline code or code blocks containing shell commands
     (`npm run X`, `yarn X`, `make X`, `cargo X`, `python -m X`, `npx X`). Strip
     arguments; extract just the command name.
   - **Version strings:** `v1.2.3`, `1.2.3`, `>=1.2.3`, pinned deps in prose.
   - **Feature claims:** sentences that assert existence — "supports X", "includes X",
     "has X", "provides X", "X is built-in", "X is enabled by default".

3. **Cross-check file links.** For each local path extracted from a markdown link:
   - Resolve it relative to the doc file's directory.
   - `find` or `read` to confirm the target exists. If not -> **critical** finding.

4. **Cross-check command references.** For each command name:
   - `grep` the repo for a script/package-bin definition (`package.json` scripts,
     `Makefile` targets, `Cargo.toml` bin, `setup.py`/`pyproject.toml` entry points,
     shell scripts in `bin/` or `scripts/`).
   - If no definition exists AND the command is not a well-known system binary
     (`git`, `ls`, `cat`, `curl`, `jq`, etc.) -> **warning** finding.
   - If a script IS defined, check that the arguments the doc uses still match
     the script's actual flags — flag mismatches -> **info**.

5. **Cross-check feature claims.** For each feature assertion:
   - `find` the feature name (the noun, not the sentence) in the codebase: config keys,
     source files, type definitions, exported symbols.
   - If nothing matches -> **warning** (the feature may exist under a different name;
     the finding should note "searched for X, found nothing; may be named differently").
   - If the feature exists but is behind a flag the doc doesn't mention -> **info**.

6. **Check version strings.** For each version reference found in prose:
   - Compare against the repo's actual version: `package.json` version field, `Cargo.toml`,
     `pyproject.toml`, `version.txt`, etc.
   - If the doc version is older -> **info** (may be intentional; flag as potentially stale).
   - If the doc references a version that is *higher* than what exists -> **warning**.

7. **Batch-check external URLs.** For each external URL:
   - HEAD request (timeout 5s). 404/410/DNS failure -> **critical** (dead link).
   - 403/429/connection refused -> **info** (may be rate-limited or geo-blocked; note it
     but do not flag as dead).
   - 301/302 -> follow one hop; if the final target is the same domain, note the redirect
     as **info**.

8. **Rank and output.** Sort findings by severity (critical first), then by file path.
   Output as a markdown table:

   ```
   | # | Severity | File | Line | Finding |
   |---|----------|------|------|---------|
   | 1 | critical | README.md | 42 | Link `./docs/setup.md` -> file does not exist |
   | 2 | warning  | AGENTS.md | 15 | Command `yarn deploy` not defined in any script |
   | 3 | info     | README.md | 8 | Version `v2.1.0` in doc vs `v2.3.0` in package.json |
   ```

   End with a one-line summary: `X critical, Y warnings, Z info — total N findings`.

## Anti-patterns

- **Fixing anything.** This skill is report-only. Never edit docs; the user decides
  what to fix.
- **Auditing generated files.** `dist/`, `build/`, `node_modules/`, `*.generated.*`
  are out of scope — their content is derived, not authored.
- **Failing on external URLs that are merely slow.** A 429 or timeout is not a dead
  link. Only 404/410/DNS failure are critical.
- **Over-flagging version info.** A doc pinned to an older version on purpose is info,
  not warning. The severity distinction matters.
- **Assuming feature names are unique.** When a feature claim doesn't match code, say
  "may be named differently" — don't assume absence.
- **Checking anchors inside the same doc.** `#section` links to anchors the doc itself
  defines; checking those is useful but low value and fragile. Skip unless the user
  specifically asks.

## Done when

- Every target doc has been read and all link/command/feature/version claims extracted.
- Each claim has been cross-checked against repo state or the network.
- The findings table is complete, ranked, and includes file:line for every row.
- Nothing in the repo was modified.

## Not for

- Writing or fixing docs — use /ai-write for authoring, /ai-edit or manual edits for fixes.
- Reviewing prose quality or style — use /ai-review or /humanizer.
- Diagnosing a runtime failure that happens to mention docs — use /ai-debug.
- External research about a topic the docs cover — use /ai-research.
