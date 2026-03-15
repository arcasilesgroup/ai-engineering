# Done — Spec 051: Architecture v3

## Summary

Clean-sheet architecture redesign: 7→10 agents, 35→40 skills, self-improvement mechanism, guard integration, feature gap reviewer. Applied SOLID, DRY, Anthropic skill-creator pattern.

## Delivered

| Deliverable | Status |
|-------------|--------|
| 3 new agents (guard, guide, operate) | DONE — 159, 146, 156 lines |
| 7 new skills (guard, dispatch, guide, onboard, evolve, ops, lifecycle) | DONE — 1037 lines total |
| 5 stub skills expanded to full procedures | DONE — security 216L, quality 175L, governance 153L, build 257L, perf 150L |
| 2 agent renames (scan→verify, release→ship) | DONE — all cross-refs updated |
| 11 skill renames (self-documenting names) | DONE — all cross-refs updated |
| create+delete merged into lifecycle | DONE — 93 lines |
| explain reassigned to guide agent | DONE — guide references it, plan removed ref |
| 5 runbooks assigned owner: operate (consolidated from 13) | DONE |
| guard.advise in build post-edit validation | DONE — Step 2 in build agent |
| verify.gap --framework self-audit mode | DONE — added to gap skill + verify modes |
| evolve skill (self-improvement) | DONE — 12 analysis rules, report template |
| dispatch skill (formal task schema) | DONE — YAML schema + DAG construction |
| agent-model governance standard | DONE — 66 lines |
| framework-contract.md rewritten | DONE — 10 agents, guard.gate, evolve loop |
| product-contract.md rewritten | DONE — v0.3.0, updated tables + roadmap |
| manifest.yml updated | DONE — 10 agents, 40 skills |
| CHANGELOG.md updated | DONE — v0.3.0 entry |
| .ai-engineering/README.md created | DONE — developer guide |
| Claude Code commands (44 files) | DONE — 13 renamed, 7 created, 1 deleted |
| Template mirror synced | DONE — 10 agents, 40 skills, 5 runbooks |
| Python source updated (6 files) | DONE — audit.py, governance_cmd, sync_mirrors, 3 tests |
| All tests pass | DONE — 1463 pass, 0 fail |

## Metrics

| Metric | Before | After |
|--------|--------|-------|
| Agents | 7 | 10 |
| Skills | 35 | 40 |
| Stub skills | 5 | 0 |
| Orphan skills | 1 (explain) | 0 |
| Runbook owners | 0 | 5 |
| Tests | 1463 pass | 1463 pass |
| Commits | — | 14 |
| Lines added | — | ~6,700 |

## Gap Register (Aspirational Features)

Features that are documented but NOT yet implemented. Each tracked with a future spec.

| # | Gap | Why Aspirational | Impact | Future Spec |
|---|-----|-----------------|--------|-------------|
| GAP-01 | Programmatic agent dispatch | execute agent is a behavioral contract — no Python orchestrator code exists. Dispatch is manual (human invokes agents). | Medium — framework works fine with manual dispatch | spec-052 |
| GAP-02 | Guide growth tracking | guide.teach and guide.onboard work, but tracking learning progress across sessions requires telemetry infrastructure not yet built. | Low — core teaching works | spec-054 |
| GAP-03 | Operate scheduled execution | operate.run works (AI reads runbook + follows instructions), but scheduled cron-based execution requires external infrastructure (GitHub Actions, Foundry). | Medium — manual execution works | spec-055 |
| GAP-04 | Observe predict mode | observe dashboards work, but forecasting future health trends requires rule-based extrapolation not yet implemented. | Low — dashboards provide current state | spec-056 |
| GAP-05 | Multi-IDE verification | Claude Code adapters tested and working. Copilot prompts and Gemini adapters exist but NOT verified with actual IDEs. | Medium — only Claude Code confirmed | spec-057 |
| GAP-06 | GOVERNANCE_SOURCE.md rewrite | Canonical governance source needs update for 10 agents / 40 skills. Currently stale. | Medium — IDE adapters generated from source | spec-058 |
| GAP-07 | .github/prompts + .github/agents rename | Copilot prompt files and agent files still use old names. Need rename to match new skill/agent names. | Low — only affects Copilot users | spec-058 |
| GAP-08 | Root README.md architecture section | Root README has CHANGELOG entry but needs full architecture overview with 10-agent diagram. | Low — .ai-engineering/README.md is complete | spec-058 |
| GAP-09 | Standards directory flatten | Plan proposed moving standards/framework/* → standards/* for DRY. Descoped — too many cross-references to update for marginal benefit. | Very Low — current structure works | deferred |
| GAP-10 | ai-eng validate counter check | Validator may flag skill/agent counter mismatches until GOVERNANCE_SOURCE and instruction files are fully synced. | Low — validate is advisory | spec-058 |

## Decisions

| ID | Decision | Rationale |
|----|----------|-----------|
| implicit | Keep agent names as single-word verbs | Convention: plan, execute, guard, build, verify, ship, observe, guide, write, operate |
| implicit | guard.advise as post-edit step (not parallel IDE feature) | Simple, efficient, practical — works TODAY without IDE integration |
| implicit | evolve as READ-ONLY analysis skill | Security: AI proposes, humans approve. No autonomous framework modification. |
| implicit | Standards flatten DESCOPED | Too many refs (50+) for marginal benefit. Current standards/framework/ path works. |
| implicit | Copilot/Gemini adapter rename DEFERRED | Only Claude Code is verified. Other IDEs are aspirational. |
