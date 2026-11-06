# Validated finding details

The separate validator confirmed all four findings. It adjusted the wrapped-command issue from HIGH to MEDIUM because it adds limited attacker capability over other shell forms already accepted by the guard set. Findings 2 and 3 include host-contract conditions that were not tested in a live host process.

## 1. Copilot CLI camelCase payload bypasses guards - HIGH

**Trace:** `settings.copilot.json.tpl:4-7` registers `preToolUse` -> `chain/mod.ts:159` calls `normalise()` -> `payload.ts:66-71` reads only `tool_name`/`tool` and `tool_input`/`input` -> `chain/mod.ts:198` selects guards with an empty tool name and allows.

**Reproduction:** In a governed scratch repository, call `ai-eng chain PreToolUse --surface copilot-cli` with the documented camelCase payload containing `toolName: "bash"` and `toolArgs: {"command":"git commit --no-verify"}`. The process returns allow with no output. The snake_case payload is denied. A camelCase write to `.ai-engineering/config.toml` is also allowed.

**Attacker result:** A Copilot agent can use governed tools without self-protect, no-verify, policy, injection, or wrap checks. The receipt records an empty tool and only the loop guard.

**Conditions:** The repo enables `copilot-cli`; the host emits the documented camelCase schema for the registered camelCase event. The host payload was not captured live.

## 2. Nested `.git` marker disables governance - HIGH

**Trace:** `chain/mod.ts:128-144` uses payload `cwd` to resolve the root -> `env.ts:25-33` stops at the nearest `.git` entry -> `chain/mod.ts:150` returns allow when that nested directory has no config.

**Reproduction:** In a governed scratch repository, run `mkdir -p nested/.git`, then change the host-reported `cwd` to `nested`. Calls to remove the parent `.ai-engineering/config.toml`, write that file, and run `git -C .. commit --no-verify` return allow with no guard or receipt. The same calls from the governed root are denied.

**Attacker result:** The agent can silently disable the complete chain for subsequent calls in the session.

**Conditions:** The host updates hook `cwd` after a persistent `cd`; this was established from host documentation, not a live session. Hosts that pin `cwd` to the workspace root are not affected.

## 3. `adapt apply` self-approves protected changes - HIGH

**Trace:** `cli.ts:95` dispatches `adapt apply` -> `commands/adapt.ts:77-89` validates a hash stored beside attacker-controlled proposal contents -> `commands/adapt.ts:108` writes the protected file -> `commands/adapt.ts:124-125` commits with an `Approved-by` trailer.

**Reproduction:** Generate a proposal page for `.ai-engineering/config.toml` using the matching SHA-256, write that page from the governed agent, then invoke `ai-eng adapt apply`. In a scratch repository, the command replaced the config with agent-controlled content and committed it. A following `git commit --no-verify` was allowed because governance had been removed.

**Attacker result:** The agent can change or remove the controls that are intended to be human-approved and produce a misleading approval trail.

**Conditions:** Git identity is available; if absent, the agent can set repository-local identity through its normal Git call.

## 4. Wrapped command is reparsed - MEDIUM

**Trace:** `chain/mod.ts:198` evaluates the original command -> `chain/mod.ts:265` returns the test-command rewrite -> `wrap/index.ts:36` joins argv with spaces -> `wrap/index.ts:46` invokes `/bin/sh -c`.

**Reproduction:** On a rewrite-capable surface, submit `npm test '>' .ai-engineering/config.toml`. The quoted operator passes self-protect; after host parsing and argument joining it becomes an unquoted redirect. Running the rewritten line truncates the governance config. The unquoted control is denied.

**Attacker result:** A string that guards treated as inert text becomes shell syntax and can modify a protected file. Subsequent calls can become ungoverned.

**Conditions:** The surface applies the rewrite (Cursor, Codex, OpenCode, Pi, or Oh My Pi) and the command qualifies for wrapping. Claude Code is not affected by this rewrite path.
