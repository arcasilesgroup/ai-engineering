# Autopilot Manifest: spec-064

## Split Strategy
by-dependency — linear chain where each sub-spec builds on the previous. Template files first, then infrastructure, then phases, then orchestration, then UX, then tests.

## Sub-Specs

| # | Title | Status | Depends On | Work Units | Estimated Complexity |
|---|-------|--------|------------|------------|---------------------|
| sub-001 | Template Parity | complete | None | 5 | medium |
| sub-002 | Templates Public API + VCS Fix | pending | sub-001 | 3 | low |
| sub-003 | Phase Pipeline Foundation | pending | sub-002 | 4 | high |
| sub-004 | Core Phases + Merge | pending | sub-003 | 5 | high |
| sub-005 | Service Refactor + Update Migration | pending | sub-004 | 5 | high |
| sub-006 | Wizard UX + CLI Modes | pending | sub-005 | 5 | high |
| sub-007 | Tests + CI | pending | sub-006 | 5 | medium |

## Totals
- Sub-specs: 7
- Work units: 32
- Dependency chain depth: 7 (linear)

## File Ownership (no overlaps)

| Sub-Spec | Files |
|----------|-------|
| sub-001 | `templates/project/scripts/hooks/**`, `templates/project/.claude/settings.json`, `templates/.ai-engineering/context*/`, `templates/project/.ai-engineering/` |
| sub-002 | `src/ai_engineering/installer/templates.py` |
| sub-003 | `src/ai_engineering/installer/phases/__init__.py`, `phases/detect.py`, `phases/pipeline.py` |
| sub-004 | `src/ai_engineering/installer/phases/governance.py`, `phases/ide_config.py`, `phases/hooks.py`, `phases/state.py`, `phases/tools.py`, `installer/merge.py` |
| sub-005 | `src/ai_engineering/installer/service.py`, `src/ai_engineering/updater/service.py` |
| sub-006 | `src/ai_engineering/cli_commands/core.py`, `src/ai_engineering/installer/ui.py` |
| sub-007 | `tests/unit/installer/**`, `tests/integration/**`, `.github/workflows/install-smoke.yml` |
