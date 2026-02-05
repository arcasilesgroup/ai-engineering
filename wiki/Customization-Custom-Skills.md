# Custom Skills

> Create team-specific skills for your workflows.

## Overview

Skills are markdown files that define interactive workflows. Custom skills let you encode team-specific processes.

## Location

Custom skills go in `.claude/skills/custom/`:

```
.claude/
└── skills/
    ├── commit/            # Framework skills
    ├── review/
    ├── test/
    └── custom/            # Your custom skills
        ├── deploy-staging.md
        ├── release-notes.md
        └── onboard-dev.md
```

The `custom/` directory is never overwritten by framework updates.

## Skill Anatomy

```markdown
---
description: One-line description shown in skill list
tools: [Bash, Read, Write, Edit, Glob, Grep]
autoInvocable: false
---

# Skill Name

## Objective
What this skill accomplishes (one sentence).

## Process
1. Step one
2. Step two
3. Step three

## Success Criteria
How to know it completed successfully.

## Constraints
What NOT to do.
```

## Creating a Custom Skill

### Example: Deploy to Staging

**File:** `.claude/skills/custom/deploy-staging.md`

```markdown
---
description: Deploy current branch to staging environment
tools: [Bash, Read]
autoInvocable: false
---

# Deploy to Staging

## Objective
Deploy the current branch to the staging environment after verification.

## Process

### 1. Verify Build
Run the full test suite to ensure code is ready:
- .NET: `dotnet test`
- TypeScript: `npm test`

### 2. Build Production Artifacts
Build optimized production bundles:
- .NET: `dotnet publish -c Release`
- TypeScript: `npm run build`

### 3. Push to Staging Branch
Push the current branch to trigger deployment:
```bash
git push origin HEAD:staging --force-with-lease
```

### 4. Monitor Pipeline
Check the deployment pipeline status and report.

### 5. Verify Deployment
- Check health endpoint
- Verify version number
- Report deployment status

## Success Criteria
- All tests pass before deployment
- Pipeline completes successfully
- Health check returns 200

## Constraints
- Never deploy on Fridays after 3 PM
- Never deploy during incidents
- Always verify tests pass first
```

### Example: Generate Release Notes

**File:** `.claude/skills/custom/release-notes.md`

```markdown
---
description: Generate release notes from commits since last tag
tools: [Bash, Read, Write]
autoInvocable: false
---

# Generate Release Notes

## Objective
Create release notes from commits since the last release tag.

## Process

### 1. Find Last Tag
```bash
git describe --tags --abbrev=0
```

### 2. Get Commits Since Tag
```bash
git log $(git describe --tags --abbrev=0)..HEAD --oneline
```

### 3. Categorize Changes
Group commits by type:
- **Features** (feat:)
- **Bug Fixes** (fix:)
- **Breaking Changes** (BREAKING:)
- **Other** (docs, chore, refactor)

### 4. Generate Markdown
Create `RELEASE_NOTES.md`:

```markdown
# Release X.Y.Z

## Features
- Feature 1
- Feature 2

## Bug Fixes
- Fix 1

## Breaking Changes
- None

## Contributors
@contributor1, @contributor2
```

### 5. Review with User
Present the draft for review and editing.

## Success Criteria
- All commits are categorized
- Breaking changes are highlighted
- Release notes are readable
```

## Skill Best Practices

### Keep Skills Focused

```markdown
# Good: Single purpose
Deploy the current branch to staging.

# Bad: Too many responsibilities
Deploy to staging, run migrations, update DNS, notify team.
```

### Include Exact Commands

```markdown
# Good: Specific commands
Run: `dotnet test --no-build --verbosity normal`

# Bad: Vague instructions
Run the tests.
```

### Reference Standards

```markdown
## Process
1. Read `standards/dotnet.md` for testing requirements
2. Ensure code passes all quality gates
3. Follow deployment checklist in `docs/deployment.md`
```

### Add Constraints

```markdown
## Constraints
- Never skip tests, even for "small" changes
- Never deploy directly to production (use release branch)
- Always notify #deployments channel
```

### Handle Errors

```markdown
### Error Handling
If tests fail:
1. Report which tests failed
2. Suggest running `/fix tests`
3. Do NOT proceed with deployment
```

## Invoking Custom Skills

Custom skills are invoked like built-in skills:

```
/deploy-staging
/release-notes
/onboard-dev
```

## Auto-Invocable Skills

Set `autoInvocable: true` if Claude should trigger the skill automatically:

```yaml
---
autoInvocable: true
---
```

Use sparingly — most custom skills should require explicit invocation.

## Testing Custom Skills

1. Create the skill file
2. Open Claude Code
3. Type `/skill-name`
4. Verify it executes correctly
5. Iterate on the instructions

## Sharing Skills Across Teams

For organization-wide skills:

1. Create a shared skills repository
2. Copy skills to `custom/` during install
3. Or use the submodule approach for centralized management

---
**See also:** [Skills Overview](Skills-Overview) | [Custom Agents](Customization-Custom-Agents)
