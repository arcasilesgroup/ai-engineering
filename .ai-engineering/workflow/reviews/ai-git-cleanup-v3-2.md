# ai-git-cleanup-v3 #2 — adversarial review thread

## Goal (checkpoint 2)
SKILL.md runs phases 0-3 in order — automatic safe migration, deterministic classification, ONE ask per delete batch (the only confirmation), execute and report — supports `--sync`/`--branches`/`--all`, drops `disable-model-invocation` for a trigger-rich description, states the rewritten safety invariants, and the structure gates stay green with the flow spec proving the ordering.

## Acceptance
- Phase order: automatic reversible migration (stash/switch/pinned ff-only pull/pop with WARN paths) → read-only analyze → ONE ask per batch → execute (worktrees first, guards, prune-if-removed) then per-branch report.
- Flags --sync/--branches/--all documented; frontmatter trigger-rich, disable-model-invocation gone; Lifecycle + Trail of Bits Source line kept; skills.spec green.
- Safety invariants rewritten and true: 1-ask floor, choke-point protection, evidence, quoting, guard before every -d, pinned sync target, dirty refusal, fail-closed, main-session-only, no push/gc/CI/remote.
- Plus the `+`-marker parser fix (worktree-held merged → MERGED/-d/worktreePath) with exact-config test.

## changed_files
- skills/ai-git-cleanup/SKILL.md (full four-phase rewrite + frontmatter)
- skills/ai-git-cleanup/scripts/analyze.mjs (/^[*+]/ marker strip)
- tests/git-cleanup-analyze.spec.ts (+1 worktree-held-merged case → 32)
- tests/git-cleanup-flow.spec.ts (reworked 3→5 by test writer; TS narrowing fix by test writer)
- src/assets.ts (regenerated, byte-unchanged)

## Verify commands
- bun test tests/git-cleanup-flow.spec.ts (5)
- bun test tests/git-cleanup-analyze.spec.ts (32)
- bun test tests/git-cleanup-cli.spec.ts (19)
- bun test tests/skills.spec.ts (19)
- bun test tests/workflow-handoff.spec.ts (2)
- bun test tests/arch.spec.ts (22)
- bun test tests/embed-canon.spec.ts (13)
- bun run typecheck
- bun run lint

## Known context
- Gate 1 PASS incl. spot-checks: worktree-held merged branch → batched MERGED/-d/guard/worktreePath; dirtied → keep WORKTREE_HELD + requiresAcknowledgment, never batched. SKILL.md greps: no disable-model-invocation, flags documented, hard-floor sentence present, all push mentions are prohibitions.
- Orchestrator deviations logged in plan assumptions: U20/U21 source-text cases dropped (R1); `+`-parser bug folded into cp2.
- cp1 thread: ai-git-cleanup-v3-1.md (PASS after choke-point guard fix, L20).
- Design decisions (fixed): scope git-only; name kept; auto + exactly ONE batch confirmation; migration/sync run WITHOUT asking (reversible by design); phase-0 pull failure = WARN + continue.

## Round 1 — critic (VERDICT: PASS)

- F1 | minor | SKILL.md:159 | "pick" semantics undefined — how subsets are selected / empty batch / whether it becomes a second prompt; the one-ask floor leaves the pick path unconstrained | failure mode is floor-violation in the SAFE direction (extra ask) or a numbered menu as THE one ask; not a data-loss path

Attacks that did not land: trigger surface (git-contextual, orchestrator-applied, accepted design), stash-pop conflict (stash kept, tested), switch-fail-after-stash (stop instruction exists), already-on-default (no-op), detached HEAD ('' never matches guard), worktree switch block, flag partitioning (wantsMigration/wantsClassification), no-push scan, choke-point (analyze.mjs:207, tested), parser fix scope (only branch --merged parses markers), L19 self-proving fixtures.

Loop result: PASS in 1 round, no fixer. F1 → deferred MINOR note for app review.
