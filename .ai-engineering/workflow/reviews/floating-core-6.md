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

## F1 · BLOCKER · resolved
**Where:** src/install.ts:47
**Critic (r1):** The chain marker matches any command segment after `;`, `&` or `|`, so `isOurs` removes an entire user hook such as `my-audit.sh && ai-eng chain PreToolUse` during update/uninstall. Match only the exact generated chain command forms (including Copilot's availability wrapper), and add a regression proving a user wrapper is retained.

**Fixer (r1):** fixed — `src/install.ts` now matches only exact generated chain commands, including Copilot's exact availability wrappers; the update regression preserves a user's wrapper while replacing the exact managed command · verify: `bun test tests/carriers-install.spec.ts tests/chain-dialect.spec.ts` ✓
**ROOT CAUSE:** Managed-hook detection matched a chain substring inside user-written shell wrappers.
**FIX:** Replaced separator-based matching with exact generated-command matching and added an update regression for both wrapper retention and stale managed-command replacement.
**LESSON:** Remove shared hooks only when the complete command matches a generated command.
**Critic (r2):** Resolved. The matcher now checks exact `command` leaves, the legacy Python form is anchored, and the added update test proves a wrapper survives while the exact managed command is replaced.

## F2 · MAJOR · resolved
**Where:** src/surfaces/surfaces.json:90
**Critic (r1):** Cursor's documented `stop` hook (`.ai-engineering/research/011-shopify-workflow-en-ai-engineering.html:306,314`) is omitted from surface support and its carrier, so G8 never runs there despite the harness emitting the event. Record the lowercase event, wire its supported follow-up response, and assert the emitted event—not only exact `"Stop"`—in carrier tests.

**Fixer (r1):** fixed — Cursor now declares and installs lowercase `stop`, routes it to `chain Stop`, and returns `followup_message` for Cursor Stop denials · verify: `bun test tests/carriers-install.spec.ts tests/chain-dialect.spec.ts` ✓
**ROOT CAUSE:** Cursor's native Stop event and follow-up response were absent from the surface declaration, carrier, and dialect.
**FIX:** Added Cursor's `stop` carrier, event-specific follow-up envelope, and regressions for the lowercase carrier event and Stop response.
**LESSON:** Model a host's native event key and its response dialect explicitly instead of assuming another surface's Stop contract.
**Critic (r2):** Resolved. Cursor now declares and installs `stop`; `chain Stop --surface cursor` uses the `followup_message` denial envelope, and the carrier/dialect tests cover both.

## F3 · MAJOR · fixed
**Where:** src/install.ts:40
**Critic (r2):** `MANAGED_CHAIN_HOOKS` hand-copies every command string from the settings templates, creating a second source of truth contrary to LEARNINGS R7. A future template command change can leave the new managed entry unmatched and duplicate it on update. Derive these exact forms from a canonical source shared with template generation and cover every emitted command.
**Fixer (r2):** fixed — `src/install.ts` now derives exact hook commands from embedded settings templates, and `tests/carriers-install.spec.ts` verifies every emitted command is stripped while existing wrapper regressions stay intact · verify: `bun test tests/carriers-install.spec.ts`, `bun run typecheck`, `bun run lint`, `bun test tests/arch.spec.ts` ✓
**ROOT CAUSE:** The installer duplicated generated command forms instead of reading the embedded templates that own them.
**FIX:** Managed commands are collected from embedded settings-template hook entries; regression coverage discovers the same template commands and checks their exact removal.
**LESSON:** Derive managed entries from the artifacts that emit them, while retaining exact-match ownership boundaries.

## Gate 1 · behavior attempt 1 follow-up

### Finding 1 · test-hygiene serial assertion
**ROOT CAUSE:** The hygiene check's child serial run exited non-zero because the carrier-merge test still expected a generic `ai-eng` shell wrapper to be removed; the environment and cwd restoration assertions were not the cause.
**FIX:** Corrected the wrapper assertion and its shared matcher regression; `bun test tests/test-hygiene.spec.ts` now passes with both hygiene checks green.
**LESSON:** When an outer serial-run assertion fails, inspect the child suite's actual failure before changing cleanup behavior.

### Finding 2 · carrier merge drops sibling user hooks
**ROOT CAUSE:** `isOurs` searched recursively, so one exact managed command caused its enclosing hook group—and user wrapper siblings mentioning `ai-eng`—to be classified as ours.
**FIX:** Match only exact `command` fields, recursively strip owned hook leaves and prune only now-empty generated groups; added exact-content wrapper regressions in `tests/carriers-install.spec.ts` and `tests/adversarial/carrier-merge.test.ts`.
**LESSON:** Attribute ownership to each exact command leaf; remove a containing group only when it has no user hooks left.

## F4 · BLOCKER · fixed
**Where:** src/install.ts:8
**Critic (r1):** This adds an `install.ts → embed.ts` import while `embed.ts:8` already imports `hashFile` from `install.ts`, creating a module cycle contrary to `.ai-engineering/arch.rules.json`'s `forbid: cycles`. Break the cycle by extracting `hashFile` into a lower-level helper imported by both modules.

**Fixer (r3):** fixed — extracted `hashFile` to `src/shared-hash.ts`, imported it from both modules while preserving install's re-export, and taught `tests/arch.spec.ts` to detect same-layer cycles · verify: `bun test tests/carriers-install.spec.ts`, `bun run typecheck`, `bun run lint`, `bun test tests/arch.spec.ts` ✓
**ROOT CAUSE:** `embed.ts` imported `hashFile` from `install.ts`, then deriving managed commands from embedded templates made `install.ts` import `embed.ts`, forming a cycle.
**FIX:** Moved the shared file-hash helper to `src/shared-hash.ts`; managed commands still come from embedded settings templates and are matched exactly. The architecture test now checks the full module graph and proves its cycle detector catches same-layer loops.
**LESSON:** Shared low-level helpers belong below the modules that consume them, and a declared cycle prohibition must inspect module edges even within one layer.
