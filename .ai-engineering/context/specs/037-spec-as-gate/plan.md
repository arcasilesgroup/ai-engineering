---
spec: "037"
approach: "serial-phases"
---

# Plan — Spec-as-Gate

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/cli_commands/spec_save.py` | CLI command: parse stdin, validate, scaffold, branch, commit |
| `.github/copilot-instructions.md` | GitHub Copilot IDE instructions |
| `.cursor/rules/ai-engineering.mdc` | Cursor IDE rules |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/cli_factory.py` | Register `spec save` subcommand |
| `.ai-engineering/agents/plan.md` | Produce spec as text + call `ai-eng spec save` + STOP |
| `.ai-engineering/skills/spec/SKILL.md` | Document CLI-driven path as preferred |
| `.ai-engineering/skills/plan/SKILL.md` | Reference CLI save in shared rules |

## File Structure

```
src/ai_engineering/cli_commands/spec_save.py   # New: CLI command
.github/copilot-instructions.md                 # New: Copilot config
.cursor/rules/ai-engineering.mdc                # New: Cursor config
.ai-engineering/agents/plan.md                  # Mod: text output + CLI
.ai-engineering/skills/spec/SKILL.md            # Mod: CLI path docs
.ai-engineering/skills/plan/SKILL.md            # Mod: reference CLI
src/ai_engineering/cli_factory.py               # Mod: register command
```

## Session Map

### Phase 1: CLI `ai-eng spec save` [M]

Build the deterministic CLI command that:
1. Reads spec markdown from stdin or `--file`
2. Parses frontmatter (title, slug, pipeline, size, tags)
3. Validates required sections (Problem, Solution, Scope, Acceptance Criteria)
4. Determines next spec number from `context/specs/`
5. Creates branch `feat/NNN-slug` (or uses current if already on feature branch)
6. Scaffolds `spec.md`, `plan.md`, `tasks.md` in `context/specs/NNN-slug/`
7. Updates `_active.md`
8. Atomic commit
9. Outputs confirmation

Register in `cli_factory.py`.

### Phase 2: Update agent + skills [S]

- `agents/plan.md`: change behavior to produce spec as structured text in conversation, then call `ai-eng spec save` via Bash, then STOP.
- `skills/spec/SKILL.md`: add "CLI-driven path" section documenting `ai-eng spec save` as preferred when invoked from `/ai:plan`.
- `skills/plan/SKILL.md`: add reference to CLI save mechanism.

### Phase 3: Cross-IDE configuration [S]

- `.github/copilot-instructions.md`: instructions for Copilot to follow the plan/execute flow.
- `.cursor/rules/ai-engineering.mdc`: same for Cursor.
- Brief docs section for other IDEs.

### Phase 4: Tests + validation [S]

- Unit tests for `spec_save.py` (parse, validate, scaffold).
- Integration test: stdin pipe -> spec files on disk.

## Patterns

- CLI command follows existing pattern in `src/ai_engineering/cli_commands/`.
- Spec scaffold reuses logic from existing spec creation (same directory structure, same frontmatter schema).
- Cross-IDE configs reference the same agents/skills — single source of truth.
