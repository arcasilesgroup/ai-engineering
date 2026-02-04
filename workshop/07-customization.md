# Module 7: Customization

## Overview

Learn how to extend the framework with custom standards, commands, agents, and stacks.

---

## Adding a Custom Command

### 1. Create the File

Create a new markdown file in `.claude/commands/`:

```bash
touch .claude/commands/my-command.md
```

### 2. Follow the Template

```markdown
---
description: One-line description shown in command picker
---

## Context
What this command does and when to use it.

## Inputs
$ARGUMENTS - What the user provides

## Steps

### 1. First Step
[Instructions for Claude]

### 2. Second Step
[Instructions for Claude]

## Verification
How to verify the output is correct.
```

### 3. Use It

In Claude Code:
```
/my-command some arguments
```

### Tips

- Keep descriptions under 80 characters
- Include a `## Verification` section
- Reference `standards/*.md` files when applicable
- Use `$ARGUMENTS` to accept user input

---

## Adding a Custom Agent

### 1. Create the File

```bash
touch .claude/agents/my-agent.md
```

### 2. Follow the Template

```markdown
---
description: One-line description
tools: [Bash, Read, Glob]
---

## Objective
What this agent does (one sentence).

## Process
1. Step one
2. Step two
3. Step three

## Success Criteria
How to know it worked.

## Constraints
What NOT to do.
```

### Key Differences from Commands

- Agents are **autonomous** — no interaction with the user
- Agents should be **focused** — one clear purpose
- Most agents should be **read-only** — report, don't modify
- List the `tools` the agent needs in the frontmatter

---

## Adding a New Stack

### 1. Create the Standard

```bash
touch standards/rust.md
```

Write the coding conventions, naming rules, patterns, and anti-patterns for the new stack.

### 2. Create Copilot Instructions

```bash
touch .github/instructions/rust.instructions.md
```

```markdown
---
applyTo: "**/*.rs"
---

# Rust Instructions
[Key conventions for Copilot]
```

### 3. Create a Learnings File

```bash
touch learnings/rust.md
```

### 4. Update CLAUDE.md

Add the new stack to the standards reference table and tech stack section.

### 5. Update install.sh

Add the new stack option to the install script.

---

## Modifying Quality Gate Thresholds

Edit `standards/quality-gates.md`:

```markdown
## Quality Gate Thresholds

| Metric | Threshold |
|--------|-----------|
| Coverage on new code | >= 90%   |  ← Changed from 80%
| Duplicated lines | <= 2%       |  ← Changed from 3%
```

The `/quality-gate` command and `quality-checker` agent read these values automatically.

---

## Adding Project-Specific Standards

You can add custom standards files:

```bash
touch standards/microservices.md
```

Then reference it in `CLAUDE.md`:

```markdown
| `standards/microservices.md` | Microservice communication patterns |
```

---

## Exercise: Create a Custom Command

Create a `/changelog` command that:
1. Reads recent git commits
2. Groups them by type (feat, fix, etc.)
3. Generates a CHANGELOG entry

Save it as `.claude/commands/changelog.md` and test it.

## Next

→ [Module 8: Advanced Workflows](08-advanced-workflows.md)
