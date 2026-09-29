# ai-git-cleanup-v3 #3 — adversarial review thread

## Goal (checkpoint 3)
The run ends with the per-branch report proven end to end, references/merge-evidence.md is removed with attribution preserved in NOTICE, CHANGELOG and the changeset carry the v3 entry, assets are regenerated, and the full suite is green at the new baseline.

## Acceptance
- Report proven end to end (U22: exact rows, bucket↔row linkage, stashState ⟺ migration.stash); forbidden-command sweep (U23) green.
- references/merge-evidence.md gone with zero dangling refs (skills.spec G7 + rg); attribution preserved (NOTICE/THIRD-PARTY name Trail of Bits + URL + CC BY-SA 4.0 + retained files; SKILL.md Source line intact).
- CHANGELOG Unreleased unmistakable `ai-git-cleanup v3` line; changeset single minor; assets regenerated without the removed reference.
- Full suite green at the new baseline: 928/928.

## changed_files
- skills/ai-git-cleanup/references/merge-evidence.md (DELETED, dir removed)
- NOTICE.md, THIRD-PARTY-NOTICES.md (rows narrowed to retained files)
- CHANGELOG.md (v3 line added), .changeset/ai-git-cleanup.md (amended)
- src/assets.ts (regenerated, reference entries gone)
- tests/git-cleanup-flow.spec.ts (U22 + U23 added by test writer; TS2538 fix by test writer)

## Verify commands
- bun test tests/git-cleanup-flow.spec.ts (7)
- bun test tests/git-cleanup-analyze.spec.ts (32)
- bun test tests/git-cleanup-cli.spec.ts (19)
- bun test tests/skills.spec.ts (19)
- bun test tests/workflow-handoff.spec.ts (2)
- bun test tests/arch.spec.ts (22)
- bun test tests/embed-canon.spec.ts (13)
- rg -q 'ai-git-cleanup' CHANGELOG.md
- test ! -f skills/ai-git-cleanup/references/merge-evidence.md
- bun run typecheck / bun run lint
- bun test (full) — 928/928

## Known context
- Gate 1 PASS incl. report spot-check (4 rows exact, every branch once, stashState both directions) and docs spot-check (attribution + v3 line + changeset).
- U23's documented ceiling: a forbidden command appended to a negated-same-line would pass (SKILL.md quotes forbidden commands in safety prose; allowance is deliberate).
- cp1/cp2 threads: -1.md (choke-point guard, L20), -2.md (PASS, minor pick-semantics note).
- MINOR from cp2 deferred: SKILL.md:159 pick semantics undefined (safe-direction failure).

## Round 1 — critic (VERDICT: PASS)

- F1 | minor | tests/git-cleanup-flow.spec.ts:541 | U22 toEqual brittle to benign field additions | ACCEPTED: R2-compliant — a new key fails cleanly naming itself; correct behavior, not a defect
- F2 | minor | tests/git-cleanup-flow.spec.ts:602 | negated-line heuristic skips lines that name AND prohibit a command | ACCEPTED: that IS the safety prose; non-vacuity probe at :642-643 proves un-negated commands are caught; documented ceiling
- F3 | minor | CHANGELOG.md:11 | 781-char v3 line might hide a truncated sentence | NOT A DEFECT: tail verified — line terminates "…are gone."

Attacks that did not land: no dangling merge-evidence reference (rg only hits CHANGELOG historical text); "named evidence" backed by analyze.mjs fields not the file; NOTICE/THIRD-PARTY/Source sufficient under CC BY-SA §4(a); U23 scans scripts/ recursively, literal full-match, case/double-space covered, dynamic construction caught by emitted-command scan; assets clean; zero test imports of deleted file; cross-file refs zero (G7 covers same-dir only); 928/928 confirmed, no flakiness observed.

Loop result: PASS in 1 round, no fixer. All minors accepted as by-design.
