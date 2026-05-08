---
name: ai-ide-audit
description: Audits an IDE end-to-end (instruction surface, hooks, skills, agents, installer wiring) using strict file-evidence — never assumptions. Trigger for 'audit IDE support', 'is Copilot wired up correctly', 'check Claude Code integration', 'are there orphaned hooks', 'verify IDE setup'. Accepts Claude Code, GitHub Copilot, Gemini, Codex, or all. Not for code quality; use /ai-verify instead. Not for security scanning; use /ai-security instead.
effort: max
argument-hint: "claude-code|github-copilot|gemini|codex|all [--fix]"
tags: [audit, ide, copilot, claude-code, governance]
mirror_family: gemini-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-ide-audit/SKILL.md
edit_policy: generated-do-not-edit
---


# IDE Support Audit

## Quick start

```
/ai-ide-audit all              # audit all platforms
/ai-ide-audit github-copilot   # Copilot only
/ai-ide-audit claude-code      # Claude Code only
/ai-ide-audit all --fix        # audit + auto-fix P0 issues
```

## Workflow

Strict evidence-based audit of IDE support in ai-engineering. No assumptions — every claim cites a file path. Output is always the structured audit document, no matter how many IDEs are requested.

1. **Write the report skeleton first** from `references/report-template.md` BEFORE collecting evidence.
2. **Dispatch a single `Explore` subagent** to read instruction surfaces, hook configs, mirror dirs, and `manifest.yml` counts.
3. **Classify each capability per platform** (SUPPORTED / PARTIAL / UNSUPPORTED) using the capability matrix.
4. **Run spec-107 advisory checks** (advisory-only per NG-11):
   - **Check 6** — agent naming consistency cross-IDE: every agent file's frontmatter `name:` must equal its slug.
   - **Check 7** — GEMINI.md skill count freshness: extract `## Skills (N)` from rendered GEMINI.md and compare against disk count.
   - **Check 8** — generic instruction-file count scan: walk every CLAUDE.md / AGENTS.md / GEMINI.md / copilot-instructions.md and validate `## Skills (N)` + `## Agents (N)` headers vs canonical counts.
5. **With `--fix`**, auto-remediate P0 issues only; re-run mirror sync; verify tests still pass.

> Detail: see [evidence collection (instruction surfaces, hooks, mirrors, sync script)](references/evidence-collection.md), [capability matrix + advisory checks + auto-fix policy](references/capability-matrix.md), [audit document skeleton](references/report-template.md).

## When to Use

- Verifying an IDE is genuinely wired end-to-end (instruction surface → hooks → skills → agents → installer).
- After any change to `scripts/sync_command_mirrors.py`, `src/ai_engineering/installer/templates.py`, or hook files.
- When skill or agent counts look wrong across IDEs.
- When a hook exists in `scripts/hooks/` but isn't firing.
- NOT for general code quality — use `/ai-verify`. NOT for security scanning — use `/ai-security`.

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

## Common Mistakes

- Filling the matrix before collecting evidence (write the skeleton first).
- Marking SUPPORTED on partial wiring just because a file exists.
- Auto-fixing P1/P2 issues with `--fix` (it only touches P0).
- Skipping the post-fix unit test run.

## Examples

### Example 1 — full IDE sweep before a release

User: "audit every IDE we ship support for, then auto-fix the P0 issues"

```
/ai-ide-audit all --fix
```

Walks every IDE surface, scores SUPPORTED / PARTIAL / UNSUPPORTED per capability, fixes orphaned hooks and stale counts, re-runs mirror sync, re-runs unit tests.

### Example 2 — quick Copilot health check after sync

User: "did the sync_command_mirrors run leave Copilot in a good state?"

```
/ai-ide-audit github-copilot
```

Verifies `.github/copilot-instructions.md`, `.github/hooks/hooks.json`, `.github/skills/`, `.github/agents/` against the canonical formula and flags any drift.

## Integration

Triggered after: installer changes, `sync_command_mirrors.py` runs, new hooks added. Calls: `python scripts/sync_command_mirrors.py` (with `--fix`). Feeds into: `/ai-governance` (risk acceptance for UNSUPPORTED gaps). See also: `/ai-verify`, `/ai-security`.

$ARGUMENTS
