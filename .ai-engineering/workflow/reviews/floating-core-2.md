# Review thread · floating-core #2 · Delete the workspace hub and add the ceremony contract test

## Goal
The workspace hub, its server, UI, template and tests are gone, `ai-eng workspace` is an unknown verb, and a ceremony contract test proves every piece ai-orchestrator cites exists and ships in the canon.

## Acceptance
- No `Bun.serve` anywhere in src/.
- `ai-eng workspace` is an unknown verb and `--help` does not list it.
- The ceremony contract test passes: every skill, agent, script and template cited by ai-orchestrator exists and is embedded.
- The duplicate lifecycle validator in src/workspace/status.ts is gone.
- Arch test green with the workspace layer removed.

## changed_files
- .ai-engineering/arch.rules.json
- FILEMAP.md
- PERMISSIONS.md
- src/assets.ts
- src/cli.ts
- src/commands/workspace.ts
- src/embed.ts
- src/shared-verbs.ts
- src/workspace/
- templates/workspace.html.tpl
- tests/workspace-command.spec.ts
- tests/workspace-discovery.spec.ts
- tests/workspace-server.spec.ts
- tests/workspace-settings.spec.ts
- tests/workspace-ui.spec.ts
- tests/cli-ux.test.ts
- tests/ceremony-contract.spec.ts

## Verify
- `bun test tests/cli-ux.test.ts`
- `bun test tests/ceremony-contract.spec.ts`
- `bun test tests/generated-payload.test.ts`
- `sh -c '! grep -rn "Bun.serve" src'`
- `bun run typecheck`
- `bun run lint`
- `bun test tests/arch.spec.ts`
- `bun test --parallel=1`
