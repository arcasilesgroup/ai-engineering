# Review thread · floating-core #5 · Port the checkpoint gate to a TypeScript guard in the chain

## Goal
`src/guards/checkpoint.ts` enforces rules G1-G8 inside the chain for Write, Edit, Task/Agent, Bash and Stop, every case of `tests/test_checkpoint_gate.py` is ported as a table, plans are accepted outside a managed worktree, and no carrier calls `python3`.

## Acceptance
- Every rule G1-G8 has passing and denying cases, ported from the Python suite.
- S3: a first plan written in a normal checkout (no managed worktree) is accepted.
- S4: the ui gate and ui stage marker are accepted outside a worktree.
- S13: in an ungoverned repo the guard does nothing and writes nothing.
- No carrier template calls `python3`; `ai-eng update` replaces an old Python gate entry.
- The ceremony contract test stays green.

## changed_files
- tests/adversarial/governance-gate.test.ts
- tests/chain-dispatch.spec.ts
- tests/carriers-install.spec.ts
- tests/workflow-doctor-surfaces.spec.ts
- tests/checkpoint-gate-carrier.spec.ts
- tests/ceremony-contract.spec.ts
- tests/checkpoint-guard.spec.ts
- tests/chain-dialect.spec.ts
- FILEMAP.md
- scripts/checkpoint-gate.py
- scripts/gen-assets.ts
- skills/.chain-bundle/ai-eng-chain.ts
- skills/ai-orchestrator/SKILL.md
- src/assets.ts
- src/chain/mod.ts
- src/commands/checkpoint-gate-report.ts
- src/embed.ts
- src/install.ts
- src/surfaces/surfaces.json
- src/workflow/checkpoint.ts
- src/guards/checkpoint.ts
- templates/plugin.omp.ts.tpl
- templates/plugin.opencode.ts.tpl
- templates/plugin.pi.ts.tpl
- templates/settings.claude.json.tpl
- templates/settings.codex.json.tpl
- templates/settings.copilot.cli.json.tpl
- templates/settings.copilot.json.tpl
- templates/settings.cursor.json.tpl
- tests/arch.spec.ts
- tests/test_checkpoint_gate.py
- .github/hooks/ai-eng.json
- LEARNINGS.md

## Verify
- `bun test tests/chain-dialect.spec.ts`
- `bun test tests/checkpoint-guard.spec.ts`
- `bun test tests/carriers-install.spec.ts`
- `bun test tests/checkpoint-gate-carrier.spec.ts`
- `bun test tests/workflow-doctor-surfaces.spec.ts`
- `bun test tests/chain-dispatch.spec.ts`
- `bun test tests/adversarial/governance-gate.test.ts`
- `bun test tests/ceremony-contract.spec.ts`
- `bun test tests/generated-payload.test.ts`
- `sh -c '! grep -l python3 templates/settings.*.tpl templates/plugin.*.tpl'`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`

## F1 · BLOCKER · fixed
**Where:** src/guards/checkpoint.ts:319
**Critic (r1):** The Bash guard exempts the entire command when it starts with `git`, so a git-prefixed compound command can still run `cp` (or redirection) into a checkpoint JSON and bypass G7. Remove the blanket exemption; only allow a single known read-only git command or reject write-capable segments, with a compound-command regression test.

**ROOT CAUSE:** `checkBash` skipped its write-pattern decision for every command beginning with `git`, including compounds that also contained a write to the checkpoint path.
**FIX:** Removed the blanket Git-prefix exemption; added compound `git status` plus `cp`/redirection denials while keeping `git add` and read-only `git status` allowed.
**LESSON:** Inspect the complete compound command for writes to governed paths; a safe-looking first command does not make later segments safe.
**Fixer (r1):** fixed — the Bash guard now checks write-capable patterns across Git-prefixed compounds, `src/guards/checkpoint.ts` · verify: `bun test tests/checkpoint-guard.spec.ts tests/carriers-install.spec.ts tests/checkpoint-gate-carrier.spec.ts` ✓

## F2 · MAJOR · fixed
**Where:** src/install.ts:47
**Critic (r1):** The unanchored `checkpoint-gate.py` alternative marks any hook command mentioning that filename as managed; update then drops the whole array entry, including user-added commands in a wrapper. Recognize only the exact standalone legacy hook and preserve or refuse ambiguous combined entries; test a wrapped legacy hook with a user command.

**ROOT CAUSE:** `MARKER` matched the legacy script filename anywhere in a hook string, so a user wrapper mentioning that path was classified as ours and removed.
**FIX:** Replaced the filename substring with a full-string match for the standalone legacy Python hook; added a regression proving a wrapped user command is preserved while the standalone managed hook is retired.
**LESSON:** Migration ownership must match the complete managed command shape, not a filename substring that user commands can also contain.
**Fixer (r1):** fixed — legacy removal now requires the exact standalone invocation, `src/install.ts` · verify: `bun test tests/checkpoint-guard.spec.ts tests/carriers-install.spec.ts tests/checkpoint-gate-carrier.spec.ts` ✓

## Replanned CP5 review scope

Automatic replan split the old CP5 into CP5 (guard and chain behavior) and CP6 (carrier/Python retirement). The previous F1/F2 fixes remain in the shared code history; this review attempt covers only the CP5 slice below.

### Goal
`src/guards/checkpoint.ts` enforces G1-G8 for Write, Edit, Task/Agent, Bash and Stop; chain routing and verdict dialects are correct; normal checkouts and ungoverned repos retain the approved behavior.

### Acceptance
- Every rule G1-G8 has passing and denying cases, including no-lifecycle denial.
- G6 uses the detected base.
- S3/S4 work outside managed worktrees.
- S13 does nothing and writes no receipt in an ungoverned repo.
- Chain routes supported tools and Stop with each harness's verdict dialect.
- Outside the three triggers, the guard allows without reading the plan.

### changed_files
- tests/checkpoint-guard.spec.ts
- src/guards/checkpoint.ts
- src/chain/mod.ts
- src/chain/dialect.ts
- src/workflow/checkpoint.ts
- tests/chain-dispatch.spec.ts
- tests/chain-dialect.spec.ts
- tests/adversarial/governance-gate.test.ts
- tests/arch.spec.ts
- skills/.chain-bundle/ai-eng-chain.ts
- FILEMAP.md
- LEARNINGS.md

### Verify
- `bun test tests/chain-dialect.spec.ts`
- `bun test tests/checkpoint-guard.spec.ts`
- `bun test tests/chain-dispatch.spec.ts`
- `bun test tests/adversarial/governance-gate.test.ts`
- `bun test tests/generated-payload.test.ts`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`
