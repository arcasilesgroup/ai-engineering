# FAQ

> Frequently asked questions about the AI Engineering Framework.

## General

### What is this framework?

A collection of markdown files that AI coding agents (Claude Code, GitHub Copilot) read natively to enforce your team's standards, automate workflows, and maintain quality. No CLI, no build step, no dependencies.

### What AI tools does it work with?

| Tool | Support Level |
|------|---------------|
| **Claude Code** | Full (skills, agents, hooks, standards) |
| **GitHub Copilot** | Standards only (via copilot-instructions.md) |
| **Cursor** | Partial (CLAUDE.md and standards) |

### Do I need to install anything?

No runtime dependencies. The framework is pure markdown + shell scripts. Optional tools (gitleaks, gh CLI) enhance functionality but aren't required.

---

## Installation

### How do I install the framework?

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git /tmp/ai-framework
/tmp/ai-framework/scripts/install.sh --name "MyProject" --stacks dotnet,typescript --cicd github
```

See [Quick Install](Installation-Quick-Install) for details.

### Can I use this with an existing project?

Yes. The framework adds files alongside your existing code. It doesn't modify your source files.

### What if I only use TypeScript, not .NET?

Specify only the stacks you use:

```bash
./install.sh --name "MyProject" --stacks typescript --cicd github
```

### How do I update the framework?

```bash
./install.sh --update --target /path/to/project
```

See [Updating](Installation-Updating) for details.

---

## Skills

### How do I use a skill?

Type the skill name with a slash:

```
/commit-push
/review staged
/test src/services/
```

### What skills are available?

21 skills covering git workflow, code quality, security, and documentation. See [Skills Overview](Skills-Overview) for the full list.

### Can I create my own skills?

Yes. Add markdown files to `.claude/skills/custom/`. See [Custom Skills](Customization-Custom-Skills).

### Why isn't my custom skill showing up?

1. Check it's in `.claude/skills/custom/`
2. Verify the file has proper frontmatter
3. Make sure the filename ends in `.md`

---

## Agents

### How do I run an agent?

Ask Claude to dispatch it:

```
Run the verify-app agent.
Use code-architect to plan the feature.
```

### What's the difference between skills and agents?

| Aspect | Skills | Agents |
|--------|--------|--------|
| Interaction | Interactive, step-by-step | Autonomous, background |
| Invocation | `/skill-name` | Claude dispatches |
| Purpose | Multi-step workflows | Single-purpose verification |

### Can I run multiple agents at once?

Yes:

```
Run verify-app and code-architect in parallel.
```

---

## Hooks

### Why aren't my hooks running?

1. Make scripts executable: `chmod +x .claude/hooks/*.sh`
2. Check `settings.json` has hooks configured
3. Verify the matcher pattern matches your tool usage

### How do I disable a hook?

Remove or comment out the hook in `.claude/settings.json`.

### Can hooks block Claude's actions?

Yes. Return exit code `2` to block:

```bash
#!/usr/bin/env bash
if [[ "$1" == *"dangerous"* ]]; then
  echo "BLOCKED: Dangerous operation"
  exit 2  # Blocks the action
fi
exit 0  # Allows the action
```

---

## Standards

### How does Claude know my coding standards?

Claude reads `standards/*.md` files at session start. Write your rules there and Claude will follow them.

### Can I add rules for a stack not covered?

Yes. Create a new file like `standards/go.md`. See [Custom Standards](Customization-Custom-Standards).

### My standards aren't being followed. Why?

1. Check the file is in `standards/`
2. Reference it in CLAUDE.md
3. Use clear, actionable language
4. Provide examples of correct patterns

---

## CLAUDE.md

### What is CLAUDE.md?

The main entry point that Claude Code reads to understand your project. It contains identity, rules, skills, agents, and project context.

### Can I customize CLAUDE.md?

Yes, in the TEAM section. The framework section is updated automatically; the TEAM section is yours.

### What are the section markers?

```markdown
<!-- BEGIN:AI-FRAMEWORK:v2.0.0 -->
Framework content (auto-updated)
<!-- END:AI-FRAMEWORK -->

<!-- BEGIN:TEAM -->
Your content (never overwritten)
<!-- END:TEAM -->
```

### My CLAUDE.md doesn't have section markers

Run `/migrate-claude-md` to add them.

---

## CI/CD

### Does this work with GitHub Actions?

Yes. The framework includes GitHub Actions workflows in `.github/workflows/`.

### Does this work with Azure Pipelines?

Yes. The framework includes Azure Pipelines in `pipelines/`.

### How does platform detection work?

The framework reads your git remote URL and detects:
- `github.com` → GitHub
- `dev.azure.com` or `visualstudio.com` → Azure DevOps

---

## Troubleshooting

### /validate says files are missing

Run the installer again:

```bash
./install.sh --name "MyProject" --stacks dotnet --target .
```

### Skills aren't working

1. Verify `.claude/skills/` exists
2. Check Claude Code is reading CLAUDE.md
3. Try `/validate` to check installation

### Hooks aren't formatting my code

1. Make sure formatter is installed (prettier, dotnet format, etc.)
2. Check hook is executable: `chmod +x .claude/hooks/auto-format.sh`
3. Verify PostToolUse hook is configured for Write|Edit

### Secret scanning isn't blocking commits

1. Install gitleaks: `brew install gitleaks`
2. Test: `gitleaks detect --source . --no-git`
3. Check `/commit-push` skill is being used

---

## Contributing

### How can I contribute?

See [CONTRIBUTING.md](https://github.com/arcasilesgroup/ai-engineering/blob/main/CONTRIBUTING.md).

### Where do I report bugs?

[Open an issue](https://github.com/arcasilesgroup/ai-engineering/issues) on GitHub.

---

## More Questions?

- Check the [wiki](Home) for detailed documentation
- [Open an issue](https://github.com/arcasilesgroup/ai-engineering/issues) for bugs
- Review [CLAUDE.md](https://github.com/arcasilesgroup/ai-engineering/blob/main/CLAUDE.md) for framework details

---
**See also:** [Getting Started](Getting-Started) | [Home](Home)
