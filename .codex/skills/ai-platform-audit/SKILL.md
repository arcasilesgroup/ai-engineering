---
name: ai-platform-audit
description: Use when you need to verify that an IDE platform is genuinely supported in ai-engineering — not just assumed. Trigger for 'audit platform support', 'is Copilot wired up correctly?', 'check Claude Code integration', 'are there orphaned hooks?', 'platform support audit', 'verify IDE setup', 'check platform gaps', 'are skill counts correct per platform?', 'do all hooks work?', or any time platform configuration feels off. Accepts Claude Code, GitHub Copilot, Gemini, Codex, or 'all'. Also trigger proactively after any sync-mirrors run, installer change, or new hook added.
effort: max
argument-hint: "claude-code|github-copilot|gemini|codex|all [--fix]"
tags: [audit, platform, copilot, claude-code, governance]
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-platform-audit/SKILL.md
edit_policy: generated-do-not-edit
---


# Platform Support Audit

Strict evidence-based audit of IDE platform support in ai-engineering. No assumptions — every claim cites a file path. Output is always the structured report below, no matter how many platforms are requested.

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
- Count directories in `.codex/skills/`, `.github/skills/`, `.codex/skills/`, `.gemini/skills/`; same for `.codex/agents/` etc.
- Scan `.codex/skills/*/SKILL.md` frontmatter for `copilot_compatible: false`; read `skills.total` and `agents.total` from `.ai-engineering/manifest.yml`.
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

These three checks are **advisory-only** per spec-107 NG-11. They surface
naming + count drift across IDE surfaces but never hard-fail. Hard-gate
enforcement lands in a future spec when ≥90% of projects pass cleanly.

### Check 6 — Agent naming consistency cross-IDE

For every agent file under `.codex/agents/`, `.github/agents/`,
`.codex/agents/`, and `.gemini/agents/`, extract the front-matter
`name:` field. Flag whenever:

```
name != basename(file).removesuffix(".agent.md").removesuffix(".md")
```

This catches future Explorer-style mismatches where the on-disk filename
diverges from the canonical agent slug (e.g., `explore.agent.md` declaring
`name: Explorer` instead of `ai-explore`). Spec-107 D-107-03 normalised the
explore agent to `ai-explore`; Check 6 ensures every other Copilot agent
keeps slug parity going forward.

Severity: **advisory WARN**. Output lists the file path, observed name,
expected slug, and remediation pointer (`scripts/sync_command_mirrors.py`).

### Check 7 — GEMINI.md skill count freshness

Extract the count `N` from the `## Skills (N)` header in `.gemini/GEMINI.md`.
Compare with `len(glob(".gemini/skills/ai-*/SKILL.md"))` (the disk reality).
Flag any mismatch.

Spec-107 D-107-04 replaced the hand-maintained count with a
`__SKILL_COUNT__` placeholder rendered by
`scripts/sync_command_mirrors.py write_gemini_md`; Check 7 detects future
template drift where the placeholder is accidentally removed and replaced
with a stale literal.

Severity: **advisory WARN**. Remediation: re-run `ai-eng sync`.

### Check 8 — Generic instruction-file count scan

Walk every canonical instruction file and extract h2 count headers. Surface
covered:

- `CLAUDE.md`
- `AGENTS.md`
- `.github/copilot-instructions.md`
- `.gemini/GEMINI.md`

For each file, regex match `^## Skills \((\d+)\)$` and `^## Agents \((\d+)\)$`.
Compare each captured `N` against the canonical count from
`.ai-engineering/manifest.yml` (`skills.total`, `agents.total`). Flag any
mismatch with the source file path so reviewers can trace drift.

This is defense-in-depth: even if a future IDE adapter introduces a new
instruction file, the regex pattern is generic enough to catch stale counts
across the whole surface.

Severity: **advisory WARN**. Remediation: re-run `ai-eng sync`.

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
