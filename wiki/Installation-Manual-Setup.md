# Manual Setup

> Step-by-step manual installation for full control over what gets installed.

## When to Use Manual Setup

- You want to understand exactly what's being installed
- You need to customize the installation process
- The install script doesn't work in your environment
- You're integrating with an existing framework

## Step 1: Clone the Framework

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git /tmp/ai-framework
cd /tmp/ai-framework
```

## Step 2: Copy Core Files

```bash
# Copy CLAUDE.md (main entry point)
cp CLAUDE.md /path/to/your/project/

# Copy .claude directory (skills, agents, hooks)
cp -r .claude /path/to/your/project/

# Copy standards
cp -r standards /path/to/your/project/
```

## Step 3: Copy Context Templates

```bash
# Copy context templates
cp -r context /path/to/your/project/

# Copy learnings templates
cp -r learnings /path/to/your/project/
```

## Step 4: Copy CI/CD (Choose One)

**For GitHub:**
```bash
mkdir -p /path/to/your/project/.github
cp -r .github/workflows /path/to/your/project/.github/
cp .github/copilot-instructions.md /path/to/your/project/.github/
cp -r .github/instructions /path/to/your/project/.github/
```

**For Azure DevOps:**
```bash
cp -r pipelines /path/to/your/project/
```

## Step 5: Enable Hooks

Make hook scripts executable:

```bash
chmod +x /path/to/your/project/.claude/hooks/*.sh
```

## Step 6: Customize CLAUDE.md

Edit `CLAUDE.md` and update the TEAM section:

```markdown
<!-- BEGIN:TEAM -->
## Project Overview

My Project is a [description]...

## Custom Rules
- [Add your project-specific rules]
<!-- END:TEAM -->
```

## Step 7: Customize Project Context

Edit these files:

| File | Purpose |
|------|---------|
| `context/project.md` | Project description and objectives |
| `context/architecture.md` | System architecture |
| `context/stack.md` | Technology versions |
| `context/glossary.md` | Domain terminology |

## Step 8: Create Personal Overrides (Optional)

```bash
cp CLAUDE.local.md.example CLAUDE.local.md
```

Add `CLAUDE.local.md` to `.gitignore`:

```bash
echo "CLAUDE.local.md" >> .gitignore
```

## Step 9: Verify Installation

Open Claude Code and run:

```
/validate
```

## Git Submodule Alternative

Instead of copying files, you can use a git submodule:

```bash
cd your-project

# Add as submodule
git submodule add https://github.com/arcasilesgroup/ai-engineering.git .ai-engineering

# Symlink the files Claude Code needs
ln -s .ai-engineering/CLAUDE.md CLAUDE.md
ln -s .ai-engineering/.claude .claude
ln -s .ai-engineering/standards standards

# Copy files you'll customize (don't symlink these)
cp -r .ai-engineering/context context
cp -r .ai-engineering/learnings learnings
```

See [Submodule Approach](Advanced-Submodule-Approach) for full details.

## Minimal Installation

If you only want standards enforcement without skills/agents:

```bash
# Just copy CLAUDE.md and standards
cp CLAUDE.md /path/to/your/project/
cp -r standards /path/to/your/project/

# Create minimal .claude directory
mkdir -p /path/to/your/project/.claude
echo '{}' > /path/to/your/project/.claude/settings.json
```

---
**See also:** [Quick Install](Installation-Quick-Install) | [Submodule Approach](Advanced-Submodule-Approach)
