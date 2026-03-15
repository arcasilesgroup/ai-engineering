---
name: wiring-scanner
schedule: "0 11 * * 2"
environment: worktree
layer: scanner
owner: operate
requires: [gh]
---

# Wiring Scanner

## Prompt

Detect implemented but disconnected code: functions, modules, or exports that exist but are not connected to any entry point, route, CLI command, or consumer.

1. Read `.ai-engineering/skills/gap/SKILL.md` — follow the wiring gap detection procedure (step 5.5).
2. Scan the codebase for each wiring gap category:
   - **Route handlers** without route registration.
   - **CLI commands** without CLI wiring.
   - **Public API functions** without any caller.
   - **Event handlers** without event subscription.
   - **Exported modules** without any importer.
   - **Template/config files** without any reference.
3. For each disconnected item:
   - Check if a GitHub Issue already exists.
   - If not, create one with labels `wiring-gap`, `needs-triage`.
   - Title format: `[wiring] <type>: <symbol> in <file>`
   - Priority: `p2-high` for critical-path code, `p3-normal` for utilities.

## Context

- Uses: feature-gap skill (wiring mode).
- Reads: `src/` for Python modules.
- Cross-references: CLI registration, test imports, `__init__.py` exports.

## Safety

- Read-only mode: detect and create issues only.
- Do NOT modify source code.
- Maximum 15 issues per run.
- Skip findings that already have open issues.
- Some "disconnected" code is intentionally so (templates, plugins). Label as `needs-review`.
