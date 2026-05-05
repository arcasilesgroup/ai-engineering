# Autopilot Manifest: spec-122

## Split Strategy

By-dependency: sub-001 (config hygiene + evals delete) is the no-deps entry
point; sub-002 (Engram + state.db) and sub-003 (OPA proper) depend only on
sub-001 and run in parallel; sub-004 (meta-cleanup) depends on all three
because docs reference final state.

## Source

User-authored sub-specs at `.ai-engineering/specs/spec-122-{a,b,c,d}-*.md`
(all `status: approved`). This manifest is the autopilot orchestration layer;
Phase 2 enriches each `sub-NNN/spec.md` + `plan.md` with codebase exploration
and detailed task breakdown.

## Sub-Specs

| # | Title | Status | Depends On | Source spec | Files (best guess) |
|---|-------|--------|------------|-------------|---------------------|
| sub-001/ | Hygiene + Config + Delete Evals | complete | None | spec-122-a | `CONSTITUTION.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `.semgrep.yml`, `.gitleaks.toml`, `.ai-engineering/manifest.yml`, `.ai-engineering/references/iocs.json`, `.ai-engineering/evals/`, `.ai-engineering/runs/consolidate-2026-04-29/`, `.ai-engineering/schemas/manifest.schema.json`, `.ai-engineering/schemas/skill-frontmatter.schema.json`, `.ai-engineering/specs/spec-117-progress/`, `.ai-engineering/specs/spec-121-self-improvement-and-hook-completion.md`, `.ai-engineering/scripts/wire-memory-hooks.py`, `.ai-engineering/state/instinct-observations.ndjson.repair-backup`, `.ai-engineering/state/strategic-compact.json`, `.ai-engineering/state/spec-116-t31-audit-classification.json`, `.ai-engineering/state/spec-116-t41-audit-findings.json`, `.ai-engineering/state/gate-cache/`, `src/ai_engineering/eval/` |
| sub-002/ | Engram Delegation + Unified state.db | partial | sub-001 | spec-122-b | `.ai-engineering/state/memory.db`, `.ai-engineering/state/state.db` (new), `.ai-engineering/state/decision-store.json`, `.ai-engineering/state/gate-findings.json`, `.ai-engineering/state/ownership-map.json`, `.ai-engineering/state/install-state.json`, `.ai-engineering/state/hooks-manifest.json`, `.ai-engineering/state/framework-events.ndjson`, `.ai-engineering/scripts/memory/`, `src/ai_engineering/state/migrations/` (new), `src/ai_engineering/state/audit_index.py`, `src/ai_engineering/state/audit_chain.py`, `pyproject.toml`, `uv.lock`, `.claude/skills/ai-remember/SKILL.md`, `.claude/skills/ai-dream/SKILL.md`, `scripts/install.sh` |
| sub-003/ | OPA Proper Switch + Governance Wiring | partial | sub-001 | spec-122-c | `.ai-engineering/policies/branch_protection.rego`, `.ai-engineering/policies/commit_conventional.rego`, `.ai-engineering/policies/risk_acceptance_ttl.rego`, `src/ai_engineering/governance/policy_engine.py`, `scripts/install.sh`, `.git/hooks/pre-commit`, `.git/hooks/pre-push`, `.ai-engineering/manifest.yml`, `.claude/skills/ai-risk-accept/SKILL.md`, `tests/integration/governance/test_opa_eval.py` (new) |
| sub-004/ | Meta-Cleanup (Docs + Scripts + Drift) | planned | sub-001, sub-002, sub-003 | spec-122-d | `scripts/sync_command_mirrors.py`, `scripts/sync_mirrors/` (new), `docs/solution-intent.md`, `docs/cli-reference.md`, `docs/anti-patterns.md`, `docs/ci-alpine-smoke.md`, `docs/copilot-subagents.md`, `docs/agentsview-source-contract.md`, `CHANGELOG.md`, `.gitignore`, `CONSTITUTION.md`, `src/ai_engineering/templates/project/CONSTITUTION.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`, `README.md`, `.claude/skills/ai-autopilot/SKILL.md`, `.claude/skills/ai-brainstorm/SKILL.md`, `.claude/skills/ai-mcp-sentinel/SKILL.md`, `.claude/skills/ai-commit/SKILL.md`, `.claude/skills/_shared/`, `.gemini/skills/`, `.codex/skills/`, `.agents/skills/`, `tests/unit/skills/test_spec_path_canonical.py` (new), `tests/unit/hooks/test_canonical_events_count.py` (new), `tests/unit/hooks/test_hot_path_slo.py` (new), `tests/unit/docs/test_skill_references_exist.py` (new) |

## Execution DAG

```
Wave 1: [sub-001]
Wave 2: [sub-002, sub-003]   (parallel)
Wave 3: [sub-004]
```

## Totals

- Sub-specs: 4
- Dependency chain depth: 3 (Wave 1 → Wave 2 → Wave 3)
- Decisions covered: 40 (D-122-01 .. D-122-40 across 4 sub-specs)

## Quality Rounds

(populated by Phase 5)

## Wave Commits

- Wave 1 (sub-001): `7ce3c3ef` — feat(spec-122-a): hygiene + config + delete evals

## Wave 1 Notes

- 17/18 tasks complete in code (T-1.1, T-1.3..T-1.18)
- T-1.2 BLOCKED — workspace-charter stub delete deferred (file-boundary outside frontmatter; 7+ test fixtures + 2 templates need lockstep update). Routed to follow-up.
- ~90 files changed; net -672 LOC
- All pre-commit gates clean (ruff format ✓, gitleaks ✓; ruff lint = pre-existing tech debt, no new issues)

## Branch

Base: `feat/spec-120-observability-modernization`
Working: same (per user directive — no new branch)

## Flags accepted

- `--hitl=off` — no-op (autopilot runs HITL-off by design per DEC-023)
- `--auto-merge=on` — no-op at orchestrator level; merge gated by branch protection + quality convergence
- `--max-iterations=3` — applied at Phase 5 (matches default 3-round quality loop)
