# Submodule Approach

> Using git submodules to manage the framework (for power users).

## TL;DR

**Not recommended as the primary approach.** The install script provides better customization support, simpler CI/CD, and native team content handling. This document is for power users with specific requirements.

## Comparison

| Aspect | Install Script | Git Submodule |
|--------|----------------|---------------|
| **Customization** | Easy — files are copied, fully editable | Hard — submodule is read-only |
| **CLAUDE.md editing** | Direct file editing | Cannot edit (symlink to submodule) |
| **Team content** | Native support via TEAM section | Requires overlay pattern |
| **CI/CD setup** | Files already present | Requires `--recursive` clone |
| **Updates** | `install.sh --update` | `git submodule update --remote` |
| **Version pinning** | `.ai-version` file | Submodule commit SHA |
| **Merge conflicts** | Possible in framework files | None (read-only) |
| **Offline support** | Full (files are local) | Requires submodule fetch |

## What Breaks with Submodules

### 1. CLAUDE.md Cannot Be Customized

If `CLAUDE.md` is a symlink to the submodule, teams cannot:
- Add project-specific content
- Customize Critical Rules
- Add custom Danger Zones

**Workaround:** Copy CLAUDE.md instead of symlinking.

### 2. context/ and learnings/ Are Project-Specific

These directories must contain project-specific content:
- `context/project.md` — Your project description
- `learnings/*.md` — Accumulated team knowledge

**Workaround:** Keep these in the main repo, not the submodule.

### 3. CI/CD Complexity

Every CI/CD pipeline needs:

```yaml
- uses: actions/checkout@v4
  with:
    submodules: recursive  # Easy to forget
```

Forgetting `recursive` causes cryptic failures.

## Hybrid Pattern (If You Must)

For teams that still want submodules, use this hybrid pattern:

### Directory Structure

```
your-project/
├── .ai-engineering/           # Submodule (read-only reference)
│   ├── .claude/
│   ├── standards/
│   └── ...
├── CLAUDE.md                  # Project file (copied, NOT symlink)
├── .claude/
│   ├── settings.json          # Project-specific (NOT symlink)
│   ├── skills/
│   │   ├── custom/            # Project custom skills
│   │   └── -> ../.ai-engineering/.claude/skills/*
│   ├── agents/
│   │   ├── custom/            # Project custom agents
│   │   └── -> ../.ai-engineering/.claude/agents/*
│   └── hooks/
│       └── -> ../.ai-engineering/.claude/hooks/*
├── standards/
│   └── -> .ai-engineering/standards/*
├── context/                   # Project-specific (no symlinks)
└── learnings/                 # Project-specific (no symlinks)
```

### Setup Script

```bash
#!/usr/bin/env bash
# scripts/setup-submodule-hybrid.sh

set -euo pipefail

SUBMODULE_PATH=".ai-engineering"

# Add submodule if not present
if [[ ! -d "$SUBMODULE_PATH" ]]; then
  git submodule add https://github.com/arcasilesgroup/ai-engineering.git "$SUBMODULE_PATH"
fi

# Initialize and update
git submodule update --init --recursive

# Copy files that need customization (don't symlink these)
cp "$SUBMODULE_PATH/CLAUDE.md" ./CLAUDE.md 2>/dev/null || true
cp "$SUBMODULE_PATH/.claude/settings.json" ./.claude/settings.json 2>/dev/null || true

# Create project-specific directories
mkdir -p context learnings .claude/skills/custom .claude/agents/custom

# Copy context templates if not present
for file in project.md architecture.md stack.md glossary.md; do
  if [[ ! -f "context/$file" ]]; then
    cp "$SUBMODULE_PATH/context/$file" "context/$file"
  fi
done

# Create symlinks for read-only content
for skill_dir in "$SUBMODULE_PATH/.claude/skills/"*/; do
  skill_name=$(basename "$skill_dir")
  if [[ "$skill_name" != "custom" && ! -L ".claude/skills/$skill_name" ]]; then
    ln -sf "../$SUBMODULE_PATH/.claude/skills/$skill_name" ".claude/skills/$skill_name"
  fi
done

echo "Hybrid setup complete."
```

### Updating the Submodule

```bash
# Update to latest
cd .ai-engineering
git fetch origin
git checkout v2.1.0  # Or: git checkout main
cd ..
git add .ai-engineering
git commit -m "chore: update ai-engineering framework to v2.1.0"
```

### CI/CD Configuration

**GitHub Actions:**
```yaml
- uses: actions/checkout@v4
  with:
    submodules: recursive
```

**Azure Pipelines:**
```yaml
- checkout: self
  submodules: recursive
```

## When Submodules Make Sense

Consider submodules if:

1. You have 50+ repos and need guaranteed consistency
2. You have a dedicated platform team managing the framework
3. You want to prevent any framework modifications
4. You're okay with the added complexity

## Recommendation

For most teams, **use the install script**:

```bash
# Initial install
scripts/install.sh --name "MyProject" --stacks dotnet,typescript --cicd github

# Updates
scripts/install.sh --update --target .
```

Benefits:
- Simple setup and updates
- Full customization support
- Native CLAUDE.md sectioning
- No CI/CD changes needed
- Works offline after install

---
**See also:** [Quick Install](Installation-Quick-Install) | [Updating](Installation-Updating)
