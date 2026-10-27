# Review thread · floating-core #6 · Retire Python checkpoint hooks without losing user hooks

## Goal
Carriers use the TypeScript checkpoint guard, updates replace only standalone managed Python hooks, the Python checker is retired, and the final embedded chain bundle matches its sources.

## Acceptance
- No carrier template calls `python3`, and Stop hooks are present only for harnesses that emit Stop.
- The checked-in `.github` hook does not invoke the retired Python checker.
- `ai-eng update` retires an old standalone Python checkpoint hook while preserving unrelated user hooks.
- The Python checker and its test are retired and are not materialized in the installed payload.
- After source edits and regeneration, generated-payload verifies the final chain bundle byte for byte.
- The ceremony contract test stays green with ai-orchestrator citing the TypeScript checkpoint guard.

## changed_files
- src/surfaces/surfaces.json
- .github/hooks/ai-eng.json
- src/install.ts
- src/embed.ts
- scripts/gen-assets.ts
- scripts/checkpoint-gate.py
- tests/test_checkpoint_gate.py
- templates/settings.claude.json.tpl
- templates/settings.codex.json.tpl
- templates/settings.copilot.json.tpl
- templates/settings.copilot.cli.json.tpl
- templates/settings.cursor.json.tpl
- templates/plugin.omp.ts.tpl
- templates/plugin.opencode.ts.tpl
- templates/plugin.pi.ts.tpl
- tests/carriers-install.spec.ts
- tests/checkpoint-gate-carrier.spec.ts
- tests/workflow-doctor-surfaces.spec.ts
- tests/ceremony-contract.spec.ts
- skills/ai-orchestrator/SKILL.md
- src/assets.ts
- src/commands/checkpoint-gate-report.ts
- FILEMAP.md

## Verify
- `bun test tests/carriers-install.spec.ts`
- `bun test tests/checkpoint-gate-carrier.spec.ts`
- `bun test tests/workflow-doctor-surfaces.spec.ts`
- `bun test tests/ceremony-contract.spec.ts`
- `sh -c '! grep -l python3 templates/settings.*.tpl templates/plugin.*.tpl'`
- `sh -c '! grep -q checkpoint-gate.py .github/hooks/ai-eng.json'`
- `bun test tests/generated-payload.test.ts`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`
