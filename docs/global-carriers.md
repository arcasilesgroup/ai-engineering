# Global carriers

A carrier is the file a host reads to reach `ai-eng chain`. It lives where that host actually reads: under the user's home for the surfaces that load user scope, in the checkout for the two whose cloud readers only see the repo. The repository declares itself in `.ai-engineering/config.toml`, and only that declaration makes the policy apply: the gate is `declaration()` in `src/env.ts` — the file exists, parses, and names `[surfaces] enabled` — and it is the only fail-open in the system. A repo that never declared itself is not governed: the chain allows, and nothing is written there, not even a receipts directory. Nothing else in the codebase answers "is this repo governed"; `enabledSurfaces()` and the gate read the same call, so they cannot disagree about what was said.

## The carrier table

`src/surfaces/surfaces.json` is the registry. Every path carries its `source` and the date it was read, so a stale claim is a delta against a recorded measurement instead of against somebody's memory. A path claimed from memory is the failure this table exists to end: ai-engineering wrote the OMP carrier into `.agents/hooks/`, which OMP never reads, and `doctor` called it green.

| Surface | Scope | Path | Kind | Chain bundle | Evidence source | Measured |
|---|---|---|---|---|---|---|
| Claude Code | machine | `.claude/settings.json` | settings | — | research/004 §01 (user scope applies to every project) · anthropics/claude-code#83502: user-scope hooks run without workspace trust | 2026-09-14 |
| Oh My Pi | machine | `.omp/agent/hooks/pre/ai-eng.ts` | module | `.omp/agent/hooks/pre/.ai-eng-chain.ts` | omp://hooks.md (native hook capability: `<configDir>/hooks/pre\|post`, agent dir is `PI_CODING_AGENT_DIR` aware) · live probe on omp 18.1.17 2026-09-14: a default-export factory written there loaded and blocked a bash call; the old `.agents/hooks/` path loads nothing; the chain bundle is dot-prefixed because omp's hook scanner loads EVERY `*.ts` in that directory and a bundle is not a hook factory | 2026-09-14 |
| OpenCode | machine | `.config/opencode/plugins/ai-eng.ts` | module | `.config/opencode/plugins/ai-eng-chain.ts` | research/004 §01 (opencode loads plugins from `~/.config/opencode/plugins/`) | 2026-09-14 |
| Cursor | repo | `.cursor/hooks.json` | settings | — | research/003 · cursor.com/docs/cloud-agent: cloud VMs have no access to your local home directory, and the user level loses to the project one | 2026-09-11 |
| Codex CLI | machine | `.codex/hooks.json` | settings | — | research/004 §01 (user hooks load even when the project is untrusted) · openai/codex#20321: trust is per hook definition, pinned by hash | 2026-09-14 |
| Copilot | repo | `.github/hooks/ai-eng.json` | settings | — | research/003: VS Code Copilot Chat and the cloud agent read the repo copy only | 2026-09-11 |
| Copilot | machine | `.copilot/hooks/ai-eng.json` | settings | — | research/004 §01: Copilot CLI 1.0.83 reads `~/.copilot/hooks/*.json` and never fires the repo copy | 2026-09-14 |
| Pi | machine | `.pi/agent/extensions/ai-eng.ts` | module | `.pi/agent/extensions/ai-eng-chain.ts` | pi.dev/docs/latest/extensions · brainstorm TrustFacts §3: pi has no native user-level HOOKS, only extensions | 2026-09-14 |
| Zed | — | — | — | — | `carriers: []` — it denies through its OWN tool permissions (`agent.tool_permissions`, `always_deny` regexes) and never by running our chain; its WASM extension API adds languages, themes, debuggers, MCP servers and slash commands, none of which intercepts a tool call, so there is no seat for a guard (`zed.dev/docs/ai/tool-permissions`, measured 2026-09-14 on Zed 1.19.2) | — |

Machine paths are relative to the base every machine-side path hangs off (`machineBase()` in `src/surfaces/adapters.ts`): `AI_ENG_HOME` when a test set it, otherwise the real physical home. A test install must never rewrite the real `~/.claude`, `~/.omp`, `~/.pi` or `~/.config`.

`chain` is a second file that must sit beside the entry: hosts that run the carrier in-process import the chain from it. The OMP bundle is dot-prefixed because the host's hook scanner loads every `*.ts` in that directory. `carrierFiles(id, scope)` decides whether a surface has a generator at all — no adapter, no offer — and `init` refuses a surface that cannot carry a required guard (`surfaceCanGovern`).

## How a carrier is written

| Kind | Install | Uninstall |
|---|---|---|
| `settings` | merged by marker into the file that is already there | our entries out by marker, theirs kept |
| `module` | the whole file written, plus its chain bundle beside it | entry and bundle unlinked whole |

Both placements go through the same merge (`mergeSharedText` in `src/install.ts`). A machine `settings` file that does not exist is written from our template as is; one that exists is merged, because it can be one the user already owns and nothing of theirs is touched or reformatted. Repo carriers are planned by `surfaceEntries()` in `src/commands/init-shared.ts` as `{ path, ours, merge: kind === "settings" }`, so Cursor and Copilot take the merge in the checkout too.

The merge rules, from the source:

- Objects merge key by key; arrays keep every foreign entry and append ours, dropping our own previous ones first — which is what makes a second install a no-op; a scalar from our template is ours.
- Our entries are identified by the marker `/(?:^|[;&|]\s*)ai-eng chain/`. It has to be the command itself, not the word anywhere in a string: `my-wrapper.sh -- ai-eng chain PreToolUse` is the user's hook, and an uninstall that deletes it takes away something we never installed. The marker matches at the start of a command or after a shell separator — the Copilot entry guards the call with `command -v ai-eng … && ai-eng chain …`, and that `&&` is where ours starts.
- Refusals, each one named: `not-json` when the file does not parse, `not-object` when it parses to something that is not an object, `reformat` when this code cannot reproduce the file's bytes exactly with its own indentation, line endings and trailing newline. A settings file with comments, a typo, or a layout this installer would have to rewrite is the user's: it is not touched, and the reason is reported.
- Module carriers are written whole, and the sha256 of the entry definition is recorded per surface in `machine.json` (`~/.ai-engineering/machine.json`) whether or not the merge changed a byte.
- Uninstall (`removeMachineCarriers`) takes out our entries deepest-first; the containers that existed only to hold them go with them, so a settings file a user had before init is one again after uninstall. Our banner goes by content, and a `$comment` we did not write stays. A settings file that cannot be parsed or reproduced is left alone and said. A file that held only our entries is deleted. `machine.json` goes with the carriers when it holds nothing else.

## What `doctor` reports

Three questions, and they are separate on purpose.

| Check | Question | Rows |
|---|---|---|
| `config.toml` (check 3) | this IS the gate | governed · surfaces, or absent / unparseable / no `[surfaces]` enabled list. "I could not read it" must never read as ok: the chain treats an unreadable file as an undeclared repo |
| `surface <id>` (check 11, row a) | the machine carrier: is it where that host actually reads, and is it the one this binary ships? | missing (fail on core, warn otherwise) · `module` bytes that do not match the shipped ones (warn) · `settings` with no ai-eng entries (warn) |
| `surface <id>` (check 11, row b) | the repo carrier: for the hosts whose readers live in the checkout, is their carrier in the repo? | present, or missing (fail, warn for best-effort) |
| `machine state` (check 11b) | which binary wrote the carriers, and is this one older than that record? | a downgrade warns; a changed definition warns and names the surfaces |

Existence is not the question for check 11, row a: the OMP carrier sat in `.agents/hooks/` for a year, absent from nothing and read by nobody. Row b is the declaration, and no file answers the third question: a downgrade is not cosmetic, because the carrier is the new binary's and the chain it calls would be the old one, which has no gate — the policy would fall back onto repos that never asked for it. Codex re-asks for trust in `/hooks` after any byte change, so a changed definition is the only way to know that happened. A surface with no carrier row gets `no carrier: guard wiring is not implemented for this host`.

## The git floor

`git init.templateDir` puts the three shims in every new clone. The shims stay in `.git/hooks/` — same place, same marker — so the sweep, the coexistence with husky and the contract do not change. Three rules, and none of them is "write over what is there":

1. No `templateDir` → ours, in `~/.ai-engineering/git-template` so it is deleted with the rest on uninstall, and the previous value (none) is recorded.
2. A `templateDir` the user already had → our shims are copied INTO it, marker-managed, and their setting is never touched. A `hooks/` directory holding someone else's hooks is left alone entirely.
3. A `templateDir` that is ours → the shims are made current, nothing else.

The shims are `pre-commit`, `commit-msg` and `pre-push`, mode `0755`, marked `ai-eng git floor shim`. Logic lives in the binary, not in the file. `writeShims` replaces a file only when it already carries our marker: never trample a hook a person wrote. `uninstall` runs `restoreTemplateDir()`, which takes our shims out of a directory we joined (their setting stays), leaves the setting alone when it now points somewhere this install did not set, and otherwise unsets it and removes our directory.

The shim carries the gate itself, because it is born with every clone and must pass in silence where nobody asked for policy:

```sh
[ -f .ai-engineering/config.toml ] || exit 0
command -v ai-eng >/dev/null 2>&1 && exec ai-eng git pre-commit
echo "ai-eng: this repo is governed but 'ai-eng' is not on PATH — install it, or remove .ai-engineering/config.toml to stop being governed (hook: pre-commit)" >&2
exit 1
```

`core.hooksPath` global stays discarded: a LOCAL `hooksPath` (husky, pre-commit) beats the global one and silently leaves the repo ungoverned, so redirecting it would buy nothing. `init` unsets a value that points at ai-eng's own floor because that value is ours, names a value that is the user's together with the one line that fixes it, and the `no-verify` guard denies a command that would repoint it.

## The proofs

```sh
sh scripts/proof-carriers.sh   # G8: the OMP carrier loads, proved with the host itself
sh scripts/proof-cli-ux.sh     # R16: the floor reaches new clones, and a repo without config.toml is not policed
```

`proof-carriers.sh` runs two proofs, strongest first: the host's own loader — `discoverAndLoadHooks` from the installed omp package — discovers the carrier at `<agentDir>/hooks/pre/`, binds its handlers, and the handler blocks an adversarial call while writing a receipt in the governed repo; then a real headless `omp` session, when the binary is on PATH. Both run inside a sandbox `AI_ENG_HOME` with `PI_CODING_AGENT_DIR` pointed at the same directory, so the proof never touches the developer's `~/.omp`. A carrier that is present everywhere and loaded nowhere is worse than no carrier, because it reports green.

`proof-cli-ux.sh` covers the floor under R16: it owns the global git config for its run and puts it back, then checks that `init` sets `init.templateDir`, that a fresh clone is born with the three shims and that a commit there reaches the floor, that the shim copied into a repo without `config.toml` exits 0 in silence, and that a governed repo with no `ai-eng` on PATH exits 1.

## Adding a new surface

1. A row in `src/surfaces/surfaces.json`: `id`, `label`, `tier`, `can`, and `carriers` with `scope`, `kind`, `path`, `source` and `measured`. The `source` names the document or probe the path was read from, with its date. `carriers: []` is a valid answer — a surface that cannot deny has no carrier to place — and `can.deny: false` makes `init` refuse it rather than promise falsely.
2. `carrierFiles(id, scope)` in `src/surfaces/adapters.ts`: a case returning the entry template and, for an in-process host, the chain bundle. No case means no adapter, and no offer at init.
3. A template under `templates/` (`settings.<id>.json.tpl` for a settings host, `plugin.<id>.ts.tpl` for a module host). Then regenerate the payload: `bun scripts/gen-assets.ts` is not optional after touching `templates/`, because the binary carries `src/assets.ts` and a file that is not in it does not ship.
4. A load proof. A path is declared when the host loads it, not when it exists; `scripts/proof-carriers.sh` is the shape to copy — drive the host's own loader, assert the handler blocks, and check the receipt the chain wrote.
