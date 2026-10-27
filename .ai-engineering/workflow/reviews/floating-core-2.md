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

## F1 · MAJOR · resolved
**Where:** tests/ceremony-contract.spec.ts:84 (citation at skills/ai-orchestrator/SKILL.md:165)
**Critic (r1):** The template extractor only matches `.ai-engineering/<name>.html` with no subdirectory, so the Phase 1 viewer the orchestrator opens (`.ai-engineering/workflow/checkpoints/viewer.html`, written from `templates/viewer.html.tpl`, listed as a ceremony piece in brainstorm 6.2 bis "Visor viewer.html") is never extracted. Probing the extractor on HEAD yields templates PRD/brainstorm/spec/plan/recap only — deleting or un-embedding `viewer.html.tpl` leaves the contract green, so the acceptance "every … template cited by ai-orchestrator exists and is embedded" is not proved (R2, R7). → Let the design-artifact pattern accept nested `.ai-engineering/…/<name>.html` paths (mapping the basename to `<name>.html.tpl`), add `viewer.html.tpl` to the extractor floor assertion, and add a nested-path citation to the negative fixture so the branch is pinned.
**Fixer (r1):** fixed — the artifact pattern now accepts any depth `.ai-engineering/(dir/)*<name>.html` and maps the basename to `<name>.html.tpl` (tests/ceremony-contract.spec.ts:85, doc comment :47-49); extractor floor asserts `brainstorm/plan/viewer.html.tpl` (:182); negative fixture cites `.ai-engineering/workflow/board/ghost-viewer.html` and expects `template ghost-viewer.html.tpl: no templates/ghost-viewer.html.tpl` (:202, :220). Placeholder outputs (`NNN-…`, `<name>`) live in skills the orchestrator does not invoke or don't match `[\w-]+`, and the real-repo contract stays green. · verify: `bun test tests/ceremony-contract.spec.ts tests/cli-ux.test.ts` ✓ (12 pass) · `bun run typecheck` ✓ · `bun run lint` ✓
**Critic (r2):** resolved — the matcher now accepts nested `.ai-engineering/…/<name>.html` (:85), the floor requires `viewer.html.tpl` (:182), and the fixture pins a nested citation; un-embedding the viewer now yields a canon gap. Re-ran the contract, cli-ux, arch and payload tests (37 pass), plus typecheck and lint (exit 0).


## F2 · MINOR · resolved
**Where:** tests/ceremony-contract.spec.ts:136
**Critic (r1):** The "script present in the repository but not installed by init" branch has no case in the negative fixture (only "not in the repository" is exercised), so a regression that drops the canon check for scripts stays green (R3). → Add a fixture script that exists under the fixture `skills/ai-fixture/` or `scripts/` but is absent from the materialized canon, and expect the `not installed by init` line.
**Fixer (r1):** fixed — fixture writes `scripts/stray-gate.py` and cites it (tests/ceremony-contract.spec.ts:202, :209); expects `script scripts/stray-gate.py: not installed by init` (:217). · verify: `bun test tests/ceremony-contract.spec.ts tests/cli-ux.test.ts` ✓ (12 pass) · `bun run typecheck` ✓ · `bun run lint` ✓
**Critic (r2):** resolved — the fixture's `scripts/stray-gate.py` exists in the repo, is absent from the canon, and is expected as `not installed by init`; verified green.


## F3 · MINOR · resolved
**Where:** tests/cli-ux.test.ts:81-86
**Critic (r1):** The malformed `workspace.json` fixture and its comment guard a hub that no longer exists; after the deletion it is dead setup that names a removed feature. → Drop the `workspace.json` write and comment (a temp `AI_ENG_HOME` alone keeps the run isolated).
**Fixer (r1):** fixed — dropped the `workspace.json` write, its comment and the now-unused `writeFileSync` import (tests/cli-ux.test.ts:6, :81-83). · verify: `bun test tests/ceremony-contract.spec.ts tests/cli-ux.test.ts` ✓ (12 pass) · `bun run typecheck` ✓ · `bun run lint` ✓
**Critic (r2):** resolved — the dead `workspace.json` setup and the unused import are gone; cli-ux stays green.
