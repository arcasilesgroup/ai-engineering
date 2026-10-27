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

## F1 · BLOCKER · fixed
**Where:** src/install.ts:47
**Critic (r1):** The chain marker matches any command segment after `;`, `&` or `|`, so `isOurs` removes an entire user hook such as `my-audit.sh && ai-eng chain PreToolUse` during update/uninstall. Match only the exact generated chain command forms (including Copilot's availability wrapper), and add a regression proving a user wrapper is retained.

**Fixer (r1):** fixed — `src/install.ts` now matches only exact generated chain commands, including Copilot's exact availability wrappers; the update regression preserves a user's wrapper while replacing the exact managed command · verify: `bun test tests/carriers-install.spec.ts tests/chain-dialect.spec.ts` ✓
**ROOT CAUSE:** Managed-hook detection matched a chain substring inside user-written shell wrappers.
**FIX:** Replaced separator-based matching with exact generated-command matching and added an update regression for both wrapper retention and stale managed-command replacement.
**LESSON:** Remove shared hooks only when the complete command matches a generated command.

## F2 · MAJOR · fixed
**Where:** src/surfaces/surfaces.json:90
**Critic (r1):** Cursor's documented `stop` hook (`.ai-engineering/research/011-shopify-workflow-en-ai-engineering.html:306,314`) is omitted from surface support and its carrier, so G8 never runs there despite the harness emitting the event. Record the lowercase event, wire its supported follow-up response, and assert the emitted event—not only exact `"Stop"`—in carrier tests.

**Fixer (r1):** fixed — Cursor now declares and installs lowercase `stop`, routes it to `chain Stop`, and returns `followup_message` for Cursor Stop denials · verify: `bun test tests/carriers-install.spec.ts tests/chain-dialect.spec.ts` ✓
**ROOT CAUSE:** Cursor's native Stop event and follow-up response were absent from the surface declaration, carrier, and dialect.
**FIX:** Added Cursor's `stop` carrier, event-specific follow-up envelope, and regressions for the lowercase carrier event and Stop response.
**LESSON:** Model a host's native event key and its response dialect explicitly instead of assuming another surface's Stop contract.
