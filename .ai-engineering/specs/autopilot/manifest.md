# Autopilot Manifest: spec-087

## Split Strategy
by-layer: each sub-spec targets a distinct infrastructure layer (templates, sync engine, installer, docs, validator, tests, execution) to maximize parallelism while respecting data-flow dependencies.

## Sub-Specs

| # | Title | Status | Depends On | Files (best guess) |
|---|-------|--------|------------|---------------------|
| sub-001 | Codex & Gemini Template Surface | planning | None | `.codex/hooks.json`, `.codex/config.toml`, `.gemini/settings.json` (templates) |
| sub-002 | Sync Script Migration to .codex/ | planning | sub-001 | `scripts/sync_command_mirrors.py` |
| sub-003 | Installer Provider Remapping | planning | sub-001 | `installer/templates.py`, `installer/autodetect.py` |
| sub-004 | Instruction File Fixes | planning | None | `CLAUDE.md`, `GEMINI.md` (root + templates) |
| sub-005 | Validator & State Updates | planning | None | `validator/_shared.py`, `mirror_sync.py`, `defaults.py`, `manifest.yml`, `ownership-map.json` |
| sub-006 | Test Suite Updates | planning | sub-002, sub-003, sub-005 | `test_sync_mirrors.py`, `test_validator.py`, `test_autodetect.py`, `test_install_matrix.py` |
| sub-007 | Root Generation & Cleanup | planning | sub-002, sub-004, sub-006 | `.codex/`, `.agents/`, `AGENTS.md`, `GEMINI.md` (root) |

## Totals
- Sub-specs: 7
- Dependency chain depth: 3 (sub-001 -> sub-002 -> sub-006 -> sub-007)

## Traceability

| Spec Section | Sub-Spec(s) |
|-------------|-------------|
| G1: Eliminate .agents/ | sub-002, sub-007 |
| G2: .codex/ skills+agents | sub-001, sub-002 |
| G3: .codex/hooks.json | sub-001 |
| G4: .gemini/settings.json rewrite | sub-001 |
| G5: sync_command_mirrors.py | sub-002 |
| G6: Installer update | sub-003 |
| G7: Instruction files | sub-004 |
| G8: Validator | sub-005 |
| G9: Tests | sub-006 |
| G10: Hooks parity | sub-001, sub-002 |
