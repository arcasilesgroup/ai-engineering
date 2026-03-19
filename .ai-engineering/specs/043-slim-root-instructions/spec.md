---
id: "043"
slug: "slim-root-instructions"
status: "in-progress"
created: "2026-03-09"
size: "M"
tags: ["governance", "token-efficiency", "deduplication", "progressive-disclosure"]
branch: "feat/043-slim-root-instructions"
pipeline: "standard"
decisions: []
---

# Spec 043 — Slim Root Instructions: Deduplicate CLAUDE.md / AGENTS.md / copilot-instructions.md

## Problem

Root instruction files (`CLAUDE.md`, `AGENTS.md`, `.github/copilot-instructions.md`) duplicate ~70% of their content with each other and with `context/product/framework-contract.md`. Meanwhile, `product-contract.md` — which contains unique, valuable context (roadmap, KPIs, architecture, blockers) — is never loaded by any agent or session.

Current state:
- Session Start Protocol appears 3× (CLAUDE, AGENTS, copilot)
- Skills/Agents tables appear 3×
- Command Contract appears 3×
- Quality/Security thresholds appear in 5 files
- `framework-contract.md` is ~80% redundant with CLAUDE.md + AGENTS.md combined
- `product-contract.md` has unique context that no agent ever reads
- Every new skill/agent requires manual updates to 3+ files
- Total token waste: ~2,100 tokens of duplicated content loaded every Claude session

## Solution

Slim the root instruction files to contain only:
1. Platform-specific behavior (unique per provider)
2. Pointers to canonical sources (`framework-contract.md`, `product-contract.md`)
3. Session start protocol (kept — auto-injected, cheap)

Consolidate duplicated content into the contracts, which become the single source of truth. Add on-demand loading directives so agents read contracts when they need governance or product context.

## Scope

### In Scope

- Slim `CLAUDE.md`: remove duplicated tables, keep prohibitions + session start + pointers
- Slim `AGENTS.md`: remove duplicated tables, keep agent behavior mandates + pointers
- Slim `.github/copilot-instructions.md`: remove duplicated tables, keep spec-as-gate variant + pointers
- Ensure `framework-contract.md` is the canonical source for: ownership, lifecycle, pipeline strategy, quality/security thresholds, command contract
- Ensure `product-contract.md` is the canonical source for: skills/agents tables, CLI commands, roadmap, KPIs, architecture
- Add on-demand loading directives to skills that need product context (plan, spec, pr)
- Update `manifest.yml` start_sequence commentary if needed

### Out of Scope

- Changing the progressive disclosure mechanism itself
- Adding contracts to the automatic `start_sequence`
- Modifying the contracts' content (only ensuring they are the source of truth)
- Template mirror updates (will be handled by `ai-eng validate` after merge)

## Acceptance Criteria

1. CLAUDE.md is ≤ 60 lines (from 140 currently)
2. AGENTS.md is ≤ 70 lines (from 146 currently)
3. copilot-instructions.md is ≤ 40 lines (from 75 currently)
4. No content is lost — all information exists in exactly one canonical location
5. `ai-eng validate` passes after changes (no broken references)
6. Skills that need product context (plan, spec, pr) have explicit "read contract" directives
7. Zero duplicated tables across root files

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| D1 | Keep Session Start Protocol in all 3 root files | Auto-injected per platform, low cost (~50 tok each), critical for session correctness |
| D2 | Keep Absolute Prohibitions in CLAUDE.md only | Claude-specific enforcement, AGENTS.md has its own Non-Negotiables section |
| D3 | Move skills/agents tables to product-contract.md only | Already there (§2.2, §7.4), remove from root files |
| D4 | Move command contract to framework-contract.md | Operational rules belong in the framework contract |
| D5 | Move pipeline strategy to framework-contract.md | Already partially there, consolidate |
| D6 | On-demand loading over auto-loading | Respect progressive disclosure budget, avoid +7,000 tok/session |
