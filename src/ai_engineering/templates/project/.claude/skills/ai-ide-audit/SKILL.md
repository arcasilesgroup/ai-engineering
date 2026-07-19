---
name: ai-ide-audit
description: "Audits an IDE end-to-end (instruction surface, hooks, skills, agents, installer wiring) using strict file-evidence — never assumptions. Trigger for 'audit IDE support', 'is Copilot wired up correctly', 'check Claude Code integration', 'are there orphaned hooks', 'verify IDE setup'. Accepts Claude Code, GitHub Copilot, Codex, Antigravity, or all. Not for code quality; use /ai-verify instead. Not for security scanning; use /ai-security instead."
effort: high
argument-hint: "claude-code|github-copilot|codex|antigravity|all [--fix]"
tags: [audit, ide, copilot, claude-code, governance]
---

# IDE Support Audit

Audits an IDE end-to-end — instruction surface, hooks, skills, agents, installer wiring — using strict file-evidence rather than assumptions. Use it to verify IDE setup for Claude Code, GitHub Copilot, Codex, Antigravity, or all at once, optionally auto-fixing P0 gaps.

## Quick start

```
/ai-ide-audit all              # audit all platforms
/ai-ide-audit github-copilot   # Copilot only
/ai-ide-audit claude-code      # Claude Code only
/ai-ide-audit antigravity      # Antigravity app + agy CLI
/ai-ide-audit all --fix        # audit + auto-fix P0 issues
```

## Workflow

Strict evidence-based audit of IDE support. No assumptions — every claim cites a file path.
Output is always the structured audit document, no matter how many IDEs are requested.
Principles applied: §10.1 KISS (write the report skeleton first, fail fast on missing
evidence); §10.4 DRY (skill/agent counts have one canonical source — mirrors must match it,
never re-derive).

1. **Step 0 — load contexts**: read `.ai-engineering/manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` per stack and `.ai-engineering/overrides/_shared/conventions.md`; load `.ai-engineering/team/*.md`.
2. **Write the report skeleton first** from `references/report-template.md` BEFORE collecting evidence.
3. **Dispatch a single `Explore` subagent** to read instruction surfaces, hook configs, mirror dirs, and `manifest.yml` counts.
4. **Classify each capability per platform** — SUPPORTED / PARTIAL / UNSUPPORTED — using the capability matrix.
5. **Run spec-107 advisory checks** (advisory-only per NG-11):
   - **Check 6** — agent naming consistency cross-IDE: every agent file's frontmatter `name:` must equal its slug.
   - **Check 8** — instruction-file count scan: walk every CLAUDE.md / AGENTS.md / copilot-instructions.md and validate `## Skills (N)` + `## Agents (N)` headers vs canonical counts.
6. **With `--fix`**: auto-remediate P0 issues only; re-run mirror sync; verify tests still pass.

> Detail: see [evidence collection (instruction surfaces, hooks, mirrors, sync script)](references/evidence-collection.md), [capability matrix + advisory checks + auto-fix policy](references/capability-matrix.md), [audit document skeleton](references/report-template.md).

## Common Mistakes

- Marking SUPPORTED on partial wiring just because a file exists.
- Auto-fixing P1/P2 issues with `--fix` (it only touches P0).

## Examples

### Example — full IDE sweep before a release

User: "audit every IDE we ship support for, then auto-fix the P0 issues"

```
/ai-ide-audit all --fix
```

Walks every IDE surface, scores SUPPORTED / PARTIAL / UNSUPPORTED per capability, fixes orphaned hooks and stale counts, re-runs mirror sync, re-runs unit tests.

## Integration

Triggered after: installer changes (`src/ai_engineering/installer/templates.py`), `scripts/sync_command_mirrors.py` runs, new hooks added. Calls: `python scripts/sync_command_mirrors.py` (with `--fix`). Feeds into: `/ai-governance` (risk acceptance for UNSUPPORTED gaps). See also: `/ai-verify`, `/ai-security`.

$ARGUMENTS
