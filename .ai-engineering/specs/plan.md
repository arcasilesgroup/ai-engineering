# Plan: Copilot Subagent Orchestration — Full Parity with Claude Code

## Pipeline: standard
## Phases: 5
## Tasks: 17 (build: 13, verify: 3, conditional: 1)

---

### Phase 1: Sync Pipeline Infrastructure
**Gate**: `AgentMeta` extended, `AGENT_METADATA` updated, `generate_copilot_agent()` serializes new properties. `ruff check scripts/` passes.

- [x] T-1.1: Extend `AgentMeta` dataclass with `copilot_agents`, `copilot_handoffs`, `copilot_hooks` fields (agent: build)
  - File: `scripts/sync_command_mirrors.py` lines 63-72
  - Add 3 optional fields with defaults (empty tuple, empty tuple, None)
  - Constraint: frozen dataclass — use default_factory pattern or direct defaults

- [x] T-1.2: Update `AGENT_METADATA` dict with subagent config for 5 orchestrators (agent: build)
  - File: `scripts/sync_command_mirrors.py` lines 76-236
  - Add `copilot_agents` to: autopilot, build, plan, review, verify
  - Add `copilot_handoffs` to: autopilot, build, plan, review
  - Add `copilot_hooks` to: build only
  - 4 leaf agents (explore, guard, guide, simplify) keep empty defaults
  - Note: autopilot handoff uses `agent: "agent"` (intentional — targets the built-in default Copilot chat agent for PR creation, returning control to user)

- [x] T-1.3: Update `generate_copilot_agent()` to serialize new frontmatter properties (agent: build)
  - File: `scripts/sync_command_mirrors.py` lines 584-600
  - Inject `agent` into tools list when `copilot_agents` is non-empty
  - Serialize `agents: [...]` when non-empty
  - Serialize `handoffs:` block (list of dicts) when non-empty
  - Serialize `hooks:` block (nested dict) when non-empty
  - Use `_format_yaml_field()` (line 352) for dict/list serialization
  - Constraint: DO NOT modify `_serialize_frontmatter()` — it's for skills, not agents

- [x] T-1.4: Lint and type-check sync script changes (agent: build)
  - Run: `ruff check scripts/sync_command_mirrors.py`
  - Run: `ruff format --check scripts/sync_command_mirrors.py`
  - Fix any issues before proceeding

### Phase 2: Canonical Agent Body Updates
**Gate**: All `Dispatch Agent(X)` replaced with "Use the X agent" syntax. Autopilot has "Subagent Orchestration" section. Build references Guard/Explorer as subagents. No `.claude/` contains Copilot-only properties.

- [x] T-2.1: Add "Subagent Orchestration" section to autopilot canonical (agent: build)
  - File: `.claude/agents/ai-autopilot.md`
  - Add new section after "Capabilities" (after line 26)
  - Content per spec R4: 5-point delegation protocol

- [x] T-2.2: Replace all `Dispatch Agent(X)` references in autopilot AND build canonicals (agent: build)
  - File: `.claude/agents/ai-autopilot.md` — 8 occurrences at lines: 23, 24, 25, 42, 43, 53, 55, 68
  - File: `.claude/agents/ai-build.md` — scan for ANY `Dispatch Agent(` occurrences beyond lines 65-87
  - Replace with "Use the X agent to..." pattern
  - Constraint: preserve meaning and context of each reference

- [x] T-2.3: Update Build canonical — guard.advise and dispatch pattern (agent: build)
  - File: `.claude/agents/ai-build.md`
  - Line 65-66: Replace `guard.advise` with Guard agent subagent reference
  - Lines 81-87: Add Explorer as consultable subagent in dispatch pattern

- [x] T-2.4: Investigate and fix autopilot skill path bug (agent: build)
  - File: `.claude/skills/ai-autopilot/SKILL.md`
  - Investigation found: line 83 mentions "watch-and-fix loop" — verify if there's a handler reference that the `translate_refs()` regex misses
  - Check all `.claude/` path references in the skill that the regex `_XREF_CLAUDE_SKILL` might not match (e.g., handler paths not rooted at the skill's SKILL.md)
  - Fix any path references that won't translate correctly via sync

- [x] T-2.5: Update dispatch skill canonical with agent name references (agent: build)
  - File: `.claude/skills/ai-dispatch/SKILL.md`
  - Replace any generic "subagent" references with explicit agent names where appropriate
  - Ensure names used will be translated by `translate_refs()` for each platform

### Phase 3: Sync, Regenerate, and Validate
**Gate**: `ai-eng sync --check` passes (exit 0). Generated mirrors have correct frontmatter. Validator doesn't flag false drift.

- [x] T-3.1: Run sync to regenerate all mirrors (agent: build)
  - Run: `python scripts/sync_command_mirrors.py --verbose`
  - Verify output: 9 agents × 3 surfaces + 37 skills × 3 surfaces regenerated
  - Check generated `.github/agents/autopilot.agent.md` — must have `agents`, `handoffs`, `agent` in tools
  - Check generated `.github/agents/build.agent.md` — must have `agents`, `handoffs`, `hooks`, `agent` in tools

- [x] T-3.2: Run sync check to verify parity (agent: verify)
  - Run: `ai-eng sync --check` or `python scripts/sync_command_mirrors.py --check`
  - Must exit 0 (no drift)
  - If fails: the mirror_sync validator may need updating (T-3.3)

- [x] T-3.3: Update mirror_sync validator if needed (agent: build) — NOT NEEDED (sync passes)
  - File: `src/ai_engineering/validator/categories/mirror_sync.py`
  - ONLY if T-3.2 fails due to Copilot-only properties
  - The validator uses full-file SHA-256 comparison (line 315)
  - Since sync script GENERATES the mirrors, the hashes should match after regeneration
  - If validator compares canonical `.claude/` vs `.github/` directly (not via sync), it will fail — adjust comparison logic
  - Blocked by: T-3.2 (only execute if T-3.2 fails)

### Phase 4: Documentation and Governance
**Gate**: `docs/copilot-subagents.md` exists with 3 environment examples. `copilot-instructions.md` has subagent section. DEC-024 registered.

- [x] T-4.1: Create `docs/copilot-subagents.md` (agent: build)
  - New file: `docs/copilot-subagents.md`
  - Must include:
    - Sync architecture explanation (canonical → mirrors)
    - Copilot-specific properties (`agents`, `handoffs`, `hooks`)
    - VS Code usage example (agent tool + agents property)
    - Copilot CLI usage example (task tool with agent_type)
    - Coding Agent usage example (auto-discovery from repo)
    - Capabilities matrix by environment
    - Handoff chain diagram
    - Reference to official docs + returngis article

- [x] T-4.2: Add "Subagent Orchestration" section to copilot-instructions.md (agent: build)
  - File: `.github/copilot-instructions.md`
  - Add section after "Observability" (after line 51)
  - Document: orchestrator agents, subagent tool, handoffs, and roles

- [x] T-4.3: Register DEC-024 in decision-store.json (agent: build)
  - File: `.ai-engineering/state/decision-store.json`
  - ID: DEC-024
  - Title: "Copilot subagent orchestration via sync pipeline"
  - Status: active, Criticality: high
  - Record rationale: platform-specific properties injected via AGENT_METADATA

### Phase 5: Final Verification
**Gate**: All 20 acceptance criteria pass. Linters clean. No regressions.

- [x] T-5.1: Run full linter suite (agent: verify)
  - `ruff check src/ scripts/`
  - `ruff format --check src/ scripts/`
  - `gitleaks detect`
  - All must pass

- [x] T-5.2: Verify all 20 acceptance criteria (agent: verify) — 20/20 PASS
  - Check AC 1-3: sync pipeline (AgentMeta, AGENT_METADATA, generate function)
  - Check AC 4-8: generated mirrors (frontmatter properties, sync --check)
  - Check AC 9-12: canonical body changes (sections, syntax, path fix)
  - Check AC 13-16: docs and governance (files exist, DEC-024, validator)
  - Check AC 17-20: negative checks (leaf agents clean, no Copilot props in canonical, linters)

---

## Agent Assignments Summary

| Agent | Tasks | Purpose |
|-------|-------|---------|
| build | 13 | Sync script changes, canonical body updates, docs, governance |
| verify | 3 | Sync check, lint suite, AC verification |

## Dependencies

```
T-1.1 → T-1.2 → T-1.3 → T-1.4
                              ↘
T-2.1 ──┐                     T-3.1 → T-3.2 → T-3.3 (conditional)
T-2.2 ──┤ (parallel)                              ↓
T-2.3 ──┤                     T-4.1 ──┐
T-2.4 ──┤                     T-4.2 ──┤ (parallel, after Phase 3)
T-2.5 ──┘                     T-4.3 ──┘
                                       ↓
                               T-5.1 → T-5.2
```

Phase 1 and Phase 2 can run in parallel (different files).
Phase 3 requires both Phase 1 and Phase 2 complete.
Phase 4 can start after Phase 3.
Phase 5 runs last.

## Files Modified (Expected)

| File | Phase | Change Type |
|------|-------|-------------|
| `scripts/sync_command_mirrors.py` | 1 | Extend dataclass, metadata, generator |
| `.claude/agents/ai-autopilot.md` | 2 | Add section, unify syntax |
| `.claude/agents/ai-build.md` | 2 | Update guard.advise, add Explorer |
| `.claude/skills/ai-autopilot/SKILL.md` | 2 | Fix path bug |
| `.claude/skills/ai-dispatch/SKILL.md` | 2 | Update agent references |
| `src/ai_engineering/validator/categories/mirror_sync.py` | 3 | Conditional — only if validator fails |
| `docs/copilot-subagents.md` | 4 | New file |
| `.github/copilot-instructions.md` | 4 | Add section |
| `.ai-engineering/state/decision-store.json` | 4 | Add DEC-024 |

## Auto-generated (via sync, NOT manually edited)

| File | Source |
|------|--------|
| `.github/agents/*.agent.md` (9 files) | sync from `.claude/agents/` + `AGENT_METADATA` |
| `.github/prompts/*.prompt.md` (37 files) | sync from `.claude/skills/` |
| `.agents/agents/*.md` (9 files) | sync from `.claude/agents/` |
| `.agents/skills/*/SKILL.md` (37 dirs) | sync from `.claude/skills/` |
