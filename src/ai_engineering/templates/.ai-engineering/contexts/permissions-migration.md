# Permissions Migration: Wildcard to Narrow Allow List

**Spec**: spec-107 D-107-02
**Owner**: `.claude/settings.json` (`permissions.allow`)
**Doctor advisory**: `permissions-wildcard-detected` (WARN, never FAIL)

## Why migrate away from `["*"]`

`.claude/settings.json` ships in older projects with `permissions.allow: ["*"]`,
which authorizes Claude Code to invoke every tool surface, including any MCP
server attached to the session. The wildcard provides zero defense-in-depth:

1. **No audit trail** — there is no record of which tools the project intends
   to grant. A reviewer cannot tell whether a new MCP server was deliberately
   adopted or silently injected via a malicious manifest update.
2. **Supply-chain blast radius** — a compromised MCP server (Postmark/XZ-class
   attack) is implicitly trusted because every `mcp__*` namespace is allowed.
3. **Drift detection is impossible** — narrowing later requires reconstructing
   the actual usage pattern from logs instead of diffing the config.

A narrow explicit list closes those gaps without surrendering any productive
workflow. Each entry documents an intentional capability decision.

## Canonical narrow list

Ship templates use this 13-entry set, sufficient for every spec-105/106/107
workflow plus the two MCP servers documented in this repo:

```json
"permissions": {
  "allow": [
    "Read",
    "Write",
    "Edit",
    "MultiEdit",
    "Bash",
    "Agent",
    "Glob",
    "Grep",
    "Skill",
    "TaskCreate",
    "TaskUpdate",
    "mcp__context7__*",
    "mcp__notebooklm-mcp__*"
  ],
  "deny": [
    "Bash(rm -rf *)",
    "Bash(*--no-verify*)"
  ]
}
```

`Read`, `Write`, `Edit`, `MultiEdit`, `Bash`, `Glob`, `Grep`, `Agent`, `Skill`,
`TaskCreate`, `TaskUpdate` are the foundational Claude Code tools used by every
ai-engineering skill and agent. The two `mcp__*` glob entries cover the
Context7 docs MCP and the NotebookLM MCP server vendored with the framework.

## How to migrate an existing project

`ai-eng install` and `ai-eng update` deliberately do **not** rewrite an
existing `.claude/settings.json` — see decision D-107-02 / NG-1. Migration is
opt-in and user-driven so you can audit the change locally.

1. Open `.claude/settings.json` in your project.
2. Inspect your current `permissions.allow` value:
   - If it is `["*"]`, replace it with the canonical list above.
   - If you already have a narrow list, no action needed.
3. Confirm the `deny` array is preserved verbatim. Never remove a deny rule
   while migrating (CLAUDE.md Don't #7).
4. Run `ai-eng doctor` and confirm the `permissions-wildcard-detected` WARN
   advisory clears.

## Extending the allow list

When a project uses an MCP server outside the canonical two, add the matching
glob to the allow array. Use server-name globs rather than re-introducing the
top-level wildcard:

```json
"allow": [
  "Read", "Write", "Edit", "MultiEdit", "Bash", "Agent",
  "Glob", "Grep", "Skill", "TaskCreate", "TaskUpdate",
  "mcp__context7__*",
  "mcp__notebooklm-mcp__*",
  "mcp__custom-internal-mcp__*"
]
```

If a single tool inside an MCP server should be denied while the rest is
allowed, add it to `deny` rather than narrowing the allow glob — denies always
win in Claude Code's permission resolver.

## Boundaries (NEVER)

- Never re-introduce `"*"` to clear an unrelated permissions error. Diagnose
  the missing capability and add it explicitly.
- Never delete a deny rule when narrowing the allow list. Deny is the last line
  of defense against destructive command patterns.
- Never silence the doctor advisory by editing `_check_permissions_wildcard`.
  Migrate the project instead — the check is informational and costs nothing.
