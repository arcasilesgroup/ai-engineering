---
spec: spec-087
title: "Native IDE Directory Architecture -- Eliminate .agents/, Native Hooks Per IDE"
status: approved
effort: large
---

# spec-087: Native IDE Directory Architecture

## Summary

The current multi-IDE mirror system uses `.agents/` as a "generic" directory shared between Gemini CLI and Codex. This is wrong on multiple levels:

1. **Gemini CLI has its own native `.gemini/` directory** with full support for settings.json, hooks, skills, and agents. Yet we also copy `.agents/` redundantly.
2. **Codex CLI has its own native `.codex/` directory** that supports skills, hooks (`.codex/hooks.json`), and config (`config.toml`). We don't generate `.codex/` at all.
3. **The Gemini hooks format is incorrect** -- our template uses a flat format but the official schema requires nested `matcher/hooks` arrays.
4. **Codex has zero hooks** -- no telemetry, no deny-list, no instinct learning, no auto-format.
5. **GitHub Copilot hooks exist and are fully implemented** -- but never referenced in documentation tables.
6. **GEMINI.md has a bug** (line 114: says Claude Code uses `.gemini/` paths).
7. **CLAUDE.md is stale** (line 116: lumps Gemini with Codex under `.agents/`).

Each IDE should use ONLY its native directory with correct, natively-formatted hooks.

## Goals

- G1: Eliminate the `.agents/` directory entirely from the framework. All content migrates to `.codex/`.
- G2: Create `.codex/skills/` and `.codex/agents/` mirrors with correct Codex-native formatting.
- G3: Create `.codex/hooks.json` with all 9 hooks in Codex-native format (nested matcher/hooks, same as Claude).
- G4: Rewrite `.gemini/settings.json` hooks to the official nested `matcher/hooks` array format with `hooksConfig` key.
- G5: Update `sync_command_mirrors.py` to generate `.codex/` instead of `.agents/`, and fix Gemini hooks generation.
- G6: Update the installer (`templates.py`, `autodetect.py`, `operations.py`) so Codex maps to `.codex/` and Gemini no longer copies `.agents/`.
- G7: Fix all instruction files (CLAUDE.md, GEMINI.md, AGENTS.md) platform mirrors tables.
- G8: Update the validator to check `.codex/` mirrors and Gemini mirrors (currently only Copilot is validated).
- G9: Update all tests (`test_sync_mirrors.py`, `test_validator.py`, `test_autodetect.py`, etc.) for the new structure.
- G10: Achieve hooks parity -- every IDE gets the same logical hooks adapted to its native format.

## Non-Goals

- NG1: Changing the content of skills or agents (only directory/format changes).
- NG2: Adding NEW hook types beyond what we already have (telemetry, injection guard, compact, mcp-health, instinct, observe, auto-format).
- NG3: Modifying Claude Code's `.claude/` structure (it's already correct).
- NG4: Modifying GitHub Copilot's `.github/` structure (it's already correct and fully implemented).
- NG5: Implementing Codex agent personas via config.toml `[agents]` (Codex doesn't support .md agent files natively; we place .md files in `.codex/agents/` for cross-IDE consistency and future-proofing, accepting they won't be auto-loaded by Codex today).

## Decisions

### D-087-01: `.agents/` is fully replaced by `.codex/`

**Choice:** Delete all `.agents/` directories (root, templates). Codex content goes to `.codex/skills/` and `.codex/agents/`.

**Rationale:** Codex CLI natively reads `.codex/skills/<name>/SKILL.md` (confirmed from `codex-rs/core-skills/src/loader.rs`). The `.agents/skills/` path was also scanned but as an additional alias, not the primary location. Using `.codex/` is cleaner, native, and allows adding `hooks.json` and `config.toml` alongside skills.

### D-087-02: Gemini hooks use the official nested format

**Choice:** Rewrite `.gemini/settings.json` to use the nested `{ matcher: "pattern", hooks: [{ type: "command", ... }] }` structure per the official Gemini CLI schema.

**Rationale:** The current flat format (`{ name, command, matcher: { tool_names: [...] } }`) does not match the official schema at `github.com/google-gemini/gemini-cli/main/schemas/settings.schema.json`. Hooks will silently fail or be ignored.

### D-087-03: Gemini installer stops copying `.agents/`

**Choice:** Remove `(".agents", ".agents")` from `_PROVIDER_TREE_MAPS["gemini"]` in `templates.py`.

**Rationale:** Gemini CLI has full native support via `.gemini/`. When both `.gemini/skills/` and `.agents/skills/` exist, `.agents/` takes precedence (per Gemini's `skillManager.ts`), which can cause confusion if they diverge. Single source is safer.

### D-087-04: Codex hooks use hooks.json with same nested structure as Claude

**Choice:** Generate `.codex/hooks.json` with the 5 Codex-supported events: `PreToolUse`, `PostToolUse`, `SessionStart`, `UserPromptSubmit`, `Stop`.

**Rationale:** Codex CLI's hook format (from `codex-rs/hooks/src/engine/`) uses the same nested `matcher/hooks` array structure as Claude Code. Per-IDE fields differ: Codex supports `statusMessage` (Claude doesn't), and Codex uses CWD-relative paths instead of `$CLAUDE_PROJECT_DIR`. Same Python scripts, different path prefixes.

### D-087-05: AGENTS.md is kept as Codex instruction file

**Choice:** Keep `AGENTS.md` at root. It's the native instruction file for Codex and also read by Copilot and Gemini as fallback.

**Rationale:** Codex reads `AGENTS.md` as its primary instruction file (hardcoded default). Removing it would break Codex instruction loading. Copilot also reads it alongside `CLAUDE.md` and `GEMINI.md`.

### D-087-06: Codex agents go in `.codex/agents/` as .md files

**Choice:** Place agent .md files in `.codex/agents/` even though Codex CLI doesn't natively read them from that path.

**Rationale:** Codex agents are currently defined via `config.toml [agents]` table, not .md files. However: (a) the agent .md files serve as documentation and cross-IDE consistency, (b) Codex may add native agent .md support in the future (Gemini and Copilot already have it), (c) the `sync_command_mirrors.py` script generates them uniformly. We accept they're passive in Codex today.

### D-087-07: Environment variables per IDE in hook scripts

**Choice:** Hook scripts detect the current IDE via environment variables and adapt paths accordingly:
- Claude Code: `$CLAUDE_PROJECT_DIR`
- Gemini CLI: `$GEMINI_PROJECT_DIR`
- GitHub Copilot: `$GITHUB_WORKSPACE` or CWD
- Codex: CWD-relative paths (see D-087-10)

**Rationale:** Each IDE sets different env vars for hook execution. The Python hooks already receive the project path via stdin JSON, so they can be IDE-agnostic by reading `cwd` from stdin.

### D-087-08: Generate `.codex/config.toml` with hooks feature flag enabled

**Choice:** Generate a minimal `.codex/config.toml` containing `codex_hooks = true` under `[features]`.

**Rationale:** Codex hooks are behind a feature flag that defaults to OFF. Without this, all hooks in `.codex/hooks.json` would be silently ignored. A minimal config.toml that only enables hooks keeps the file non-intrusive while ensuring the hooks system works.

### D-087-09: Gemini timeouts in milliseconds, Claude/Codex in seconds

**Choice:** Each IDE's settings file uses its native timeout unit. Gemini: milliseconds (e.g., `15000`). Claude/Codex: seconds (e.g., `15`). No adaptation needed in hook scripts -- the IDE handles the unit.

**Rationale:** This is a settings-level concern, not a script-level concern. The Python hook scripts don't read timeouts; the IDE enforces them. Each generated settings file uses the correct unit for its IDE.

### D-087-10: Codex hooks use CWD-relative paths

**Choice:** Codex `.codex/hooks.json` uses CWD-relative paths (e.g., `.ai-engineering/scripts/hooks/script.py`) instead of env var prefixes.

**Rationale:** Codex CLI does not set a `$CODEX_PROJECT_DIR` environment variable. It passes `cwd` in the stdin JSON payload to hooks, but the command string itself can't reference stdin. CWD-relative paths work because Codex executes hooks from the project root.

## Risks

### R1: Codex hooks feature flag is OFF by default

**Impact:** Hooks in `.codex/hooks.json` will be ignored unless users enable `codex_hooks` in `config.toml [features]`.

**Mitigation:** Document the required feature flag in AGENTS.md and in the installer output. Generate a minimal `.codex/config.toml` that enables the feature flag.

### R2: Gemini skill precedence inversion

**Impact:** If someone has both `.gemini/skills/` and `.agents/skills/` from a previous install, `.agents/` takes precedence in Gemini CLI (per `skillManager.ts`). After this migration, the stale `.agents/` would shadow the updated `.gemini/` skills.

**Mitigation:** The installer's `remove_provider` for Codex should clean up `.agents/`. Document the migration path: users upgrading should delete `.agents/` manually or run `ai-eng install --upgrade`.

### R3: Breaking change for existing Codex users

**Impact:** Users who have `.agents/skills/` configured for Codex will find their skills moved to `.codex/skills/`.

**Mitigation:** Codex still scans `.agents/skills/` as a secondary path. But we should document the change and provide a migration note. The old `.agents/` will continue to work for skills-only until users remove it.

### R4: Root `.gemini/settings.json` overwrite risk

**Impact:** The sync script will generate `.gemini/settings.json` at root. If a user has a hand-edited version with custom permissions or deny rules, the generator could overwrite their config. The template uses `"allow": ["*"]` which is permissive.

**Mitigation:** The sync script must use create-only semantics for `settings.json` files (skip if exists), same as the installer does for other files. Only skills/agents/hooks content is force-synced.

### Note: Copilot VS Code reads Claude hooks natively

VS Code Copilot inherits `.claude/settings.json` hooks automatically. This is a benefit, not a risk -- changes to Claude hooks propagate to Copilot VS Code without extra work.

## Execution Order

Phases must execute in this order due to dependencies:

1. **Phase 1 -- Templates** (parallelizable within): Create `.codex/` template structure, rewrite `.gemini/settings.json` to correct format, delete `.agents/` templates.
2. **Phase 2 -- Sync script**: Update `sync_command_mirrors.py` to target `.codex/` instead of `.agents/`, generate Gemini hooks in correct nested format, generate Codex hooks.json.
3. **Phase 3 -- Installer** (parallelizable within): Update `templates.py`, `autodetect.py`, `operations.py` for new provider mappings.
4. **Phase 4 -- Instruction files** (parallelizable, can run alongside Phase 3): Fix CLAUDE.md, GEMINI.md, AGENTS.md platform mirrors tables.
5. **Phase 5 -- Validation & state**: Update validator `_shared.py`, `file_existence.py`, `mirror_sync.py`. Check `manifest.yml` and `framework-capabilities.json` for `.agents/` references.
6. **Phase 6 -- Tests**: Update all test files for new paths. Run full test suite.
7. **Phase 7 -- Root directories**: Run sync script to generate `.codex/` at root. Delete `.agents/` at root. Verify `.gemini/settings.json` exists at root.

## References

### Official Documentation (verified March 2026)

**Claude Code:**
- Hooks: https://code.claude.com/docs/en/hooks
- Skills: https://code.claude.com/docs/en/slash-commands
- Agents: https://code.claude.com/docs/en/sub-agents
- Settings schema: https://json.schemastore.org/claude-code-settings.json

**Gemini CLI:**
- Hooks: https://geminicli.com/docs/hooks/ and https://geminicli.com/docs/hooks/reference/
- Skills: https://geminicli.com/docs/cli/skills/
- Agents: https://geminicli.com/docs/core/subagents/
- Settings schema: https://github.com/google-gemini/gemini-cli/blob/main/schemas/settings.schema.json
- Hook migration from Claude: https://github.com/google-gemini/gemini-cli/pull/14225

**GitHub Copilot:**
- Hooks (Coding Agent): https://docs.github.com/en/copilot/reference/hooks-configuration
- Hooks (VS Code): https://code.visualstudio.com/docs/copilot/customization/hooks
- Skills: https://docs.github.com/en/copilot/concepts/agents/about-agent-skills
- Agents: https://docs.github.com/en/copilot/reference/custom-agents-configuration

**Codex CLI:**
- Source: https://github.com/openai/codex
- Skills loader: `codex-rs/core-skills/src/loader.rs`
- Hooks engine: `codex-rs/hooks/src/engine/discovery.rs`
- Config schema: `codex-rs/core/config.schema.json`

### Current Hook Coverage (audit results)

| Hook | Claude | Copilot | Gemini | Codex |
|------|--------|---------|--------|-------|
| Skill telemetry | UserPromptSubmit | userPromptSubmitted | BeforeAgent | -- |
| Injection guard | PreToolUse | -- | BeforeTool | -- |
| Deny-list | settings.json deny | preToolUse deny.sh | settings.json deny | -- |
| Strategic compact | PreToolUse | preToolUse | BeforeTool | -- |
| MCP health | PreToolUse+Failure | -- | BeforeTool | -- |
| Instinct observe | Pre+PostToolUse | pre+postToolUse | Before+AfterTool | -- |
| Instinct extract | Stop | sessionEnd | AfterAgent | -- |
| Agent telemetry | PostToolUse | postToolUse | AfterTool | -- |
| Auto-format | PostToolUse | postToolUse | AfterTool | -- |
| Session lifecycle | -- | sessionStart+End | -- | -- |
| Error tracking | -- | errorOccurred | -- | -- |

### Native Hook Formats (verified)

**Claude Code** (settings.json):
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash|Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "python3 \"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/script.py\"",
        "timeout": 15
      }]
    }]
  }
}
```

**Gemini CLI** (settings.json -- CORRECT format):
```json
{
  "hooksConfig": { "enabled": true },
  "hooks": {
    "BeforeTool": [{
      "matcher": "write_file|replace|edit_file",
      "hooks": [{
        "type": "command",
        "name": "auto-format",
        "command": "python3 \"$GEMINI_PROJECT_DIR/.ai-engineering/scripts/hooks/auto-format.py\"",
        "timeout": 15000,
        "description": "Auto-format edited files"
      }]
    }]
  }
}
```

**GitHub Copilot** (.github/hooks/hooks.json):
```json
{
  "version": 1,
  "hooks": {
    "preToolUse": [{
      "type": "command",
      "bash": "./.ai-engineering/scripts/hooks/copilot-deny.sh",
      "powershell": "./.ai-engineering/scripts/hooks/copilot-deny.ps1",
      "timeoutSec": 5
    }]
  }
}
```

**Codex CLI** (.codex/hooks.json -- TO GENERATE):
```json
{
  "hooks": {
    "PreToolUse": [{
      "matcher": "Bash|Write|Edit",
      "hooks": [{
        "type": "command",
        "command": "python3 .ai-engineering/scripts/hooks/prompt-injection-guard.py",
        "timeout": 15,
        "statusMessage": "Scanning for injection patterns..."
      }]
    }]
  }
}
```

### Files Impacted (50+ files)

**Core scripts:**
- `scripts/sync_command_mirrors.py` -- Remove .agents/ target, add .codex/, fix Gemini hooks format
- `src/ai_engineering/installer/templates.py` -- Remap Codex from .agents to .codex, remove .agents from Gemini
- `src/ai_engineering/installer/autodetect.py` -- Detect .codex/ for Codex, remove .agents/ detection
- `src/ai_engineering/installer/operations.py` -- Update valid providers if needed

**Instruction files:**
- `CLAUDE.md` -- Fix platform mirrors table (separate Gemini from Codex)
- `GEMINI.md` -- Fix Claude Code row bug (line 114), update Codex row to .codex
- `AGENTS.md` -- Update platform mirrors table, add Codex hooks note

**Templates (each file has root + template copy):**
- `src/ai_engineering/templates/project/.gemini/settings.json` -- Rewrite to correct nested format
- `src/ai_engineering/templates/project/.codex/` -- NEW: skills/, agents/, hooks.json
- `src/ai_engineering/templates/project/.agents/` -- DELETE entirely
- `src/ai_engineering/templates/project/CLAUDE.md` -- Mirror of root CLAUDE.md fix
- `src/ai_engineering/templates/project/GEMINI.md` -- Mirror of root GEMINI.md fix
- `src/ai_engineering/templates/project/AGENTS.md` -- Mirror of root AGENTS.md fix

**Validation & state:**
- `src/ai_engineering/validator/_shared.py` -- Replace .agents constants with .codex, add Gemini
- `src/ai_engineering/validator/categories/file_existence.py` -- Update expected files
- `src/ai_engineering/validator/categories/mirror_sync.py` -- Update mirror targets
- `.ai-engineering/manifest.yml` -- Update enabled providers, replace codex/.agents references
- `.ai-engineering/state/framework-capabilities.json` -- Update surface paths if .agents/ referenced
- `.ai-engineering/state/ownership-map.json` -- Update if .agents/ paths referenced

**Tests:**
- `tests/unit/test_sync_mirrors.py` -- Update for .codex targets
- `tests/unit/test_validator.py` -- Update expected paths
- `tests/unit/test_validator_extra.py` -- Update if .agents referenced
- `tests/unit/installer/test_autodetect.py` -- Update detection logic
- `tests/integration/test_install_matrix.py` -- Update provider matrix
- `tests/integration/test_provider_commands.py` -- Update if .agents referenced

**Documentation:**
- `README.md` -- Update if .agents referenced
- `docs/solution-intent.md` -- Update architecture references
- `.ai-engineering/README.md` -- Update mirror references
- `.ai-engineering/runbooks/governance-drift.md` -- Update paths

**Root directories (managed by sync script):**
- `.agents/` -- DELETE entirely (after syncing to .codex/)
- `.codex/` -- NEW: generated by sync script
- `.gemini/settings.json` -- NEW at root (currently missing, only in template)

## Open Questions

None. All questions resolved as decisions D-087-08 through D-087-10.
