---
spec: "034"
slug: "spec-lifecycle-cli"
completed: "2025-07-15"
---

# Done — Spec Lifecycle CLI + Closure Normalization

## Summary

Implemented the full spec lifecycle CLI tooling and closure normalization for the ai-engineering framework. This spec delivered:

1. **Shared frontmatter parser** (`lib/parsing.py`) — single source of truth for `parse_frontmatter()` and `count_checkboxes()`, replacing duplicated inline parsers in `spec_reset.py` and `sync_command_mirrors.py`.

2. **Closure fix** — `done.md` is now mandatory for spec closure. `completed==total` alone produces a warning, not closure. This prevents premature archival.

3. **Spec CLI commands** (`ai-eng spec`):
   - `verify` — counts checkboxes, auto-corrects frontmatter counters, emits audit signal.
   - `catalog` — regenerates `_catalog.md` from all archived specs with table + tag index.
   - `list` — displays active spec with progress percentage.
   - `compact` — removes bulky files from old archived specs (keeps `done.md`), supports `--dry-run` and `--older-than`.

4. **Decision record CLI** (`ai-eng decision record`) — dual-write protocol: persists to `decision-store.json` AND `audit-log.ndjson` in a single command.

5. **Validator regex fix** — `manifest_coherence.py` now handles unquoted `null`/`none`/`~` values in `_active.md` and looks up specs in both `context/specs/` and `context/specs/archive/`.

6. **Skill + standards updates** — enriched frontmatter in spec scaffold (size, tags, branch, pipeline, decisions), integrated `spec verify`/`catalog` into commit/pr/cleanup workflows, documented new CLI commands in `core.md`.

7. **Mirror sync** — all 84 mirror files (Claude commands, Copilot prompts, Copilot agents, governance templates) synchronized. `ai-eng validate` passes 7/7 categories.

## Verification

- 1018 unit tests pass
- `ruff check src/ tests/` — all checks passed
- `ty check src/` — all checks passed
- `ai-eng validate` — 7/7 categories pass
- `ai-eng spec verify` — counters match
- `ai-eng spec catalog` — 33 specs cataloged
- All pre-commit gates pass (branch-protection, gitleaks, ruff-format, ruff-lint, hook-integrity, commit-msg-format)

## New Files

| File | Purpose |
|------|---------|
| `src/ai_engineering/lib/parsing.py` | Shared frontmatter parser + checkbox counter |
| `src/ai_engineering/cli_commands/spec_cmd.py` | Spec lifecycle CLI (verify, catalog, list, compact) |
| `tests/unit/test_parsing.py` | 14 tests for parsing module |
| `tests/unit/test_spec_cmd.py` | 15 tests for spec CLI commands |
| `.ai-engineering/context/specs/_catalog.md` | Auto-generated spec catalog |

## Modified Files

| File | Change |
|------|--------|
| `src/ai_engineering/maintenance/spec_reset.py` | Delegates to shared parser, closure fix |
| `scripts/sync_command_mirrors.py` | Delegates to shared parser |
| `src/ai_engineering/cli_factory.py` | Registered spec + decision record commands |
| `src/ai_engineering/cli_commands/decisions_cmd.py` | Added `record` subcommand |
| `src/ai_engineering/state/service.py` | Added `save_decisions()` |
| `src/ai_engineering/validator/categories/manifest_coherence.py` | Regex fix + archive lookup |
| `tests/unit/test_cli_decisions.py` | 6 new tests for decision record |
| `tests/unit/test_validator_extra.py` | 3 new tests for validator fixes |
| `tests/unit/maintenance/test_spec_reset.py` | Updated for closure semantics |

## Deferred

- **Spec B/C/D** from the Architecture Evolution Plan v3.1 — signal enrichment, session checkpoint CLI, progressive disclosure enforcement — to be addressed in follow-up specs.
