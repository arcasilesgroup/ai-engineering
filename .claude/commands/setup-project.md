---
description: Initialize a new project with the AI Engineering Framework
---

## Context

Sets up a new project with the AI Engineering Framework, configuring CLAUDE.md, standards, commands, and CI/CD for the specified technology stack.

## Inputs

$ARGUMENTS - Project name and stacks (e.g., "MyProject dotnet typescript")

## Steps

### 1. Parse Arguments

Extract from $ARGUMENTS:
- **Project name**
- **Technology stacks** (dotnet, typescript, python, terraform)
- **CI/CD platform** (github, azure, both) - ask if not specified

### 2. Initialize Project Structure

Create the framework directories:
```
.claude/commands/
.claude/agents/
standards/
context/
learnings/
```

### 3. Configure CLAUDE.md

Copy the template CLAUDE.md and customize:
- Replace `{{PROJECT_NAME}}` with the project name.
- Remove references to stacks not in use.
- Set up stack-specific standards references.

### 4. Configure Standards

Copy only the relevant standards files:
- Always: `global.md`, `security.md`, `quality-gates.md`, `testing.md`, `cicd.md`
- Per stack: `dotnet.md`, `typescript.md`, `python.md`, `terraform.md`, `api-design.md`

### 5. Configure Commands

Copy the appropriate commands:
- Always: commit, pr, review, test, fix, refactor, security-audit, quality-gate, validate, learn
- Per stack: add-endpoint (.NET), add-component (TypeScript), dotnet/* commands

### 6. Configure CI/CD

Based on platform choice:
- **github**: Copy `.github/workflows/` files
- **azure**: Copy `pipelines/` files and templates
- **both**: Copy all CI/CD files

### 7. Initialize Context

Create context files with placeholders:
- `context/project.md` - with project name filled in
- `context/architecture.md` - template
- `context/stack.md` - populated with selected stacks
- `context/glossary.md` - template
- `context/decisions/_template.md`

### 8. Initialize Learnings

Create empty learning files for selected stacks.

### 9. Verify

Run `/validate` to confirm correct setup.

## Verification

- All required files exist
- CLAUDE.md references are correct
- CI/CD files are valid
- No unresolved placeholders in non-template files
