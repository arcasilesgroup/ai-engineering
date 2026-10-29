# Review thread · floating-core #10 · Remove platform code from the runtime and enforce the final layers

## Goal
Dead and platform code is gone (sidecar, circuit breaker, briefing, upgrade, global templateDir, plant-workflow, checkpoint-gate-report, spec), init and update never commit, update never reads the network, wrap keeps the full output locally, and the arch test checks cycles and that every src file has exactly one layer.

## Acceptance
- init and update create no commit and never use `--no-verify`; changes wait for the person.
- update performs no network read.
- wrap keeps the exit code, shows only failures and prints the path of the full local log (D11).
- briefing, upgrade and spec are unknown verbs; sidecar, circuit breaker, plant-workflow and global templateDir code is gone.
- The arch test checks cycles and that every src file has exactly one layer, with the 6.3 rules.

## changed_files
- .ai-engineering/arch.rules.json
- AGENTS.md
- FILEMAP.md
- README.md
- scripts/proof-cli-ux.sh
- scripts/proof-installed-ci.sh
- skills/.chain-bundle/ai-eng-chain.ts
- skills/ai-brainstorm/SKILL.md
- skills/ai-security/SKILL.md
- skills/ai-stress-test/SKILL.md
- src/chain/mod.ts
- src/chain/payload.ts
- src/payload.ts
- src/cli.ts
- src/commands/adapt.ts
- src/commands/briefing.ts
- src/commands/checkpoint-gate-report.ts
- src/commands/doctor.ts
- src/commands/init-shared.ts
- src/commands/init.ts
- src/commands/plant-workflow.ts
- src/commands/update.ts
- src/commands/upgrade.ts
- src/env.ts
- src/floor/index.ts
- src/floor/template.ts
- src/git/run.ts
- src/guards/checkpoint.ts
- src/guards/circuit-breaker.ts
- src/guards/injection.ts
- src/guards/local-rules.ts
- src/guards/loop.ts
- src/guards/no-verify.ts
- src/guards/self-protect.ts
- src/guards/spoken-secret.ts
- src/notice.ts
- src/receipts.ts
- src/shared-verbs.ts
- src/shared-worktree.ts
- src/sidecar/queue.ts
- src/sidecar/shadow.ts
- src/sidecar/sidecar.ts
- src/spec/index.ts
- src/spec/triggers.ts
- src/surfaces/adapters.ts
- src/surfaces/surfaces.json
- src/wrap/index.ts
- templates/AGENTS.md.tpl
- tests/adversarial/carrier-merge.test.ts
- tests/adversarial/isolation.test.ts
- tests/arch.spec.ts
- tests/briefing-command.spec.ts
- tests/carriers-install.spec.ts
- tests/checkpoint-guard.spec.ts
- tests/circuit-breaker.spec.ts
- tests/init-command.spec.ts
- tests/injection-loop.spec.ts
- tests/local-rules.spec.ts
- tests/no-verify.spec.ts
- tests/payload-dialect.spec.ts
- tests/plant-workflow.spec.ts
- tests/shadow-eval.spec.ts
- tests/sidecar.spec.ts
- tests/skills.spec.ts
- tests/spec-command.spec.ts
- tests/spec-lifecycle.test.ts
- tests/uninstall-command.spec.ts
- tests/update-command.spec.ts
- tests/workflow-doctor-surfaces.spec.ts
- tests/test-hygiene.spec.ts
- tests/wrap.test.ts
- tests/cli-ux.test.ts
- tests/doctor-command.spec.ts
- tests/receipts-summary.spec.ts

## Verify
- `sh -c '! grep -rnE "ai-eng (spec|briefing|upgrade)([^a-z-]|$)" skills scripts AGENTS.md templates/AGENTS.md.tpl'`
- `bun test tests/init-command.spec.ts`
- `bun test tests/update-command.spec.ts`
- `bun test tests/wrap.test.ts`
- `bun test tests/doctor-command.spec.ts`
- `bun test tests/uninstall-command.spec.ts`
- `bun test tests/cli-ux.test.ts`
- `bun test tests/receipts-summary.spec.ts`
- `bun test tests/ceremony-contract.spec.ts`
- `bun test tests/generated-payload.test.ts`
- `sh -c '! grep -rn -- "--no-verify" src/commands'`
- `sh scripts/proof-cli-ux.sh`
- `bun run build`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`

## F1 · MAJOR · resolved
**Where:** tests/arch.spec.ts:135
**Critic (r1):** `requiredRestrictions` pins the guards, payload and commands fences but omits the required git and workflow fences from §6.3. The current JSON has those rules, but deleting either rule silently drops its protection without failing the arch test → include git→commands/cli/chain/guards and workflow→commands/cli/chain in `requiredRestrictions`.

**Fixer (r1):** fixed — pinned the git and workflow layer restrictions in `tests/arch.spec.ts` · verify: `bun test tests/arch.spec.ts` ✓, `bun run typecheck` ✓, `bun run lint` ✓
**ROOT CAUSE:** `requiredRestrictions` omitted the required git and workflow layer fences.
**FIX:** Added explicit git→commands/cli/chain/guards and workflow→commands/cli/chain assertions.
**LESSON:** Pin every required source-target fence so removing its config rule fails the architecture test.
**Critic (r2):** Resolved; all seven git/workflow restrictions are now required assertions, and the 54-test arch suite passes. Runtime files were not changed by the fix, so the prior CP10 runtime review remains valid.
