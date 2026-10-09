# Checkpoint 8 review

Goal: The workspace serves its English loading shell from one loopback-only Bun service, persists configured project roots under the user-level home, and reuses a healthy existing instance.

Acceptance:
- `ai-eng workspace` serves and opens the hub on loopback only; it never listens on a network interface.
- A second invocation reuses the healthy instance; an occupied or unhealthy service gives visible recovery guidance and never silently creates a second instance.
- Configured roots persist in user-level `home()/workspace.json`, are isolated through `AI_ENG_HOME` in tests, and do not become a second lifecycle registry.
- The initial English loading shell matches prototype state `loading-projects`; server or settings failures remain visible.

Changed files:
- src/cli.ts
- src/shared-verbs.ts
- src/commands/workspace.ts
- src/workspace/server.ts
- src/workspace/instance.ts
- src/workspace/settings.ts
- templates/workspace.html.tpl
- src/assets.ts
- .ai-engineering/arch.rules.json
- LEARNINGS.md
- tests/workspace-settings.spec.ts
- tests/workspace-command.spec.ts
- tests/workspace-server.spec.ts

Verify:
- bun test ./tests/workspace-command.spec.ts
- bun test ./tests/workspace-server.spec.ts
- bun test ./tests/workspace-settings.spec.ts
- bun scripts/gen-assets.ts
- bun test ./tests/embed-canon.spec.ts
- bun run build
- bun run typecheck
- bun run lint
- bun test ./tests/arch.spec.ts

## Round 1 — Critic

### F1 [P2] Health probe can mistake an unrelated listener for the workspace
- **Location:** `src/workspace/server.ts:16–27`
- **Scenario:** Any unrelated listener on the configured port that returns `200 {"ok":true,"status":"ok"}` is treated as the workspace. The CLI then opens its overview URL on that service instead of reporting an occupied port.
- **Coverage gap:** `tests/workspace-command.spec.ts:73–85` uses a generic HTTP server that returns this exact health body and asserts URL opening, without verifying that the listener serves the workspace.

### F2 [P2] A stale configured root prevents replacing or removing roots
- **Location:** `src/workspace/settings.ts:23–26`
- **Scenario:** `writeWorkspaceRoots()` first calls `readWorkspaceRoots()`. If an existing configured root has since moved or been deleted, validation throws before the caller can replace the list and remove the stale path.
- **Coverage gap:** Settings tests cover valid existing roots and malformed JSON, but not a well-formed settings file whose previously valid root no longer exists.

### F3 [P2] Direct settings overwrite can leave truncated JSON on interruption
- **Location:** `src/workspace/settings.ts:28`
- **Scenario:** The settings file is overwritten directly. Process interruption after truncation but before the complete JSON write leaves unreadable settings and prevents subsequent settings loads.
- **Coverage gap:** Tests check successful persistence and preservation of pre-existing malformed bytes, but do not cover interruption during a write.

**VERDICT: FAIL** — 0 resolved, 0 withdrawn, 0 arbitrated, 3 open (F1, F2, F3).
