# Contributing to AI Engineering Framework

## How to Contribute

### Reporting Issues

Open a GitHub issue with:
- Description of the problem or suggestion
- Steps to reproduce (if applicable)
- Expected vs actual behavior

### Adding a New Stack

1. Create `standards/{stack}.md` with coding conventions
2. Create `.github/instructions/{stack}.instructions.md` with Copilot instructions
3. Create `learnings/{stack}.md` (can be empty initially)
4. Update `CLAUDE.md` to reference the new standard
5. Update `scripts/install.sh` to include the new stack option
6. Add a pipeline template in `pipelines/templates/{stack}-build.yml`

### Adding a New Skill

Skills live in `.claude/skills/{skill-name}/SKILL.md`.

1. Create the directory: `.claude/skills/{skill-name}/`
2. Create `SKILL.md` with this structure:

```markdown
---
name: skill-name
description: Short description of what the skill does
disable-model-invocation: true  # Only if it should require explicit user invocation
---

## Context

[What this skill does and when to use it]

## Inputs

$ARGUMENTS - [What arguments the skill accepts]

## Steps

### 1. [First Step]
[Instructions]

### 2. [Second Step]
[Instructions]

## Verification

- [How to verify the skill worked correctly]
```

3. Update `CLAUDE.md` skills list
4. Update `scripts/install.sh` to include the new skill

**Auto-invocable vs Explicit:**
- Set `disable-model-invocation: true` for skills that should only run when the user explicitly types `/skill-name` (e.g., commit, deploy, scaffold operations).
- Omit this field for skills the model should invoke proactively when relevant (e.g., review, test, fix).

**Team Custom Skills:**
Teams can add their own skills in `.claude/skills/custom/` — these are never overwritten by framework updates.

### Adding a New Agent

Agents live in `.claude/agents/{agent-name}.md`.

1. Create the agent file with this structure:

```markdown
---
description: What the agent does
tools: [Bash, Read, Glob, Grep]  # Available tools
---

## Objective

[What the agent achieves]

## Process

1. [Step 1]
2. [Step 2]

## Success Criteria

- [What constitutes success]

## Constraints

- [What the agent must NOT do]
```

2. Update `CLAUDE.md` agents list
3. Update `scripts/install.sh` to include the new agent

**Team Custom Agents:**
Teams can add their own agents in `.claude/agents/custom/` — these are never overwritten by framework updates.

### Adding a New Hook

Hooks live in `.claude/hooks/{hook-name}.sh`.

1. Create the hook script:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Read stdin JSON (contains tool_name, file_path, command, etc.)
INPUT="$(cat)"

# Parse relevant fields
# Example: TOOL_NAME=$(echo "$INPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")

# Your logic here

# Exit codes:
#   0 = allow (continue)
#   2 = block (with reason on stderr)
exit 0
```

2. Make it executable: `chmod +x .claude/hooks/{hook-name}.sh`
3. Register it in `.claude/settings.json` under the appropriate trigger:
   - `PreToolUse` — runs before a tool executes (can block with exit 2)
   - `PostToolUse` — runs after a tool executes
   - `Notification` — runs on notifications

4. Update `context/hooks.md` documentation

### Adding a New Platform

To add support for a new git platform (e.g., GitLab):

1. Update `.claude/skills/utils/platform-detection.md` with detection logic
2. Update `/commit-push-pr` skill with PR creation commands
3. Update `/pr` skill with PR creation commands
4. Add CLI permission to `.claude/settings.json`
5. Create `.github/instructions/platform.instructions.md` entry
6. Update `scripts/install.sh` platform detection
7. Document in `README.md`

### Modifying Standards

- Standards should be prescriptive, not aspirational
- Include code examples for every rule
- Include anti-pattern examples showing what NOT to do
- Reference authoritative sources where applicable

## File Conventions

- All instructional content is **markdown**
- Metadata uses **YAML frontmatter**
- Maximum directory depth: **3 levels**
- File names: **kebab-case**
- No registries or index files — file existence = registration

## Versioning Policy

The framework follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes (directory structure, skill format, removed features)
- **MINOR**: New features (skills, agents, hooks, standards) — backward compatible
- **PATCH**: Bug fixes, typos, corrections

When making changes:
1. Update `VERSION` file
2. Add entry to `CHANGELOG.md`
3. If breaking: update `UPGRADING.md` with migration instructions

## Pull Request Process

1. Fork the repository
2. Create a branch: `feat/add-rust-stack` or `fix/dotnet-standard-typo`
3. Make your changes
4. Run `/validate` to check framework integrity
5. Update version and changelog if appropriate
6. Submit a PR with a clear description

## Code of Conduct

Be respectful, constructive, and inclusive. Focus on technical merit.
