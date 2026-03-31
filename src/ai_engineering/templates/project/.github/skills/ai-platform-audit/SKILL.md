---
name: ai-platform-audit
description: Use when you need to verify that an IDE platform is genuinely supported in ai-engineering — not just assumed. Trigger for 'audit platform support', 'is Copilot wired up correctly?', 'check Claude Code integration', 'are there orphaned hooks?', 'platform support audit', 'verify IDE setup', 'check platform gaps', 'are skill counts correct per platform?', 'do all hooks work?', or any time platform configuration feels off. Accepts Claude Code, GitHub Copilot, Gemini, Codex, or 'all'. Also trigger proactively after any sync-mirrors run, installer change, or new hook added.
effort: max
argument-hint: "claude-code|github-copilot|gemini|codex|all [--fix]"
mode: agent
tags: [audit, platform, copilot, claude-code, governance]
---


# Platform Support Audit

Strict evidence-based audit of IDE platform support in ai-engineering. No assumptions — every claim cites a file path. Output is always the structured report below, no matter how many platforms are requested.

## When to Use

- Verifying a platform is genuinely wired end-to-end (instruction surface → hooks → skills → agents → installer).
- After any change to `scripts/sync_command_mirrors.py`, `src/ai_engineering/installer/templates.py`, or hook files.
- When skill or agent counts look wrong across platforms.
- When a hook exists in `scripts/hooks/` but isn't firing.
- NOT for general code quality — use `/ai-verify`. NOT for security scanning — use `/ai-security`.

## Step 0: Load Stack Contexts

Follow `.ai-engineering/contexts/stack-context.md`.

---

## Start Here — Output Structure

**Before collecting any evidence, write this report skeleton.** Load report skeleton from `references/report-template.md`.

---

## Evidence Collection

Dispatch a single `Explore` subagent. It reads the files below and returns raw facts. You classify them into the matrix.

**Instruction Surfaces** — what each IDE reads as its primary directive:

| File | Consumed by |
|------|-------------|
| `CLAUDE.md` | Claude Code only |
| `.github/copilot-instructions.md` | GitHub Copilot only |
| `AGENTS.md` | Codex only (NOT Copilot, NOT Gemini) |
| `GEMINI.md` | Gemini only |
| `.claude/settings.json` hooks | Claude Code only |
| `.github/hooks/hooks.json` hooks | GitHub Copilot only |

**Critical invariants** — any violation is at minimum PARTIAL:
1. `AGENTS.md` Source-of-Truth table uses `.codex/` paths (never `.<ide>/`)
2. Copilot skill count = total - count of `copilot_compatible: false` skills
3. Every `copilot-*.sh` in `scripts/hooks/` must appear in `.github/hooks/hooks.json`
4. `_PROVIDER_TREE_MAPS["github_copilot"]` must include `("agents", ".github/agents")`

**Installer Wiring** (`src/ai_engineering/installer/templates.py`):
- `_PROVIDER_FILE_MAPS` — instruction files per provider
- `_PROVIDER_TREE_MAPS` — directory trees per provider (skills, agents, hooks)

**Hook Surfaces**:
- Claude Code: `.claude/settings.json` → `hooks` array (list every entry)
- GitHub Copilot: `.github/hooks/hooks.json` → all hook types (list every entry)
- Disk scan: list every `.sh` and `.ps1` in `.ai-engineering/scripts/hooks/` — any not referenced in either hooks file is an **orphaned hook**

**Skill Compatibility**:
- Count directories in `.github/skills/`, `.github/skills/`, `.codex/skills/`, `.gemini/skills/`
- Scan all `.github/skills/*/SKILL.md` frontmatter for `copilot_compatible: false`
- Read `skills.total` from `.ai-engineering/manifest.yml`
- Expected: `.github/skills/` count = `.github/skills/` count − (number of `copilot_compatible: false` skills)

**Agent Distribution**:
- Count files in `.github/agents/`, `.github/agents/`, `.codex/agents/`, `.gemini/agents/`
- Compare against `agents.total` in manifest

**Counter Cross-Check**:
- Extract `Skills (N)` and `Agents (N)` from each instruction file
- Canonical files (CLAUDE.md, AGENTS.md, GEMINI.md) must match `skills.total`
- Copilot file is allowed to be lower by exactly the number of `copilot_compatible: false` skills

**Sync Script** (`scripts/sync_command_mirrors.py`):
- `generate_agents_md()` — AGENTS.md Source-of-Truth paths must use `.codex/` (not `.<ide>/`)
- `generate_copilot_instructions()` — must call `is_copilot_compatible()` to filter count

---

## Filling the Matrix

After the Explore subagent returns, classify each capability for each in-scope platform:

| Capability | What to check | SUPPORTED if… |
|-----------|--------------|---------------|
| Instruction Surface | File exists, has content, correct `Skills (N)` | File found, count accurate |
| Hooks Wired | All hook scripts on disk appear in hooks config | Zero orphaned hooks |
| Skills Distributed | Mirror dir exists, count = expected | Count matches formula |
| Agents Distributed | Mirror dir exists, count = manifest total | Count matches manifest |
| Skill Count Accurate | Instruction file N = actual dir count | Exact match (or Copilot delta correct) |
| Agent Count Accurate | Instruction file N = manifest agents.total | Exact match |
| Installer Coverage | `_PROVIDER_TREE_MAPS` and `_PROVIDER_FILE_MAPS` entries present | All entries found |

Mark PARTIAL whenever you find evidence of the capability but with a measurable gap. Mark UNSUPPORTED only when the capability is completely absent.

---

## Auto-Fix P0 Issues

`--fix` only auto-remediates P0 issues. P1 and P2 are reported for manual action.

When TARGET_PLATFORM matches the fix scope, auto-fix these unambiguous P0s:
- Orphaned `copilot-*` hook → add entry to `.github/hooks/hooks.json`
- Wrong skill count in instruction file → run `python scripts/sync_command_mirrors.py`
- AGENTS.md Source-of-Truth uses `.<ide>/` placeholder → revert to `.codex/`

After fixing: re-run `python scripts/sync_command_mirrors.py` then verify:
```bash
source .venv/bin/activate && python -m pytest tests/unit/ -q
```
Do not mark the audit complete if tests fail.

---

## Quick Reference

```
/ai-platform-audit all              # audit all platforms
/ai-platform-audit github-copilot   # Copilot only
/ai-platform-audit claude-code      # Claude Code only
/ai-platform-audit all --fix        # audit + auto-fix P0 issues
```

## Integration

- **Triggered after**: installer changes, sync-mirrors runs, new hook added
- **Calls**: `python scripts/sync_command_mirrors.py` (when fixing sync-generated files)
- **Feeds into**: `/ai-governance` for risk acceptance of UNSUPPORTED gaps

$ARGUMENTS
