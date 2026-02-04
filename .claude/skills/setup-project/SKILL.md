---
name: setup-project
description: Initialize a new project with the AI Engineering Framework
disable-model-invocation: true
---

## Context

Sets up a new project with the AI Engineering Framework, configuring CLAUDE.md, standards, skills, agents, hooks, and CI/CD for the specified technology stack.

## Inputs

$ARGUMENTS - Project name and stacks (e.g., "MyProject dotnet typescript")

## Steps

### 1. Parse Arguments

Extract from $ARGUMENTS:
- **Project name**
- **Technology stacks** (dotnet, typescript, python, terraform)
- **CI/CD platform** (github, azure, both) - ask if not specified

### 2. Run Install Script

Execute the framework install script:
```bash
scripts/install.sh --name "<name>" --stacks <stacks> --cicd <platform> --target .
```

### 3. Post-Installation Configuration

- Replace `{{PROJECT_DESCRIPTION}}` in CLAUDE.md with the project name
- Set up stack-specific standards references
- Copy `CLAUDE.local.md.example` for the user

### 4. Detect Platform

- Read git remote URL to detect GitHub vs Azure DevOps
- Verify CLI availability (gh/az)
- Report platform-specific features

### 5. Verify

Run `/validate` to confirm correct setup.

## Verification

- All required files exist
- CLAUDE.md references are correct
- CI/CD files are valid
- Platform detected and CLI available
- No unresolved placeholders in non-template files
