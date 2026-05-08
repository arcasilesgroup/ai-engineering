---
total: 38
completed: 0
---

# Plan: sub-006 M5 — Hexagonal seams

## Pipeline: full
## Phases: 9
## Tasks: 38 (build: 31, verify: 7)

## Architecture

**Pattern**: Hexagonal Architecture (Ports & Adapters), explicit.
- `tools/skill_domain/` — pure dataclasses, validators, rules. Allowed
  imports: stdlib, `typing`, other `tools.skill_domain.*`. Banned: `skill_app`,
  `skill_infra`, `requests`, `httpx`, `subprocess`.
- `tools/skill_app/` — use cases + port definitions. Allowed:
  `skill_domain.*`, `skill_app.*`, stdlib. Banned: `skill_infra.*`.
- `tools/skill_app/ports/` — abstract Protocol/ABC files only.
- `tools/skill_infra/` — one adapter per file, each implementing exactly one
  port. Allowed: anything (subprocess, MCP clients, network, fs).

Dependency arrow: `infra → app → domain`. `tests/architecture/test_layer_isolation.py`
walks `tools/skill_domain/`, AST-parses imports, asserts none resolves into
`tools.skill_infra`. RED first; every GREEN task forbidden to touch the test.

**Justification**: D-127-09 enforced via test (not custom lint plugin). Brief
§9 hexagonal seams; brief §22 split contract.

## Design

Skipped — file moves + import rewrites only.

## Phase classification: full

Module moves + port definition + import rewrites + isolation test. Touches
>5 files across two directory trees and adds a new test surface.

### Phase 0 — Pre-flight

**Gate**: M1 scaffolding present; M4 renames live.

- [ ] T-6.0.1: Verify `tools/skill_domain/__init__.py`,
  `tools/skill_app/__init__.py`, `tools/skill_app/ports/__init__.py`,
  `tools/skill_infra/__init__.py` exist (M1 sub-002 T-2.9). If absent, BLOCK on
  M1 (agent: verify)
- [ ] T-6.0.2: Verify `.claude/skills/ai-skill-tune/SKILL.md` and
  `.claude/skills/ai-ide-audit/SKILL.md` exist (post-M4). If absent, BLOCK on
  M4 (agent: verify)
- [ ] T-6.0.3: Run full pytest; record baseline pass count for diff later
  (agent: verify)

### Phase 1 — RED: layer-isolation test

**Gate**: `tests/architecture/test_layer_isolation.py` exists, fails (empty
walk), is the only file added in this commit.

- [ ] T-6.1: Add `tests/architecture/__init__.py` (empty) +
  `test_layer_isolation.py`. Test walks `tools/skill_domain/` recursively,
  AST-parses each `.py`, collects all imports, asserts none start with
  `tools.skill_infra`. Asserts ≥1 module walked (no vacuous pass) (agent: build)

### Phase 2 — Domain moves (one module per commit)

**Gate per commit**: pytest baseline pass count holds; `git diff --stat`
≤200 LOC.

- [ ] T-6.2.1: Move `event_schema.py`; install one-line re-export shim. **DO
  NOT modify test files from T-6.1.** (agent: build)
- [ ] T-6.2.2: Move `models.py`; shim (agent: build)
- [ ] T-6.2.3: Move `decision_logic.py`; shim (agent: build)
- [ ] T-6.2.4: Move `standards.py`; shim (agent: build)
- [ ] T-6.2.5: Move `validators/skill_frontmatter.py`; shim (agent: build)
- [ ] T-6.2.6: Move `validators/cross_references.py`; shim (agent: build)
- [ ] T-6.2.7: Move `validators/counter_accuracy.py`; shim (agent: build)

### Phase 3 — Ports definition (single commit)

**Gate**: 8 port Protocol files in `tools/skill_app/ports/`; import-clean; no
infra imports; total LOC ≤200.

- [ ] T-6.3: Author 8 ports in `tools/skill_app/ports/{skill,agent,hook,
  board,memory,telemetry,mirror,research}.py` (signatures only). Update
  `__init__.py` to re-export. **DO NOT modify test files from T-6.1.**
  (agent: build)

### Phase 4 — App moves (one module per commit)

**Gate per commit**: pytest baseline holds; ≤200 LOC.

- [ ] T-6.4.1: Move `skills/service.py` → `skill_service.py`; rewrite I/O
  through `SkillPort` constructor-injected; shim. SPLIT into 4.1a/b/c if
  >200 LOC (agent: build)
- [ ] T-6.4.2: Move `validator/service.py` → `lint_service.py`; shim
  (agent: build)
- [ ] T-6.4.3: Move `validator/_shared.py` → `_lint_shared.py`; shim
  (agent: build)
- [ ] T-6.4.4: Move `manifest_coherence.py`; rewrite fs I/O through
  `SkillPort` + `MirrorPort`; shim. SPLIT 4.4a/b expected (agent: build)
- [ ] T-6.4.5: Move `required_tools.py` → `tool_audit.py`; shim (agent: build)
- [ ] T-6.4.6: Move `file_existence.py` → `file_existence_audit.py`; shim
  (agent: build)
- [ ] T-6.4.7: Move `governance/policy_engine.py` → `policy_engine.py`; shim
  (agent: build)
- [ ] T-6.4.8: Move `governance/decision_log.py` → `decision_log_service.py`;
  shim (agent: build)
- [ ] T-6.4.9: Move `work_items/service.py` → `work_item_service.py`; shim
  (agent: build)

### Phase 5 — Infra moves (one adapter per commit)

**Gate per commit**: pytest baseline holds; ≤200 LOC; each new file declares
its port in module docstring.

- [ ] T-6.5.1: `skills/service.py` fs-touching half → `skill_fs_adapter.py`
  (`SkillPort`); shim (agent: build)
- [ ] T-6.5.2: Author `agent_fs_adapter.py` (`AgentPort`) (agent: build)
- [ ] T-6.5.3: Move `regenerate-hooks-manifest.py` → `hook_manifest_adapter.py`
  (agent: build)
- [ ] T-6.5.4: Move `.ai-engineering/scripts/hooks/` (22 hooks) →
  `tools/skill_infra/hooks/` preserving tree. Use `git mv`. SPLIT 4a/b
  if size cap exceeded (agent: build)
- [ ] T-6.5.5: Move `azure_devops.py` → `board_ado_adapter.py` (`BoardPort`);
  shim (agent: build)
- [ ] T-6.5.6: Move `github.py` → `board_github_adapter.py` (`BoardPort`);
  shim (agent: build)
- [ ] T-6.5.7: Move `detector.py` → `board_detector.py`; shim (agent: build)
- [ ] T-6.5.8: Extract `installer/engram.py` MCP-client portion →
  `engram_adapter.py` (`MemoryPort`). Installer-side preserves install logic
  (agent: build)
- [ ] T-6.5.9: Author `notebooklm_adapter.py` (`ResearchPort`) (agent: build)
- [ ] T-6.5.10: Author `context7_adapter.py` (`ResearchPort`) (agent: build)
- [ ] T-6.5.11: Move `sync_command_mirrors.py` → `mirror_sync_adapter.py`
  (`MirrorPort`); thin shim at old path (agent: build)
- [ ] T-6.5.12: Move `scripts/sync_mirrors/` (7 files) →
  `tools/skill_infra/sync_mirrors/` (agent: build)
- [ ] T-6.5.13: Move `audit_chain.py` → `telemetry_audit_adapter.py`
  (`TelemetryPort`); shim (agent: build)
- [ ] T-6.5.14: Move `audit_otel_export.py` → `telemetry_otel_adapter.py`
  (`TelemetryPort`); shim (agent: build)

### Phase 6 — Skill-body import rewrites (one skill per commit)

**Behavior-change ban — extra-strict**: edits limited to literal command-string
substitutions per Exploration table. No prose / triggers / description edits.
Reviewer gate: each P6 commit ≤6 lines changed in SKILL.md diff.

- [ ] T-6.6.1: Rewrite `ai-create/SKILL.md` — substitutions per Exploration
  table (agent: build)
- [ ] T-6.6.2: Rewrite `ai-prompt/SKILL.md` — single substitution (agent: build)
- [ ] T-6.6.3: Rewrite `ai-skill-tune/SKILL.md` — Engram + eval shell-out →
  `tune_service` CLI (agent: build)
- [ ] T-6.6.4: Rewrite `ai-ide-audit/SKILL.md` — hook-byte / mirror-tree walk
  → `python -m tools.skill_app.ide_audit --full` (agent: build)

### Phase 7 — GREEN + size-cap verification

**Gate**: layer-isolation test passes; per-commit size cap verified across M5
commit range.

- [ ] T-6.7.1: Run `pytest tests/architecture/test_layer_isolation.py` →
  green. **DO NOT modify the test file from T-6.1.** (agent: verify)
- [ ] T-6.7.2: Run full pytest → baseline pass count ≤ now-pass count
  (agent: verify)
- [ ] T-6.7.3: For every commit in M5 range, verify `git diff --stat <c>^..<c>`
  ≤200 LOC (CI gate per umbrella T-6.8) (agent: verify)

### Phase 8 — Closeout (re-export shim sweep)

**Gate**: every shim added during P2/P4/P5 either deleted (callers rewritten)
OR documented as deferred.

- [ ] T-6.8.1: Inventory shims via `git grep -l 'from tools.skill_(domain|app|infra)'`
  (agent: verify)
- [ ] T-6.8.2: Delete shims where call-site rewrite fits in ≤200 LOC commit
  each (agent: build)
- [ ] T-6.8.3: For shims not deletable in M5, document as deferred under
  parent plan Self-Report (agent: build)
- [ ] T-6.8.4: Final pytest + layer-isolation green + size cap green; mark
  ready-for-review (agent: verify)

## Phase Dependency Graph

```
P0 ─→ P1 (RED) ─→ P2 (domain) ─→ P3 (ports) ─→ P4 (app) ─→ P5 (infra) ─→ P6 (skills) ─→ P7 (GREEN+cap) ─→ P8 (closeout)
```

## TDD Pairing

- T-6.1 (RED) → T-6.2.1..T-6.2.7 (first GREEN)
- T-6.3 (ports) → T-6.4.* / T-6.5.* depend on it
- GREEN constraint on every task after T-6.1: **DO NOT modify
  `tests/architecture/test_layer_isolation.py` from T-6.1.**

## Behavior-change ban — flagged tasks

- T-6.4.1 (skill_service): port-injection rewrite. Mitigation: split 4.1a/b/c.
- T-6.4.4 (manifest_coherence): heaviest validator. Split 4.4a/b expected.
- T-6.5.4 (hook bytes): 22 hooks. Must split 4.4a (move) + 4.4b (rewrite callers).
- T-6.5.8 (engram extract): client-only; verify no install side effects.

Any task >200 LOC must split before proceeding.

## Done Conditions

- [ ] `tests/architecture/test_layer_isolation.py` green
- [ ] Zero `tools.skill_infra` imports under `tools/skill_domain/` (AST-asserted)
- [ ] All 8 ports declared in `tools/skill_app/ports/`
- [ ] Each `tools/skill_infra/*.py` adapter declares its single port in module
  docstring
- [ ] Four SKILL.md bodies (`/ai-create`, `/ai-prompt`, `/ai-skill-tune`,
  `/ai-ide-audit`) reference only `tools.skill_app.*` entry points
- [ ] Every M5 commit ≤200 LOC per `git diff --stat`
- [ ] Full pytest at baseline pass count (no regressions)
- [ ] Re-export shims deleted or documented as deferred

## Self-Report
[EMPTY -- populated by Phase 4]
