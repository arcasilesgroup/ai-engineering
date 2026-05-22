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

## Per-IDE assertion lookup (current native paths)

| IDE | Native instruction path | Workspace assets | md_mirror / sync contract |
|-----|-------------------------|------------------|---------------------------|
| Claude Code | `<repo>/CLAUDE.md` | `<repo>/.claude/skills`, `<repo>/.claude/agents` | Enforced — byte-equivalent canonical payload (sha256) |
| GitHub Copilot | `<repo>/.github/copilot-instructions.md` | `<repo>/.github/skills`, `<repo>/.github/agents` | Enforced — byte-equivalent canonical payload (sha256) |
| Codex | `<repo>/AGENTS.md` | `<repo>/.codex/skills`, `<repo>/.codex/agents` | Enforced — `<repo>/.codex/AGENTS.md` MUST NOT exist |
| Antigravity | `<repo>/AGENTS.md` | `<repo>/.agents/skills`, `<repo>/.agents/agents`, `agy` runtime diagnostics | Enforced — `.agents/` generated from canonical `.claude/`; audit remains PARTIAL until hook fixtures prove full coverage |

## Spec-151 Antigravity Probe

Antigravity app and `agy` CLI are one surface. Audit classification uses
file evidence plus deterministic CLI diagnostics:

- **SUPPORTED**: `AGENTS.md` exists, `.agents/skills` and `.agents/agents`
  match canonical counts, and `agy --version` is available when CLI runtime
  support is in scope.
- **PARTIAL**: workspace assets are present but CLI runtime is missing, or
  hook payload evidence is insufficient for full audit coverage.
- **UNSUPPORTED**: `AGENTS.md` or `.agents/` assets are missing.

## Spec-107 Advisory Checks (6/8)

Advisory-only per spec-107 NG-11 (never hard-fail; hard-gate lands in a future spec when ≥90% projects pass cleanly).

- **Check 6 — Agent naming**: for every agent file across `.claude`/`.github`/`.codex`/`.agents`/agents, flag when `name != basename(file).removesuffix(".md")`. Catches Explorer-style slug drift.
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
