---
id: sub-001
parent: spec-079
title: "Hooks Cleanup"
status: planning
files: [".ai-engineering/scripts/hooks/telemetry-skill.sh", ".ai-engineering/scripts/hooks/telemetry-session.sh", ".ai-engineering/scripts/hooks/telemetry-agent.sh", ".ai-engineering/scripts/hooks/telemetry-skill.ps1", ".ai-engineering/scripts/hooks/telemetry-session.ps1", ".ai-engineering/scripts/hooks/telemetry-agent.ps1", "src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-skill.sh", "src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-session.sh", "src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-agent.sh", "src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-skill.ps1", "src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-session.ps1", "src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-agent.ps1", "scripts/hooks/", "tests/unit/test_template_parity.py"]
depends_on: []
---

# Sub-Spec 001: Hooks Cleanup

## Scope

Eliminate 6 dead migration artifacts from hooks (telemetry-*.sh/.ps1 without copilot- prefix) from both templates and dogfood installation. Remove ghost directory `scripts/hooks/` at top-level. Preserve all active hooks (.py for Claude Code, copilot-*.sh/.ps1 for GitHub Copilot). Update test_template_parity.py if affected.

## Exploration

### Dead Files to Delete (6 per location = 12 total)

**Dogfood installation** (`.ai-engineering/scripts/hooks/`):
1. `telemetry-skill.sh` -- 1779 bytes, superseded by `telemetry-skill.py`
2. `telemetry-skill.ps1` -- 1547 bytes, superseded by `telemetry-skill.py`
3. `telemetry-session.sh` -- 1060 bytes, superseded by `cost-tracker.py`
4. `telemetry-session.ps1` -- 705 bytes, superseded by `cost-tracker.py`
5. `telemetry-agent.sh` -- 2717 bytes, superseded by `observe.py`
6. `telemetry-agent.ps1` -- 1636 bytes, superseded by `observe.py`

**Template installation** (`src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/`):
Same 6 files with slightly different sizes (template copies diverged from dogfood):
1. `telemetry-skill.sh` -- 2163 bytes
2. `telemetry-skill.ps1` -- 1547 bytes
3. `telemetry-session.sh` -- 1060 bytes
4. `telemetry-session.ps1` -- 705 bytes
5. `telemetry-agent.sh` -- 3028 bytes
6. `telemetry-agent.ps1` -- 1636 bytes

### Ghost Directory

`scripts/hooks/` at top-level contains only `_lib/__pycache__/*.pyc` files (3 untracked `.pyc` files). No tracked files exist under `scripts/hooks/`. The entire directory tree is safe to remove physically.

### Active Hooks to PRESERVE (DO NOT DELETE)

**Claude Code (.py hooks)** -- referenced in `.claude/settings.json`:
- `telemetry-skill.py` -- emits `skill_invoked`, called via `UserPromptSubmit`
- `auto-format.py`, `cost-tracker.py`, `instinct-extract.py`, `mcp-health.py`, `observe.py`, `prompt-injection-guard.py`, `strategic-compact.py`
- `_lib/` directory (`__init__.py`, `audit.py`, `injection_patterns.py`)

**GitHub Copilot (copilot-*.sh/.ps1 hooks)** -- referenced in `.github/hooks/hooks.json`:
- `copilot-telemetry-skill.sh` -- wrapper that delegates to `telemetry-skill.py`
- All other `copilot-*.sh` and `copilot-*.ps1` files (13 total)

### References to Dead Files Found in Codebase

| File | Reference | Action |
|------|-----------|--------|
| `tests/integration/test_telemetry_canary.py` | Lines 34-35, 47-48: parametrized tests assert `.sh` and `.ps1` exist; Line 105: template sync checks `telemetry-skill.sh` and `telemetry-session.sh` | Update: rewrite tests to assert `.py` hooks and `copilot-*` wrappers instead |
| `src/ai_engineering/templates/project/github_templates/hooks/hooks.json` | Lines 5, 10, 15: references `telemetry-skill.sh`, `telemetry-session.sh`, `telemetry-agent.sh` | Update: replace with `copilot-telemetry-skill.sh`, `copilot-session-end.sh`, `copilot-agent.sh` |
| `docs/solution-intent.md` | Lines 617-619: lists `telemetry-skill.sh/.ps1`, `telemetry-agent.sh/.ps1`, `telemetry-session.sh/.ps1` | Update: replace with current hook names (`.py` + `copilot-*`) |
| `CHANGELOG.md` | Lines 120, 126: historical mentions | No action: changelog is historical record, do not rewrite |
| `.ai-engineering/scripts/hooks/observe.py` | Line 5: docstring mentions "telemetry-agent.sh" | Update: change comment to note it replaced that script |
| `.ai-engineering/scripts/hooks/cost-tracker.py` | Line 4: docstring mentions "telemetry-session.sh" | Update: change comment to note it replaced that script |
| `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/observe.py` | Line 5: same as dogfood | Update: same change |
| `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/cost-tracker.py` | Line 4: same as dogfood | Update: same change |
| `.ai-engineering/scripts/hooks/telemetry-skill.py` | Line 6: docstring mentions "telemetry-skill.sh" | Update: change comment to note it replaced that script |
| `src/ai_engineering/templates/project/.ai-engineering/scripts/hooks/telemetry-skill.py` | Line 6: same as dogfood | Update: same change |

### Settings Files Verification

- `.claude/settings.json` -- references only `.py` hooks. No `.sh`/`.ps1` references. CLEAN.
- `.github/hooks/hooks.json` -- references only `copilot-*.sh`/`copilot-*.ps1` hooks. CLEAN.

### Test Impact Analysis

- `tests/unit/test_template_parity.py` -- counts files in both hooks dirs and asserts parity. Deleting the same 6 files from BOTH locations preserves parity. NO code changes needed in this file as long as deletions are symmetrical.
- `tests/integration/test_telemetry_canary.py` -- directly asserts dead `.sh`/`.ps1` files exist. MUST be updated.
