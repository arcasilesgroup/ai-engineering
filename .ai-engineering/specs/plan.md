---
spec: spec-192
executor: build
safe_next_command: "/ai-build"
automation: standard
concern_count: 5
estimated_files: 10
reason: "5 surgical fixes from telemetry deck; each 1–3 files, independent, verifiable"
version: 1
---

# Plan — spec-192: Telemetry deck follow-up

## Phase 1: instinct-observe PostToolUse-only (D-192-01)

- [x] T-1.1 — Remove instinct-observe from PreToolUse in .claude/settings.json
- Agent: build
- Files: `.claude/settings.json:108-118`
- Principles applied: §10.2 YAGNI (remove dead registration), §10.7 Clean Code
- Patch (deterministic):
  Remove the PreToolUse entry (lines 108-118) containing instinct-observe.py. Keep the PostToolUse entry (lines 120-129). The block to remove starts with `"matcher": ""` and contains `instinct-observe.py` in the command — it is the last entry in the PreToolUse array.
- Gate: `python -c "import json; d=json.load(open('.claude/settings.json')); pre=d['hooks'].get('PreToolUse',[]); assert not any('instinct-observe' in h.get('command','') for h in pre), 'still in PreToolUse'"`

- [x] T-1.2 — Remove instinct-observe from PreToolUse in template mirror
- Agent: build
- Files: `src/ai_engineering/templates/project/.claude/settings.json:127-136`
- Principles applied: §10.4 DRY (template parity), §10.7 Clean Code
- Patch (deterministic): Remove the same PreToolUse instinct-observe block from the template mirror. Lines 127-136 (the block with `"matcher": ""` and `instinct-observe.py` before `"PostToolUse"`).
- Gate: template parity test passes; same grep assertion as T-1.1 against template file

- [x] T-1.3 — Regenerate hooks-manifest
- Agent: build
- Files: `.ai-engineering/state/hooks-manifest.json`
- Principles applied: §10.7 Clean Code
- Patch (deterministic): `python .ai-engineering/scripts/regenerate-hooks-manifest.py`
- Gate: `python .ai-engineering/scripts/regenerate-hooks-manifest.py --check` exits 0

## Phase 2: ruff --fix before ralph retries (D-192-03)

- [x] T-2.1 — RED: unit test for auto-fix before retry
- Agent: build
- Files: `tests/unit/hooks/test_convergence.py` (extend existing)
- Principles applied: §10.5 TDD (RED before GREEN)
- Patch: test that `_fix_ruff` calls `ruff check --fix` and returns True on exit 0; test that `check_convergence` re-checks after fix and removes resolved failures. This test will FAIL until T-2.2 implements the function.
- Gate: `pytest tests/unit/hooks/test_convergence.py -v` — tests exist and fail (RED)

- [x] T-2.2 — GREEN: add auto-fix step in convergence when ruff fails
- Agent: build
- Files: `.ai-engineering/scripts/hooks/_lib/convergence.py:123-143`
- Principles applied: §10.1 KISS (one function, one subprocess), §10.5 TDD
- Patch: Add `_fix_ruff(project_root: Path) -> bool` that runs `ruff check --quiet --fix .` and returns True if exit 0. Call it from `check_convergence()` right after `_check_ruff()` returns a failure — if `_fix_ruff` succeeds, re-run `_check_ruff` and only keep the failure if it persists. ~15 lines total.
- Gate: `pytest tests/unit/hooks/test_convergence.py -v` passes (GREEN)

## Phase 3: risk accumulator precision (D-192-04)

- [x] T-3.1 — RED: unit test for accelerated decay + clean bonus
- Agent: build
- Files: `tests/unit/test_risk_accumulator.py` (extend existing)
- Principles applied: §10.5 TDD (RED before GREEN)
- Patch: assert `DECAY_PER_MINUTE == 0.90`; test that after 5 clean minutes score drops below block threshold; test clean bonus halves a score of 20 → 10 (still below block). Tests FAIL until T-3.2.
- Gate: `pytest tests/unit/test_risk_accumulator.py -v` — tests exist and fail (RED)

- [x] T-3.2 — GREEN: accelerate decay and add clean-session bonus
- Agent: build
- Files: `.ai-engineering/scripts/hooks/_lib/risk_accumulator.py:91,377-437`
- Principles applied: §10.1 KISS (constant change + one conditional), §10.7 Clean Code
- Patch:
  1. Line 91: `DECAY_PER_MINUTE = 0.95` → `0.90`
  2. Add constant: `CLEAN_BONUS = 0.5` (extra 50% decay when no findings in recent commands)
  3. In `add()` after computing `new_score` (line 410): check if last 3 events in ring buffer are all absent or have severity `silent`; if so, multiply score by `CLEAN_BONUS` before writing. Floor at 0.
- Gate: `pytest tests/unit/test_risk_accumulator.py -v` passes (GREEN)

- [x] T-3.3 — Scope env-var IOC to exfiltration forms
- Agent: build
- Files: `.ai-engineering/scripts/hooks/_lib/ioc_catalog.py` or `prompt-injection-guard.py` IOC pattern definitions
- Principles applied: §10.1 KISS (tighten regex, no new subsystem)
- Patch: Find env-var IOC patterns (e.g., `os.environ`, `process.env`) and wrap them in a lookahead that requires an exfiltration context word (`curl|wget|requests\.post|base64|subprocess|os\.system|pipe|\|`). Bare `os.environ` alone → no match.
- Gate: unit test — `os.environ` alone = no match, `curl $os.environ` = match

- [x] T-3.4 — Update risk_accumulator template mirror
- Agent: build
- Files: `src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/risk_accumulator.py`
- Principles applied: §10.4 DRY (template parity)
- Patch: Copy the updated risk_accumulator.py to the template mirror byte-for-byte. No CI guard for this pair — manual parity required.
- Gate: `diff .ai-engineering/scripts/hooks/_lib/risk_accumulator.py src/ai_engineering/templates/.ai-engineering/scripts/hooks/_lib/risk_accumulator.py` shows no differences

## Phase 4: mandatory verify gate in ai-pr (D-192-02)

- [x] T-4.1 — Add verify-absent check to ai-pr SKILL.md
- Agent: build
- Files: `.claude/skills/ai-pr/SKILL.md`
- Principles applied: §10.3 SOLID (single gate responsibility), §10.7 Clean Code
- Patch: Insert a new step between current Step 6 (pre-push) and Step 7 (commit pipeline):
  ```
  ### 6b. Verify gate (mandatory)
  Before proceeding to commit pipeline, check whether ai-verify has run on the
  current changeset this session. If no verify outcome exists (no `verify` in
  session context, no prior ai-verify dispatch on this branch), dispatch
  ai-verify inline and wait for completion. Log the auto-dispatch as a
  framework_operation. Never skip this gate — it is the safety net for
  direct /ai-pr invocations outside the canonical chain.
  ```
- Gate: manual review that SKILL.md has the new step with correct numbering

## Phase 5: auto re-pin manifest in dev sync (D-192-05)

- [x] T-5.1 — Add _finalize_hooks_manifest call to dev_sync_cmd
- Agent: build
- Files: `src/ai_engineering/cli_commands/dev_sync.py:79-100`
- Principles applied: §10.4 DRY (reuse existing finalizer), §10.1 KISS
- Patch: After the `sync_command_mirrors` subprocess succeeds (exit 0, after the catalog update block around line 90), add:
  ```python
  from ai_engineering.cli_commands.core import _finalize_hooks_manifest
  _finalize_hooks_manifest(root)
  ```
  Import at top of file. Fail-open (the function itself never raises).
- Gate: `python -c "from ai_engineering.cli_commands.dev_sync import dev_sync_cmd; print('ok')"`

- [x] T-5.2 — Verify install + update finalize call sites
- Agent: verify
- Files: `src/ai_engineering/cli_commands/core.py:238,1175`
- Principles applied: §10.5 TDD (verify existing behavior)
- Patch: No code change — verification only. Grep confirms `_finalize_hooks_manifest(root)` at line 238 (install) and `_finalize_update_hooks_manifest(workflow_result, root)` at line 1175 (update).
- Gate: `grep -n "_finalize_hooks_manifest\|_finalize_update_hooks_manifest" src/ai_engineering/cli_commands/core.py` shows both call sites

## Phase 6: mirror sync + parity

- [x] T-6.1 — Run ai-eng dev sync for mirror parity
- Agent: build
- Files: `.codex/`, `.agents/`, `.github/` mirrors
- Principles applied: §10.4 DRY
- Patch: `python scripts/sync_command_mirrors.py`
- Gate: `ai-eng dev sync --check` exits 0

## Phase 7: quality gate

- [x] T-7.1 — Run full test suite
- Agent: verify
- Files: tests/
- Principles applied: §10.5 TDD
- Gate: `pytest tests/ -x --timeout=60` passes

- [x] T-7.2 — Run lint + format check
- Agent: verify
- Files: src/, .ai-engineering/scripts/
- Principles applied: §10.7 Clean Code
- Gate: `ruff check . && ruff format --check .` passes
