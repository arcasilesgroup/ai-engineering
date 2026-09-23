---
name: ai-codegraph
description: >-
  Semantic code intelligence via MCP: call chains, blast radius, cross-file symbol
  relationships. Uses CodeGraph (colbymchenry/codegraph) — a local-first Rust server
  that builds a SQLite knowledge graph from tree-sitter ASTs. One tool: codegraph_explore.
  Use when the question involves "how does X work", "what calls Y", "if I change X what
  breaks", or cross-file dependency analysis. Not for literal text search — use find/grep
  for that. Not for file discovery — use glob. Trigger for "codegraph", "code graph",
  "call chain", "blast radius", "what depends on", "impact analysis".
license: Apache-2.0
---

# ai-codegraph — semantic code intelligence via MCP

## What it produces

Nothing written. This skill reads the code graph and returns structured answers:
verbatim source grouped by file, call paths (including dynamic dispatch), and blast
radius summaries. The agent uses these to answer graph questions without grepping
every file.

## When to use CodeGraph vs find/grep

| Question | Tool | Why |
|----------|------|-----|
| "How does X work?" | `codegraph_explore` | Follows call chains across files |
| "What calls function Y?" | `codegraph_explore` | Graph traversal, follows polymorphism |
| "If I change this interface, what breaks?" | `codegraph_explore` | Blast radius via edge traversal |
| "What does this module depend on?" | `codegraph_explore` | Import edges in the graph |
| "Find all TODOs" | `grep` | Literal text search, faster |
| "Where is X defined?" | `find` | Simple path lookup |
| "Find all files importing X" | `grep` | Literal text match |
| "Show me the test for this function" | `find` + `grep` | Convention-based lookup |

**Rule of thumb:** graph questions → CodeGraph. Text questions → find/grep.

## Steps

1. **Check availability** — is CodeGraph installed?
   ```bash
   which codegraph && codegraph --version
   ```
   If missing: `npm i -g @colbymchenry/codegraph`

2. **Check daemon** — is the daemon running?
   ```bash
   test -S .codegraph/daemon.sock && echo "running" || echo "not running"
   ```
   If not running: `codegraph serve --mcp &`

3. **Check index** — is the project indexed?
   ```bash
   codegraph status
   ```
   If not indexed: `codegraph init`

4. **Query** — use `codegraph_explore` MCP tool:
   - `query`: natural language or symbol/file names
   - `maxFiles`: default 12, increase for broad questions

5. **Interpret results** — CodeGraph returns:
   - Verbatim source grouped by file (with line numbers)
   - Call paths (calls, imports, extends, implements)
   - Blast radius summary (what depends on the queried symbol)

## Per-surface MCP configuration

CodeGraph is an MCP server, not a governance hook. Each surface reads its own config:

| Surface | Config file | Key |
|---------|------------|-----|
| Claude Code | `~/.claude.json` (global) or `.mcp.json` (project) | `mcpServers.codegraph` |
| Cursor | `~/.cursor/mcp.json` (global) or `.cursor/mcp.json` (project) | `mcpServers.codegraph` |
| Copilot VS Code | `.vscode/mcp.json` (local) or user mcp.json | `servers.codegraph` |
| Copilot CLI | `~/.copilot/mcp-config.json` | `mcpServers.codegraph` |
| opencode | `~/.config/opencode/opencode.jsonc` | `mcp.servers.codegraph` |
| OMP | Import from `~/.claude.json` or add manually | — |
| Pi | `pi-codegraph-extension` or `@isac322/pi-codegraph` | — |

**Stdio launch shape** (all surfaces):
```json
{
  "type": "stdio",
  "command": "codegraph",
  "args": ["serve", "--mcp"]
}
```

## Lifecycle

Lane: light
Writes: nothing (read-only tool server)
Read by: any agent that needs graph queries
Dies: on session end
Next: none — the agent decides when to use it based on the question type

## Anti-patterns

- Do NOT use for literal text search (`grep` is faster)
- Do NOT use for file discovery (`find`/`glob` is faster)
- Do NOT use CodeGraph AND grep for the same question — pick one
- DO remember: CodeGraph leaves 82% more context resident after multi-turn sessions
  (vendor data: 67k vs 18k tokens after 3 turns). On small repos (<300 files),
  the cost may outweigh the benefit.

## Source

- Repository: https://github.com/colbymchenry/codegraph
- License: MIT
- Stars: ~71k
- Version: 1.6.0 (measured 2026-09-22)
- Integration evidence: `.codegraph/codegraph.db` in this workspace

Source: ai-engineering (own), Apache-2.0.
