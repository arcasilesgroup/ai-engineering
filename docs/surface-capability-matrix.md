# Surface capability matrix

Measured: **2026-11-23** · binaries exercised on the measuring machine (macOS arm64).

This table is the truth about what `ai-eng` can enforce on each agent host. It is written
from live probes and the host's own documentation, not from the README. The registry
([`src/surfaces/surfaces.json`](../src/surfaces/surfaces.json)) and `ai-eng doctor` are
aligned to it; update all three together when a host changes.

## Legend

- **Enforced** — `ai-eng chain` runs synchronously before the tool call and a denial
  blocks it. The host's `can.deny` is `true` (JSON/exit-status) or `throw` (in-process).
- **Advisory** — `ai-eng` has no synchronous deny to reach: the host only lets it observe
  (async notification), or the host denies through its own permissions with no ai-eng hook.
- **Fail closed** — a crashed or non-zero-exiting guard denies the call.
- **Fail open** — a crashed guard (or one that times out) lets the call proceed.

## Matrix

| Surface | Host CLI (measured) | Hook mechanism | Denial | Denied call really denied | Broken guard | Prompt hook | Enforced? |
|---|---|---|---|---|---|---|---|
| `claude-code` | claude 2.1.330 | sync pre-tool (`PreToolUse`) in `.claude/settings.json` | exit 2 + stderr | yes (verified in `tests/surfaces.test.ts`) | fail closed (exit 2 blocks) | `UserPromptSubmit` blocks via exit 2 | **enforced** |
| `oh-my-pi` | omp 19.1.0 | in-process module (`.omp/agent/hooks/pre/ai-eng.ts`) | throw in-process | yes | fail closed (throw) | none (no prompt-submit event) | **enforced** |
| `opencode` | opencode v2.2.7 | in-process plugin (`.config/opencode/plugins/ai-eng.ts`) | throw in-process | yes | fail closed (throw) | none | **enforced** |
| `cursor` | cursor-agent 2026.11.22 | sync pre-tool (`preToolUse`) in `.cursor/hooks.json` | stdout JSON `permission: deny`, exit 0 | yes | fail closed (`failClosed: true`) | `beforeSubmitPrompt` not wired | **enforced** |
| `codex` | **not installed** | sync pre-tool (`PreToolUse`) in `.codex/hooks.json` | stdout JSON `permissionDecision: deny` | not verified here (CLI absent) | fail open on hook error ("hook fails, tool proceeds") | `UserPromptSubmit` (advisory) | **enforced** (unverified) |
| `copilot-cli` | copilot 1.0.115-7 | sync pre-tool (`preToolUse`) in `.github/hooks/ai-eng.json` + `~/.copilot/hooks/ai-eng.json` | stdout JSON `permissionDecision: deny`, exit 0 | yes | fail **closed** on crash/non-zero exit; fail **open** on timeout and when `ai-eng` missing | `userPromptSubmitted` output ignored → advisory | **enforced** (tool calls) |
| `copilot-vscode` | VS Code Copilot harness (shared) | same harness and hook files as the CLI | same as above | yes | same as above | same advisory prompt hook | **enforced** (tool calls) |
| `pi` | pi 1.6.0 | in-process extension (`.pi/agent/extensions/ai-eng.ts`) | return `{ block, reason }` | yes | fail closed (block) | none | **enforced** |
| `agy` | agy 1.5.14 | sync pre-tool (`PreToolUse`) in `.agents/hooks.json` + `~/.gemini/config/hooks.json` | stdout JSON `decision: deny`, exit 0 | yes (verified live, see below) | fail **closed** (non-zero exit or `{}` denies) | none (`PreInvocation` can terminate, does not inspect the prompt) | **enforced** |
| `zed` | zed 1.28.1 | none (WASM extension API cannot intercept a tool call) | — | — | — | — | **advisory** (skills only) |

## Copilot, CLI and VS Code separately

The captain's request is Copilot, so it is split here even though both hosts read the same
files.

- **Copilot CLI** and **Copilot in VS Code** share one harness and one hook format
  (docs.github.com/en/copilot/reference/hooks-reference: "VS Code, the GitHub Copilot app,
  and GitHub Copilot CLI share this harness and its hook format"). One carrier set
  (`.github/hooks/*.json` in the repo, `~/.copilot/hooks/*.json` on the machine) serves both,
  and the same `preToolUse` command hook denies a call in both. `--surface copilot-cli`,
  `--surface copilot`, `--surface copilot-vscode` and `--surface vscode` all select it.
- What each **can** enforce today:
  - Both: `preToolUse` is synchronous and **fails closed on a crash or non-zero exit**, but
    **fails open on timeout**; the template also exits 0 (allows) when `ai-eng` is not on
    `PATH`, so a machine without it is not locked out.
  - Both: `userPromptSubmitted` command-hook output is **ignored** — the spoken-secret
    prompt guard does not run on Copilot; prompt rewriting is SDK-only.
- What is **CLI-only** (not VS Code): the `permissionRequest` hook (fires before the
  permission service, `behavior: allow|deny`), the `exec`+`args` no-shell form, autopilot
  mode where `ask` becomes `deny` (no user to answer), and the cloud-agent sandbox (bash
  only, pre-approved tool calls). These are host features, not things `ai-eng` adds.

## agy, verified live

On agy 1.5.14, a `.agents/hooks.json` at the project root was probed in headless print
mode (`agy --print-timeout 90s -p "…"`):

1. The `PreToolUse` hook fired with a camelCase protojson payload:
   `toolCall.name` (`run_command`) and `toolCall.args.CommandLine` carry the command.
2. `{"decision":"deny","reason":"…"}` on stdout blocked the command.
3. A non-zero exit denied the call (fail closed).
4. Empty stdout (silence) allowed the call.
5. `{}` (empty JSON object) **denied** the call — the opposite of Copilot, where `{}` is
   "no decision".
6. `PostToolUse` fired but carried no result content, so the fetched-content containment
   arm cannot run on agy; pre-tool deny of `run_command` and file writes is what is
   enforced.

## What the matrix does not claim

- **Prompt inspection** (`spoken-secret`) is enforced only on hosts with a blocking prompt
  hook: `claude-code` and `codex` (UserPromptSubmit). On Copilot the hook output is
  ignored, and on OpenCode, Oh My Pi, Pi, Cursor and agy there is no prompt-submit event.
- **Fetched-content containment** (`injection` on `PostToolUse`) needs the tool result in
  the payload; agy's `PostToolUse` does not carry it, so only the pre-tool read/fetch
  target check applies there.
- **`codex` is `not verified here`** — the CLI is not installed on the measuring machine.
