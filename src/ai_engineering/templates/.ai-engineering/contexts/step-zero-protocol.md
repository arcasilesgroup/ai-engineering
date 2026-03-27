# Step 0 -- Context Loading Protocol

Canonical context loading sequence. Skills reference this file instead of inlining these steps.

## Sequence

1. **Active spec** -- read `.ai-engineering/specs/spec.md`
2. **Active plan** -- read `.ai-engineering/specs/plan.md`
3. **Decisions** -- read `.ai-engineering/state/decision-store.json`
4. **Project identity** -- read `.ai-engineering/contexts/project-identity.md` (skip if absent)
5. **Detect stacks** -- read `.ai-engineering/manifest.yml` field `providers.stacks`
6. **Language contexts** -- for each detected language, read `.ai-engineering/contexts/languages/{lang}.md`
   Available (14): bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, rust, sql, swift, typescript
7. **Framework contexts** -- for each detected framework, read `.ai-engineering/contexts/frameworks/{fw}.md`
   Available (15): android, api-design, aspnetcore, backend-patterns, bun, claude-api, deployment-patterns, django, flutter, ios, mcp-sdk, nextjs, nodejs, react, react-native
8. **Team conventions** -- read all files in `.ai-engineering/contexts/team/*.md`

## Usage

Skills declare Step 0 as:

```
### Step 0: Load Contexts
Follow `.ai-engineering/contexts/step-zero-protocol.md`. Apply loaded standards to all subsequent work.
```

Steps 1-4 establish project state. Steps 5-8 load coding standards. All steps are ordered -- later steps may depend on earlier context.
