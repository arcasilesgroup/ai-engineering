# Surface capability matrix

Measured: **2026-11-23** · binaries exercised on the measuring machine (macOS arm64).

This table is the truth about what `ai-eng` can enforce on each agent host. It is written
from live probes and the host's own documentation, not from the README. The registry
([`src/surfaces/surfaces.json`](../src/surfaces/surfaces.json)) and `ai-eng doctor` are
aligned to it; update all three together when a host changes.

## Legend

- **Enforced** — `ai-eng chain` runs synchronously before the tool call, in the governed
  repo the call belongs to, and a denial blocks it. The host's `can.deny` is `true`
  (JSON/exit-status) or `throw` (in-process).
- **Advisory** — `ai-eng` has no synchronous deny to reach: the host only lets it observe
  (async notification), or the host denies through its own permissions with no ai-eng hook,
  or — `agy` — the hook reaches the chain without the repository the call belongs to, so
  every call is read as ungoverned and allowed. The registry records that last case as
  `enforcement: "advisory"` beside a `can.deny` of `true`.
- **Fail closed** — a crashed or non-zero-exiting guard denies the call.
- **Fail open** — a crashed guard (or one that times out) lets the call proceed.

## Matrix

| Surface | Host CLI (measured) | Hook mechanism | Denial | Denied call really denied | Broken guard | Prompt hook | Enforced? |
|---|---|---|---|---|---|---|---|
| `claude-code` | claude 2.1.330 | sync pre-tool (`PreToolUse`) in `.claude/settings.json` | exit 2 + stderr | yes (verified in `tests/surfaces.test.ts`) | fail closed (exit 2 blocks) | `UserPromptSubmit` blocks via exit 2 | **enforced** |
| `oh-my-pi` | omp 19.1.0 | in-process module (`.omp/agent/hooks/pre/ai-eng.ts`) | throw in-process | yes | fail closed (throw) | none (no prompt-submit event) | **enforced** |
| `opencode` | opencode v2.2.7 | in-process plugin (`.config/opencode/plugins/ai-eng.ts`) | throw in-process | yes | fail closed (throw) | none | **enforced** |
| `cursor` | cursor-agent 2026.11.22 | sync pre-tool (`preToolUse`) in `.cursor/hooks.json` | stdout JSON `permission: deny`, exit 0 | yes | fail closed (`failClosed: true`) | `beforeSubmitPrompt` not wired | **enforced** |
| `codex` | **not installed** | sync pre-tool (`PreToolUse`) in `.codex/hooks.json` | stdout JSON `hookSpecificOutput.permissionDecision: deny` | not verified here (CLI absent) | fail open on hook error ("hook fails, tool proceeds") | `UserPromptSubmit` blocks: the same hook command runs `ai-eng chain UserPromptSubmit --surface codex` | **enforced** (unverified) |
| `copilot-cli` | copilot 1.0.115-7 | sync pre-tool (`preToolUse`) in `.github/hooks/ai-eng.json` + `~/.copilot/hooks/ai-eng.json` | stdout JSON `permissionDecision: deny`, exit 0 | yes | fail **closed** on crash/non-zero exit; fail **open** on timeout and when `ai-eng` missing | `userPromptSubmitted` output ignored → advisory | **enforced** (tool calls) |
| `copilot-vscode` | VS Code Copilot harness (shared) | same harness and hook files as the CLI | same as above | yes | same as above | same advisory prompt hook | **enforced** (tool calls) |
| `pi` | pi 1.6.0 | in-process extension (`.pi/agent/extensions/ai-eng.ts`) | return `{ block, reason }` | yes | fail closed (block) | none | **enforced** |
| `agy` | agy 1.5.14 | sync pre-tool (`PreToolUse`) in `~/.gemini/config/hooks.json` (machine only) | stdout JSON `decision: deny`, exit 0, verified live | not reachable today: the payload names no repository, so the chain reads an ungoverned root and allows (see below) | fail **closed** (non-zero exit or `{}` denies) | none (`PreInvocation` can terminate, does not inspect the prompt) | **advisory** |
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

## agy, verified live and demoted to advisory

PROBE (2026-11-23, agy 1.5.14, a `.agents/hooks.json` at a project root, headless print
mode `agy --print-timeout 90s -p "…"`):

1. The `PreToolUse` hook fired with a camelCase protojson payload:
   `toolCall.name` (`run_command`) and `toolCall.args.CommandLine` carry the command.
2. `{"decision":"deny","reason":"…"}` on stdout blocked the command.
3. A non-zero exit denied the call (fail closed).
4. Empty stdout (silence) allowed the call.
5. `{}` (empty JSON object) **denied** the call — the opposite of Copilot, where `{}` is
   "no decision".
6. `PostToolUse` fired but carried no result content, so the fetched-content containment
   arm cannot run on agy. An `error` string, when the host sends one, is read as the
   failure the loop guard's failure arm counts.

What the probe did NOT establish, and what demotes the surface to **advisory** (recorded
2026-11-23, the same day):

- The payload names **no repository**. The hook also runs with its process cwd set to the
  directory that holds `hooks.json`, so from the machine carrier that cwd is
  `~/.gemini/config`. The chain resolves the governed repo from a top-level
  `cwd`/`workspaceRoot`/`workspacePath` or from `process.cwd()`, finds neither inside a
  governed repo, and allows every call. Enforcement was never what the shipped wiring did.
- Only the ADAPTER and the machine carrier ship. The repo carrier `.agents/hooks.json` was
  removed on purpose: a committed hook that calls `ai-eng` fails closed when the binary is
  missing (agy denies on exit 127), so it would lock every teammate without `ai-eng` out of
  every tool call.
- No rewrite field was measured. The wrap guard's rewrite is answered with silence on agy,
  so the command runs exactly as the agent wrote it, unwrapped.
- `~/.gemini/config/skills` is wired as a skill mirror on the same claim that global
  customizations live under `~/.gemini/config/`; the discovery of skills there was not
  measured independently.

What would make it enforceable again, in order of preference: a payload that carries a
resolvable repository root (then the existing adapter and carrier start blocking the same
call every other host blocks), or a measured repo-carrier story that does not break a
teammate whose `PATH` has no `ai-eng` (a `command -v ai-eng … || exit 0` guard has no
equivalent here: agy denies on a missing binary, which is what the guard would have to
avoid).

## What the matrix does not claim

- **Prompt inspection** (`spoken-secret`) is enforced only on hosts with a blocking prompt
  hook: `claude-code` (`UserPromptSubmit`, exit 2) and `codex` (`UserPromptSubmit`, JSON
  deny in `hookSpecificOutput`). On Copilot the hook output is ignored; `Cursor` HAS a
  `beforeSubmitPrompt` event but it stays unwired (research/009 did not fire it); OpenCode,
  Oh My Pi, Pi and agy have no prompt-submit event at all.
- **Fetched-content containment** (`injection` on `PostToolUse`) needs the tool result in
  the payload; agy's `PostToolUse` does not carry it, so only the pre-tool read/fetch
  target check applies there.
- **`codex` is `not verified here`** — the CLI is not installed on the measuring machine.
