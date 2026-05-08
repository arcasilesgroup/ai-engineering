---
name: ai-platform-audit
description: "Audits an IDE platform end-to-end (instruction surface, hooks, skills, agents, installer wiring) using strict file-evidence — never assumptions. Trigger for 'audit platform support', 'is Copilot wired up correctly', 'check Claude Code integration', 'are there orphaned hooks', 'verify IDE setup'. Accepts Claude Code, GitHub Copilot, Gemini, Codex, or all. Not for code quality; use /ai-verify instead. Not for security scanning; use /ai-security instead."
effort: max
argument-hint: "claude-code|github-copilot|gemini|codex|all [--fix]"
tags: [audit, platform, copilot, claude-code, governance]
---

# Platform Support Audit

## Quick start

```
/ai-platform-audit all              # audit all platforms
/ai-platform-audit github-copilot   # Copilot only
/ai-platform-audit claude-code      # Claude Code only
/ai-platform-audit all --fix        # audit + auto-fix P0 issues
```

## Workflow

Strict evidence-based audit of IDE platform support in ai-engineering. No assumptions — every claim cites a file path. Output is always the structured report below, no matter how many platforms are requested.

1. Write the report skeleton from `references/report-template.md` BEFORE collecting evidence.
2. Dispatch a single `Explore` subagent to read instruction surfaces, hook configs, mirror dirs, and `manifest.yml` counts.
3. Classify each capability per platform (SUPPORTED / PARTIAL / UNSUPPORTED) using the matrix below.
4. Run Spec-107 advisory checks (6/7/8) — agent naming, GEMINI.md skill count, generic count scan.
5. With `--fix`, auto-remediate P0 issues only; re-run mirror sync; verify tests still pass.

## When to Use

- Verifying a platform is genuinely wired end-to-end (instruction surface → hooks → skills → agents → installer).
- After any change to `scripts/sync_command_mirrors.py`, `src/ai_engineering/installer/templates.py`, or hook files.
- When skill or agent counts look wrong across platforms.
- When a hook exists in `scripts/hooks/` but isn't firing.
- NOT for general code quality — use `/ai-verify`. NOT for security scanning — use `/ai-security`.

Step 0 (load contexts): per `.ai-engineering/contexts/stack-context.md`.

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

Any violation of the four checks below (paths use `.codex/`, copilot count formula, hooks not orphaned, tree maps include `.github/agents`) is at minimum PARTIAL.

**Installer Wiring** (`src/ai_engineering/installer/templates.py`):
- `_PROVIDER_FILE_MAPS` — instruction files per provider
- `_PROVIDER_TREE_MAPS` — directory trees per provider (skills, agents, hooks)

**Hook Surfaces**:
- Claude Code: `.claude/settings.json` → `hooks` array (list every entry)
- GitHub Copilot: `.github/hooks/hooks.json` → all hook types (list every entry)
- Disk scan: list every `.sh` and `.ps1` in `.ai-engineering/scripts/hooks/` — any not referenced in either hooks file is an **orphaned hook**

**Skill / Agent Distribution + Counter Cross-Check**:
- Count directories in `.claude/skills/`, `.github/skills/`, `.codex/skills/`, `.gemini/skills/`; same for `.claude/agents/` etc.
- Scan `.claude/skills/*/SKILL.md` frontmatter for `copilot_compatible: false`; read `skills.total` and `agents.total` from `.ai-engineering/manifest.yml`.
- Expected: canonical mirrors (Claude/Codex/Gemini) match manifest totals exactly; `.github/skills/` is lower by exactly the `copilot_compatible: false` count.
- Cross-check `Skills (N)` and `Agents (N)` extracted from each instruction file against the same formula.

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

## Spec-107 Advisory Checks (6/7/8)

Advisory-only per spec-107 NG-11 (never hard-fail; hard-gate lands in a
future spec when ≥90% projects pass cleanly).

- **Check 6 — Agent naming**: for every agent file across `.claude`/`.github`/`.codex`/`.gemini`/agents, flag when `name != basename(file).removesuffix(".md")`. Catches Explorer-style slug drift.
- **Check 7 — GEMINI.md count**: extract `N` from `## Skills (N)`; compare with `len(glob(".gemini/skills/ai-*/SKILL.md"))`. Catches `__SKILL_COUNT__` placeholder removal.
- **Check 8 — Generic count scan**: regex `^## Skills \((\d+)\)$` / `^## Agents \((\d+)\)$` across every instruction file; compare to `manifest.yml` `skills.total` / `agents.total`. Defense-in-depth across future IDE adapters.

Severity: advisory WARN. Remediation: re-run `ai-eng sync`.

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

## Examples

### Example 1 — full platform sweep before a release

User: "audit every IDE platform we ship support for, then auto-fix the P0 issues"

```
/ai-platform-audit all --fix
```

Walks every IDE surface, scores SUPPORTED / PARTIAL / UNSUPPORTED per capability, fixes orphaned hooks and stale counts, re-runs mirror sync, re-runs unit tests.

### Example 2 — quick Copilot health check after sync

User: "did the sync_command_mirrors run leave Copilot in a good state?"

```
/ai-platform-audit github-copilot
```

Verifies `.github/copilot-instructions.md`, `.github/hooks/hooks.json`, `.github/skills/`, `.github/agents/` against the canonical formula and flags any drift.

## Integration

Triggered after: installer changes, `sync_command_mirrors.py` runs, new hooks added. Calls: `python scripts/sync_command_mirrors.py` (with `--fix`). Feeds into: `/ai-governance` (risk acceptance for UNSUPPORTED gaps). See also: `/ai-verify`, `/ai-security`.

$ARGUMENTS
