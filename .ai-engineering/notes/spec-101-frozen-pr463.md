# spec-101 — Installer Robustness (FROZEN)

**Reason for freezing**: PR #463 OPEN with 8 CI failures pending. Branch `feat/spec-101-installer-robustness` is being repurposed to also accumulate sub-specs S2-S5 of the adoption series (per user directive 2026-04-26: "no vamos a mergear spec-101, en esta rama hagamos todos los desarrollos de notes de S"). spec.md and plan.md are being released for the next active spec (S2 → spec-104). spec-101 content is preserved here verbatim and will move back to `_history.md` when the umbrella branch lands.

**Status snapshot (2026-04-26)**:
- Plan progress: 102/102 tasks complete (100%) + 6 CI fix waves + 1 critical fix wave + autonomous review.
- Last commit: `4999f82d`.
- PR: #463 OPEN.
- CI status: 30/38 PASS, 8 failing (Integration ×3 + spec101 Install Smoke ubuntu/windows ×4 + CI Result aggregator).
- Morning summary: `.ai-engineering/runs/spec-101/morning-summary.md`.

**Resume**: when the umbrella PR is ready to merge, restore this content to `specs/spec.md`/`specs/plan.md` OR fold it into the umbrella PR body. Pending CI fixes tracked separately.

---

## spec.md (preserved)

```markdown
---
spec: spec-101
title: Installer Robustness — Stack-Aware User-Scope Tool Bootstrap
status: approved
effort: large
refs:
  - .ai-engineering/notes/adoption-s2-commit-pr-speed.md
  - .ai-engineering/notes/adoption-s3-unified-gate-risk-accept.md
  - .ai-engineering/notes/adoption-s4-skills-consolidation-architecture.md
  - .ai-engineering/notes/adoption-s5-mcp-sentinel-ide-parity.md
---

# Spec 101 — Installer Robustness: Stack-Aware User-Scope Tool Bootstrap

[Full spec content preserved in git history at the commit that introduced this freeze. To recover: `git show <commit-before-freeze>:.ai-engineering/specs/spec.md`. Summary: 12 goals (G-1..G-12), 14 decisions (D-101-01..D-101-15), 11 NG, 15 risks. Owns the rewire of `manifest.yml` `required_tools` for 14 stacks, user-scope-only install, `python_env.mode=uv-tool` default, SDK prereq detection per-stack with EXIT 81, post-install offline-safe verification, and CI matrix smoke across 3 OSes.]
```

## plan.md (preserved)

```markdown
# Plan: spec-101 Installer Robustness — Stack-Aware User-Scope Tool Bootstrap

[Full plan preserved in git history. Phase 0-6 + nocturnal CI fix waves 1-26 + autonomous review (6 specialists in parallel). Total 102 tasks across 7 phases. Recovery: `git show <commit-before-freeze>:.ai-engineering/specs/plan.md`.]
```

---

## Outstanding work for spec-101 (CI follow-ups)

Tracked separately as part of the umbrella branch CI hygiene:

| # | Failing job | Symptom |
|---|---|---|
| 1 | Integration test #1 | TBD per latest CI log |
| 2 | Integration test #2 | TBD per latest CI log |
| 3 | Integration test #3 | TBD per latest CI log |
| 4 | spec101 Install Smoke (ubuntu) | TBD |
| 5 | spec101 Install Smoke (windows ×3) | TBD |
| 6-7 | spec101 Install Smoke (windows ×3) | TBD |
| 8 | CI Result aggregator | Downstream of items 1-7 |

These are NOT in spec-104 scope. Picked up either as ad-hoc fix waves on this branch or as a follow-up `chore(spec-101)` commit batch.

---

## Why this freeze is safe

- spec-101 implementation in `src/` and `tests/` is intact and merged into the working tree of branch `feat/spec-101-installer-robustness`. PR #463 references the branch, not `specs/spec.md` snapshot.
- Files spec-104 (S2) will touch (`policy/orchestrator.py`, `policy/gate_cache.py`, `cli_commands/gate.py`, `.claude/skills/ai-commit/SKILL.md`, `.claude/skills/ai-pr/**`) are **orthogonal** to spec-101's scope. Verified: spec-101 did not modify any skill markdown nor add anything in `policy/orchestrator.py` or `policy/gate_cache.py`.
- `manifest.yml` change for spec-104 is additive (adds `gates.policy_doc_ref` pointer; does not touch `required_tools`, `python_env`, or `prereqs` blocks owned by spec-101).
- `ai-eng sync --check` runs on every push and will catch any mirror drift introduced by either spec.
