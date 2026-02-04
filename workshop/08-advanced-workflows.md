# Module 8: Advanced Workflows

## Overview

Master advanced patterns for maximum productivity: parallel agents, plan mode, hooks, custom skills, and multi-instance workflows.

---

## Pattern 1: Parallel Claudes

Run 5+ Claude Code instances simultaneously, each working on a different task. This is the single biggest productivity multiplier.

### Setup

1. Open multiple terminal tabs/windows.
2. Each instance reads `CLAUDE.md` and follows the same standards.
3. Assign each instance a specific, independent task.

### Example: Feature Development

```
Terminal 1: "Implement the UserService with GET and POST endpoints"
Terminal 2: "Write unit tests for the OrderProvider"
Terminal 3: "Update the API documentation for v2 endpoints"
Terminal 4: "Run verify-app agent to validate build, tests, and security"
Terminal 5: "Fix lint errors in the TypeScript frontend"
```

### Rules for Parallel Work

From `CLAUDE.md`:
- Each Claude instance works on separate files.
- Never have two instances editing the same file.
- Use git branches if instances need to modify overlapping areas.
- Coordinate through CLAUDE.md or a shared plan file.

---

## Pattern 2: Plan Mode

For complex changes, use plan mode to design the approach before writing code.

### Workflow

1. **Enter plan mode**: Claude explores the codebase and designs an implementation plan.
2. **Review the plan**: You approve or modify.
3. **Execute**: Claude implements the approved plan.

### When to Use

- Multi-file changes (> 3 files)
- Architectural decisions
- New features with unclear scope
- Refactoring existing code

### Example

```
Help me add a caching layer to the API. Enter plan mode.
```

Claude will:
1. Explore the current architecture
2. Identify where caching should be added
3. Present options (Redis vs in-memory vs hybrid)
4. Create a step-by-step implementation plan
5. Wait for your approval before coding

---

## Pattern 3: Hooks

Hooks run shell commands automatically in response to Claude Code events. The framework includes 4 hook scripts out of the box.

### Included Hook Scripts

| Script | Event | Purpose |
|--------|-------|---------|
| `auto-format.sh` | PostToolUse | Auto-formats files after Claude edits them |
| `block-dangerous.sh` | PreToolUse | Blocks force push, `rm -rf`, and other destructive commands |
| `block-env-edit.sh` | PreToolUse | Prevents Claude from editing `.env` files |
| `notify.sh` | Notification | Sends desktop alerts when Claude needs attention |

### Hooks Configuration

The hooks are configured in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-dangerous.sh"
          }
        ]
      },
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/block-env-edit.sh"
          }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/auto-format.sh"
          }
        ]
      }
    ],
    "Notification": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/notify.sh"
          }
        ]
      }
    ]
  }
}
```

### How Each Hook Works

**auto-format.sh** (PostToolUse) — Runs after every file edit:
- Detects the file type and runs the appropriate formatter
- `.cs` files -> `dotnet format`
- `.ts/.tsx/.js/.jsx` files -> `npx prettier --write`
- `.py` files -> `black` or `ruff format`
- Exits silently if the formatter is not installed

**block-dangerous.sh** (PreToolUse) — Runs before Bash commands:
- Blocks `git push --force`, `git reset --hard`, `rm -rf /`
- Returns exit code 2 (blocks the tool call) if a dangerous command is detected
- Protects against accidental destructive operations

**block-env-edit.sh** (PreToolUse) — Runs before file writes:
- Checks if the target file matches `.env*` patterns
- Blocks edits to `.env`, `.env.local`, `.env.production`, etc.
- Prevents accidental secret exposure

**notify.sh** (Notification) — Runs when Claude needs attention:
- Sends a desktop notification (macOS `osascript` or Linux `notify-send`)
- Useful when running long tasks in the background

### Custom Hooks

Add your own hooks by creating scripts in `.claude/hooks/` and registering them in `settings.json`:

```json
{
  "matcher": "Write|Edit",
  "hooks": [
    {
      "type": "command",
      "command": ".claude/hooks/my-custom-hook.sh"
    }
  ]
}
```

---

## Pattern 4: Pre-Allowing Permissions

Speed up your workflow by pre-allowing common operations in `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(dotnet build:*)",
      "Bash(dotnet test:*)",
      "Bash(npm run:*)",
      "Bash(npm test:*)",
      "Bash(pytest:*)",
      "Bash(gitleaks:*)",
      "Bash(gh:*)"
    ]
  }
}
```

This eliminates permission prompts for common safe operations.

---

## Pattern 5: Session Handoff

Transfer work between Claude Code terminal and Claude web interface.

### Terminal -> Web

1. In Claude Code, explain what you've done and what's left.
2. Copy the session summary.
3. Paste into Claude web for continued discussion.

### Web -> Terminal

1. Design your approach in Claude web.
2. Copy the plan/instructions.
3. Paste into Claude Code for implementation.

---

## Pattern 6: MCP Servers

Extend Claude's capabilities with Model Context Protocol (MCP) servers.

### Common MCP Servers

| Server | Purpose |
|--------|---------|
| Filesystem | Read/write files outside the project |
| Database | Query databases directly |
| GitHub | Advanced GitHub API operations |
| Sentry | Error monitoring integration |

### Configuration

```json
// .claude/settings.json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}
```

---

## Pattern 7: Custom Skills

Create team-specific skills by adding markdown files to `.claude/skills/custom/`.

### Creating a Custom Skill

1. Create the skill file:

```markdown
<!-- .claude/skills/custom/deploy-staging.md -->
# Deploy to Staging

Deploy the current branch to the staging environment.

## Steps

1. Run the full test suite: `dotnet test` or `npm test`
2. Build the production artifacts
3. Push to the staging branch: `git push origin HEAD:staging`
4. Monitor the deployment pipeline
5. Report the deployment status
```

2. The skill is immediately available as `/deploy-staging` in Claude Code.

### Organizing Custom Skills

```
.claude/skills/
├── commit.md              # Framework skills
├── pr.md
├── review.md
├── test.md
├── ...
└── custom/                # Team-specific skills
    ├── deploy-staging.md
    ├── release-notes.md
    └── onboard-dev.md
```

### Tips for Good Custom Skills

- Keep skills focused on a single workflow
- Include the exact commands to run
- Reference standards files when applicable
- Add constraints (e.g., "never deploy on Fridays")

---

## Advanced Exercise: Full Workflow

Combine everything you've learned:

1. **Plan**: Enter plan mode for a new feature.
2. **Review plan**: Approve the implementation approach.
3. **Implement**: Claude writes the code following standards.
4. **Verify**: Run `verify-app` agent to validate build, tests, and security in parallel.
5. **Quality**: Run `/quality-gate` to verify metrics.
6. **Test**: Run `/test` to generate and execute tests.
7. **Review**: Run `/review staged` for self-review.
8. **Commit**: Run `/commit` for smart commit with secret scanning.
9. **PR**: Run `/pr` to create a structured pull request.

This is the complete AI-augmented development inner loop.

---

## Summary

You've completed the core AI Engineering Framework workshop. You now know how to:

- Install and configure the framework
- Use core skills for your daily workflow
- Set up quality gates and security scanning
- Configure CI/CD for GitHub Actions and Azure Pipelines
- Create custom skills, agents, and standards
- Use advanced patterns for maximum productivity

The framework is designed to grow with your team — add learnings, customize standards, and create new skills as your project evolves.

Continue to the next modules for deeper topics:

-> [Module 9: The Production Reliability Workflow](09-boris-cherny-workflow.md)
-> [Module 10: Versioning](10-versioning.md)
