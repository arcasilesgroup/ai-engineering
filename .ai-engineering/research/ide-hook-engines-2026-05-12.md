---
topic: IDE hook engines — OpenCode, Cursor, Antigravity (spec-133 evidence)
date: 2026-05-12
tier: external-evidence
consumers: [spec-133 D-133-06, .ai-engineering/specs/spec.md]
---

# IDE Hook Engines — Evidence for spec-133 Surface classification

## Findings

### OpenCode (sst/opencode) — **FULL SURFACE**

- Hook engine: yes (plugin-based, not settings-based) [1][2]
- Instruction files: `AGENTS.md` (project root, primary) + `CLAUDE.md` (fallback for compat); `~/.config/opencode/AGENTS.md` (global) [1]
- Tree dir: `.opencode/commands/`, `.opencode/plugins/`; global `~/.config/opencode/{commands,plugins}/` [2][3]
- Slash commands: yes — markdown files in `.opencode/commands/` become `/<filename>` [2]
- Pre/post-tool-use hooks: yes — plugin API exposes `tool.execute.before`, `tool.execute.after`, plus 25+ others: `session.created`, `session.idle`, `session.compacted`, `permission.asked`, `file.edited`, `message.updated`, `shell.env`, `lsp.client.diagnostics` [3]
- Audit/CLI deterministic probe: yes — `opencode run "<prompt>"` non-interactive mode; `opencode serve` headless HTTP API; `opencode session list`, `opencode export` [4]
- Verdict: **full-surface** — hooks (plugin), slash commands, instruction files, deterministic CLI. Plugin API is JS/TS only (vs. Claude stdio JSON), so wiring layer needs TS shim, but coverage matches Claude Code's 11 canonical events closely.

### Cursor (cursor.com, v1.7+) — **FULL SURFACE**

- Hook engine: yes (native, beta since Cursor 1.7, Sept 2025) [5][6]
- Instruction files: `.cursor/rules/*.mdc` (auto-attached rules); `.cursorrules` (legacy)
- Tree dir: `.cursor/{rules,hooks.json,mcp.json}`; user-level `~/.cursor/hooks.json`; enterprise/team scopes [5]
- Slash commands: partial — rules can be `@`-mentioned but no first-class slash command registry like Claude's `.claude/commands/`
- Pre/post-tool-use hooks: yes — `preToolUse`, `postToolUse`, `postToolUseFailure`, `sessionStart`/`sessionEnd`, `subagentStart`/`subagentStop`, `beforeShellExecution`/`afterShellExecution`, `beforeMCPExecution`/`afterMCPExecution`, `beforeReadFile`, `afterFileEdit`, `beforeSubmitPrompt`, `preCompact`, `stop`, `afterAgentResponse`, `afterAgentThought`, `workspaceOpen` [5]
- Audit/CLI deterministic probe: partial — `cursor-agent` CLI exists, hooks-from-CLI is community-requested
- Verdict: **full-surface** — Cursor's hook engine is closest 1:1 to Claude Code. Event names differ (`preToolUse` camelCase vs Claude `PreToolUse` PascalCase) but capabilities (deny, modify, observe, stdio JSON) are isomorphic. Mapping table trivial.

### Antigravity (Google) — **MIRROR-ONLY**

- Hook engine: **no** (officially confirmed as workaround-only) [7][8]
- Instruction files: `GEMINI.md` (primary, highest priority), `AGENTS.md` (lower priority, added in v1.20.3 / March 5, 2026) [8]
- Tree dir: `.agent/rules/`, `.agent/workflows/`, `.agent/skills/` (workspace); `~/.gemini/antigravity/skills/` (global) [9][10]
- Slash commands: no explicit slash-command system. Workflows are markdown in `.agent/workflows/` (procedural recipes, not invocable commands)
- Pre/post-tool-use hooks: **no** — Google staff (Abhijit_Pramanik) explicitly: *"In Antigravity, you can achieve 'hook-like' behavior … using existing features like workflows and rules directories"* — i.e., not real hooks [7]
- Audit/CLI deterministic probe: **no public CLI documented**. Antigravity is IDE-only at this stage
- Verdict: **mirror-only** — Antigravity is purely instruction-surface today. No deterministic gate wiring possible. AGENTS.md + GEMINI.md canonical-mirror payload + skills folder is the entire integration story. Re-evaluate post-v2.x if Google ships hooks.

## Comparative Table

| Capability | OpenCode | Cursor (1.7+) | Antigravity |
|---|---|---|---|
| Hook engine | yes (plugin API) | yes (native, beta) | no |
| PreToolUse | `tool.execute.before` [3] | `preToolUse` [5] | not shipped [7] |
| PostToolUse | `tool.execute.after` [3] | `postToolUse` [5] | not shipped [7] |
| SessionStart | `session.created` [3] | `sessionStart` [5] | not shipped [7] |
| Stop/Idle | `session.idle` [3] | `stop` [5] | not shipped [7] |
| Block/deny action | yes (plugin return) | yes (`permission:"deny"` or exit 2) [5] | no |
| Instruction file | `AGENTS.md` [1] | `.cursor/rules/*.mdc` | `GEMINI.md` > `AGENTS.md` [8] |
| Tree dir | `.opencode/` [2][3] | `.cursor/` [5] | `.agent/` [9] |
| Skills/Commands | `.opencode/commands/` [2] | rules only | `.agent/skills/`, `.agent/workflows/` [9] |
| Deterministic CLI | yes (`opencode run`) [4] | partial (`cursor-agent`) | no |
| Audit-grade probe | yes (`opencode serve` HTTP) [4] | partial | no |
| **ai-engineering verdict** | **full-surface** | **full-surface** | **mirror-only** |

## Sources

- [1] OpenCode Rules: https://opencode.ai/docs/rules/
- [2] OpenCode Commands: https://opencode.ai/docs/commands/
- [3] OpenCode Plugins API: https://opencode.ai/docs/plugins/
- [4] OpenCode CLI: https://opencode.ai/docs/cli/
- [5] Cursor Hooks Documentation: https://cursor.com/docs/hooks
- [6] Cursor 1.7 Hooks Deep Dive (GitButler): https://blog.gitbutler.com/cursor-hooks-deep-dive
- [7] Antigravity Hooks Forum (Google staff): https://discuss.ai.google.dev/t/hooks-in-antigravity/120458
- [8] Antigravity User Rules: https://antigravity.codes/blog/user-rules
- [9] Antigravity Skills Codelab: https://codelabs.developers.google.com/getting-started-with-antigravity-skills
- [10] Make Antigravity Use AGENTS.md: https://aiengineerguide.com/til/make-antigravity-use-agents-md-automatically/
