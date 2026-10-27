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

## F1 · BLOCKER · open
**Where:** src/guards/checkpoint.ts:319
**Critic (r1):** The Bash guard exempts the entire command when it starts with `git`, so a git-prefixed compound command can still run `cp` (or redirection) into a checkpoint JSON and bypass G7. Remove the blanket exemption; only allow a single known read-only git command or reject write-capable segments, with a compound-command regression test.

## F2 · MAJOR · open
**Where:** src/install.ts:47
**Critic (r1):** The unanchored `checkpoint-gate.py` alternative marks any hook command mentioning that filename as managed; update then drops the whole array entry, including user-added commands in a wrapper. Recognize only the exact standalone legacy hook and preserve or refuse ambiguous combined entries; test a wrapped legacy hook with a user command.
