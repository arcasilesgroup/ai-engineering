# Filling the Capability Matrix

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

## Spec-107 Advisory Checks (6/7/8)

Advisory-only per spec-107 NG-11 (never hard-fail; hard-gate lands in a future spec when ≥90% projects pass cleanly).

- **Check 6 — Agent naming**: for every agent file across `.claude`/`.github`/`.codex`/`.gemini`/agents, flag when `name != basename(file).removesuffix(".md")`. Catches Explorer-style slug drift.
- **Check 7 — GEMINI.md count**: extract `N` from `## Skills (N)`; compare with `len(glob(".gemini/skills/ai-*/SKILL.md"))`. Catches `__SKILL_COUNT__` placeholder removal.
- **Check 8 — Generic count scan**: regex `^## Skills \((\d+)\)$` / `^## Agents \((\d+)\)$` across every instruction file; compare to `manifest.yml` `skills.total` / `agents.total`. Defense-in-depth across future IDE adapters.

Severity: advisory WARN. Remediation: re-run `ai-eng sync`.

## Auto-Fix P0 Issues (`--fix`)

`--fix` only auto-remediates P0 issues. P1 and P2 are reported for manual action.

When TARGET_PLATFORM matches the fix scope, auto-fix these unambiguous P0s:

- Orphaned `copilot-*` hook → add entry to `.github/hooks/hooks.json`.
- Wrong skill count in instruction file → run `python scripts/sync_command_mirrors.py`.
- AGENTS.md Source-of-Truth uses `.<ide>/` placeholder → revert to `.codex/`.

After fixing: re-run `python scripts/sync_command_mirrors.py` then verify:

```bash
source .venv/bin/activate && python -m pytest tests/unit/ -q
```

Do not mark the audit complete if tests fail.
