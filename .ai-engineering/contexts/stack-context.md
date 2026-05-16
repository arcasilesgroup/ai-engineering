# Stack Context Protocol

Coding standards loading sequence. Skills reference this file to load stack-specific
overrides and team conventions on demand. Project state (spec, plan, decisions,
constitution, manifest) is loaded once at session start by `/ai-start` — do not
re-read those files here.

## Sequence

1. **Detect stacks** -- read `.ai-engineering/manifest.yml` field `providers.stacks`
2. **Stack overrides** -- for each detected stack, read `.ai-engineering/overrides/{stack}/conventions.md`
   Supported (7): python, typescript, go, rust, swift, csharp, kotlin (spec-128 D-128-09).
   Framework variants (Azure, React, Django, etc.) live as sections inside the stack's
   `conventions.md` rather than separate files.
3. **Shared overrides** -- read `.ai-engineering/overrides/_shared/conventions.md` for
   cross-stack rules (compliance, security floor common to all stacks).
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

## Migration note (spec-128)

Pre-spec-128 layout used `.ai-engineering/contexts/languages/{lang}.md` (14 files) and
`.ai-engineering/contexts/frameworks/{fw}.md` (15 files). Both directories deleted
per D-128-03 (training-redundant content; model has stronger priors than 200-line
markdown). New layout: `.ai-engineering/overrides/{stack}/` with project-specific
deltas only.
