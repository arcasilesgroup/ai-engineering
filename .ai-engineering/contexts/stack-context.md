# Stack Context Protocol

Coding standards loading sequence. Skills reference this file to load language, framework, and team
contexts on demand. Project state (spec, plan, decisions, constitution, manifest) is loaded once at
session start by `/ai-start` — do not re-read those files here.

## Sequence

1. **Detect stacks** -- read `.ai-engineering/manifest.yml` field `providers.stacks`
2. **Language contexts** -- for each detected language, read `.ai-engineering/contexts/languages/{lang}.md`
   Available (14): bash, cpp, csharp, dart, go, java, javascript, kotlin, php, python, rust, sql, swift, typescript
3. **Framework contexts** -- for each detected framework, read `.ai-engineering/contexts/frameworks/{fw}.md`
   Available (15): android, api-design, aspnetcore, backend-patterns, bun, claude-api, deployment-patterns, django, flutter, ios, mcp-sdk, nextjs, nodejs, react, react-native
4. **Shared framework contexts** -- when relevant, read:
   - `.ai-engineering/contexts/cli-ux.md` for CLI/UI output work
   - `.ai-engineering/contexts/mcp-integrations.md` for MCP/server usage work
5. **Team conventions** -- read all files in `.ai-engineering/contexts/team/*.md`

## Usage

Skills declare Step 0 as:

```
### Step 0: Load Stack Contexts
Follow `.ai-engineering/contexts/stack-context.md`. Apply loaded standards to all subsequent work.
```

This protocol loads only coding standards. `/ai-start` owns project state loading at session start.
