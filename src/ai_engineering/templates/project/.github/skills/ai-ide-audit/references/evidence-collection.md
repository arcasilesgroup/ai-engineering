# Evidence Collection

Dispatch a single `Explore` subagent. It reads the files below and returns raw facts. You classify them into the matrix.

## Instruction Surfaces — what each IDE reads as its primary directive

| File | Consumed by |
|------|-------------|
| `CLAUDE.md` | Claude Code only |
| `.github/copilot-instructions.md` | GitHub Copilot only |
| `AGENTS.md` | Codex only (NOT Copilot, NOT Gemini) |
| `GEMINI.md` | Gemini only |
| `.claude/settings.json` hooks | Claude Code only |
| `.github/hooks/hooks.json` hooks | GitHub Copilot only |

Any violation of the four checks below (paths use `.codex/`, copilot count formula, hooks not orphaned, tree maps include `.github/agents`) is at minimum PARTIAL.

## Installer Wiring (`src/ai_engineering/installer/templates.py`)

- `_PROVIDER_FILE_MAPS` — instruction files per provider
- `_PROVIDER_TREE_MAPS` — directory trees per provider (skills, agents, hooks)

## Hook Surfaces

- Claude Code: `.claude/settings.json` → `hooks` array (list every entry)
- GitHub Copilot: `.github/hooks/hooks.json` → all hook types (list every entry)
- Disk scan: list every `.sh` and `.ps1` in `.ai-engineering/scripts/hooks/` — any not referenced in either hooks file is an **orphaned hook**

## Skill / Agent Distribution + Counter Cross-Check

- Count directories in `.github/skills/`, `.github/skills/`, `.codex/skills/`, `.gemini/skills/`; same for `.github/agents/` etc.
- Scan `.github/skills/*/SKILL.md` frontmatter for `copilot_compatible: false`; read `skills.total` and `agents.total` from `.ai-engineering/manifest.yml`.
- Expected: canonical mirrors (Claude/Codex/Gemini) match manifest totals exactly; `.github/skills/` is lower by exactly the `copilot_compatible: false` count.
- Cross-check `Skills (N)` and `Agents (N)` extracted from each instruction file against the same formula.

## Sync Script (`scripts/sync_command_mirrors.py`)

- `generate_agents_md()` — AGENTS.md Source-of-Truth paths must use `.codex/` (not `.<ide>/`).
- `generate_copilot_instructions()` — must call `is_copilot_compatible()` to filter count.
