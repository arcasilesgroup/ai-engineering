---
spec: "034"
approach: "serial-phases"
---

# Plan — Spec Lifecycle CLI + Closure Normalization

## Architecture

### New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/lib/parsing.py` | Shared frontmatter parser — single source of truth for `---` fence parsing, consumed by `spec_reset`, `sync_command_mirrors`, `spec_cmd` |
| `src/ai_engineering/cli_commands/spec_cmd.py` | Typer subgroup: `verify`, `catalog`, `list`, `compact` subcommands |
| `.ai-engineering/context/specs/_catalog.md` | Generated spec catalog with table + tag index (artifact of `ai-eng spec catalog`) |
| `tests/unit/test_parsing.py` | Unit tests for shared frontmatter parser |
| `tests/unit/test_spec_cmd.py` | Unit tests for spec CLI subcommands (verify, catalog, compact) |

### Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/maintenance/spec_reset.py` | Import parser from `lib/parsing.py`; fix closure: `done.md` mandatory, `completed==total` is warning only |
| `scripts/sync_command_mirrors.py` | Import parser from `lib/parsing.py` instead of inline `parse_frontmatter()` |
| `src/ai_engineering/cli_factory.py` | Register `spec_app` Typer subgroup (pattern: `decision_app` at L339) |
| `src/ai_engineering/validator/categories/manifest_coherence.py` | Fix regex at L69 to handle unquoted values (`null`, `none`); prepare for list format |
| `src/ai_engineering/cli_commands/decisions_cmd.py` | Add `record` subcommand for dual-write protocol |
| `.ai-engineering/skills/spec/SKILL.md` | Enriched frontmatter scaffold (size, tags, branch, pipeline, decisions); dual-write protocol |
| `.ai-engineering/skills/commit/SKILL.md` | Add `ai-eng spec verify` invocation before commit |
| `.ai-engineering/skills/pr/SKILL.md` | Add `ai-eng spec verify` + `ai-eng spec catalog` at closure |
| `.ai-engineering/skills/cleanup/SKILL.md` | Add `ai-eng spec compact --dry-run` in cleanup flow |
| `.ai-engineering/standards/framework/core.md` | Document enriched frontmatter schema |
| `.ai-engineering/context/product/product-contract.md` | Sync figures with current state |
| `tests/unit/maintenance/test_spec_reset.py` | Update tests for new closure semantics (done.md mandatory) |
| `tests/unit/test_decisions_cmd.py` | Add tests for `record` subcommand |

### Mirror Copies

| Canonical | Mirrors |
|-----------|---------|
| `.ai-engineering/skills/spec/SKILL.md` | `.claude/commands/ai/spec.md`, `.github/prompts/ai-spec.prompt.md` |
| `.ai-engineering/skills/commit/SKILL.md` | `.claude/commands/ai/commit.md`, `.github/prompts/ai-commit.prompt.md` |
| `.ai-engineering/skills/pr/SKILL.md` | `.claude/commands/ai/pr.md`, `.github/prompts/ai-pr.prompt.md` |
| `.ai-engineering/skills/cleanup/SKILL.md` | `.claude/commands/ai/cleanup.md`, `.github/prompts/ai-cleanup.prompt.md` |

## File Structure

```
src/ai_engineering/
├── lib/
│   └── parsing.py           # NEW — shared frontmatter parser
├── cli_commands/
│   ├── spec_cmd.py           # NEW — verify, catalog, list, compact
│   └── decisions_cmd.py      # MODIFIED — add record
├── maintenance/
│   └── spec_reset.py         # MODIFIED — use shared parser, fix closure
├── validator/
│   └── categories/
│       └── manifest_coherence.py  # MODIFIED — fix active regex
└── cli_factory.py            # MODIFIED — register spec_app

tests/
├── unit/
│   ├── test_parsing.py       # NEW
│   ├── test_spec_cmd.py      # NEW
│   ├── test_decisions_cmd.py # MODIFIED
│   └── maintenance/
│       └── test_spec_reset.py # MODIFIED
```

## Session Map

### Phase 0: Scaffold [S]
- Create spec branch, scaffold files, activate, commit.
- ~15 min, 1 commit.

### Phase 1: Shared Parser + Closure Fix [M]
- Create `lib/parsing.py` with `parse_frontmatter()` and `count_checkboxes()`.
- Refactor `spec_reset.py` to use shared parser; fix closure semantics.
- Refactor `sync_command_mirrors.py` to use shared parser.
- Tests for parser and updated closure behavior.
- ~45 min, 1 commit.

### Phase 2: Spec CLI Commands [L]
- Create `spec_cmd.py` with `verify`, `catalog`, `list`, `compact` subcommands.
- Register in `cli_factory.py`.
- `verify`: count checkboxes, auto-correct frontmatter, emit signal.
- `catalog`: traverse specs, generate `_catalog.md`.
- `list`: display active specs with progress.
- `compact`: archive old specs (--dry-run, --older-than).
- Tests for all subcommands.
- ~90 min, 1 commit.

### Phase 3: Validator Fix + Decision Record [M]
- Fix `manifest_coherence.py` regex for unquoted `active:` values.
- Add `record` subcommand to `decisions_cmd.py`.
- Tests for both changes.
- ~30 min, 1 commit.

### Phase 4: Skill + Standards Updates [M]
- Update `spec/SKILL.md` — enriched frontmatter, dual-write protocol.
- Update `commit/SKILL.md` — `ai-eng spec verify` invocation.
- Update `pr/SKILL.md` — `ai-eng spec verify` + `ai-eng spec catalog`.
- Update `cleanup/SKILL.md` — `ai-eng spec compact --dry-run`.
- Update `standards/framework/core.md` — enriched frontmatter docs.
- Update `product-contract.md` — sync figures.
- Run `scripts/sync_command_mirrors.py` to sync all mirrors.
- ~45 min, 1 commit.

### Phase 5: Verification + Close [S]
- Run full test suite, linting, type checking.
- Run `ai-eng validate`.
- Generate initial `_catalog.md` via `ai-eng spec catalog`.
- Create `done.md`, update `_active.md`, create PR.
- ~20 min, 1 commit.

## Patterns

- **Architecture layers**: CLI (`spec_cmd.py`) → service (`lib/parsing.py`) → I/O (filesystem). No layer skipping.
- **Error boundary**: All CLI commands wrapped in `_safe()` / `_cli_error_boundary`.
- **Signal emission**: Every state-changing CLI command emits an event via `lib/signals.py`.
- **Backward compatibility**: Enriched frontmatter fields are additive; old specs without them are handled gracefully.
- **Test pattern**: AAA (Arrange-Act-Assert); reuse `_create_spec_dir()` helper from existing tests.
