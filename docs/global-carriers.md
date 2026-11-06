# Global carriers

A carrier is the file a host reads to reach `ai-eng chain`. Machine-side carriers live under the user's machine base; repo-side carriers live in the checkout. The repository's `[surfaces].enabled` declaration in `.ai-engineering/config.toml` is the gate: `declaration()` in `src/env.ts` accepts a file that exists, parses, and names that list. Without it, the chain allows and does not create receipts or other repo files.

## Canonical registry

Carrier paths, scopes, kinds, evidence sources and measurement dates live in the
[canonical surface registry](../src/surfaces/surfaces.json). Update that file when host
evidence changes; this guide covers the installation behavior around those declarations.

Machine paths are relative to the base every machine-side path hangs off (`machineBase()` in `src/surfaces/adapters.ts`): the physical home by default, or the alternate base supplied by `AI_ENG_HOME`. A test install must never rewrite the real `~/.claude`, `~/.omp`, `~/.pi` or `~/.config`.

When `PI_CODING_AGENT_DIR` is set, Oh My Pi and Pi carriers are placed under that host-provided agent directory instead of the default `.omp/agent` or `.pi/agent` path.

`chain` is a second file that must sit beside the entry: hosts that run the carrier in-process import the chain from it. The OMP bundle is dot-prefixed because the host's hook scanner loads every `*.ts` in that directory. `carrierFiles(id, scope)` decides whether a surface has a generator at all — no adapter, no offer — and `init` refuses a surface that cannot carry a required guard (`surfaceCanGovern`).

## How a carrier is written

| Kind | Install | Uninstall |
|---|---|---|
| `settings` | merged by marker into the file that is already there | our entries out by marker, theirs kept |
| `module` | the whole file written, plus its chain bundle beside it | entry and bundle unlinked whole |

Both placements go through the same merge (`mergeSharedText` in `src/install.ts`). A machine `settings` file that does not exist is created from our template as is, folder included, with an exclusive create (`O_CREAT|O_EXCL|O_NOFOLLOW`) inside the validated folder: the kernel refuses it if any name appeared there, so nothing of the user's is replaced. This is what `init` and `update` do on a fresh machine, and what doctor's `missing → ai-eng update` relies on. One that exists can be the user's: a merge that would change it needs a pathname replacement the portable filesystem API cannot bind to the validated file, so it is refused, left byte-identical, and reported. Repo carriers are planned by `surfaceEntries()` in `src/commands/init-shared.ts` as `{ path, ours, merge: kind === "settings" }`, so repo-side settings are merged too.

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

Existence is not enough for check 11, row a: a carrier counts only where its host reads it. Row b checks the repository declaration. A downgrade also warns because the older binary may not provide the chain the carrier calls. Codex re-asks for trust in `/hooks` after any byte change, so a changed definition is the only way to know that happened. A surface with no carrier row gets `no carrier: guard wiring is not implemented for this host`.

## The git hooks

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

`core.hooksPath` global stays discarded: a LOCAL `hooksPath` (husky, pre-commit) beats the global one and silently leaves the repo ungoverned, so redirecting it would buy nothing. `init` unsets a value that points at ai-eng's own hooks because that value is ours, names a value that is the user's together with the one line that fixes it, and the `no-verify` guard denies a command that would repoint it.

## The proofs


```sh
sh scripts/proof-cli-ux.sh     # R16: the hooks reach new clones, and a repo without config.toml is not policed
```

`proof-cli-ux.sh` covers the git hooks under R16: it owns the global git config for its run and puts it back, then checks that `init` sets `init.templateDir`, that a fresh clone is born with the three shims and that a commit there reaches the hooks, that the shim copied into a repo without `config.toml` exits 0 in silence, and that a governed repo with no `ai-eng` on PATH exits 1.

## Adding a new surface

1. A measured declaration in [`src/surfaces/surfaces.json`](../src/surfaces/surfaces.json). A surface with no carrier can still be valid; `init` refuses it when it cannot provide a required guard.
2. `carrierFiles(id, scope)` in `src/surfaces/adapters.ts`: a case returning the entry template and, for an in-process host, the chain bundle. No case means no adapter, and no offer at init.
3. A template under `templates/` (`settings.<id>.json.tpl` for a settings host, `plugin.<id>.ts.tpl` for a module host). Then regenerate the payload: `bun scripts/gen-assets.ts` is not optional after touching `templates/`, because the binary carries `src/assets.ts` and a file that is not in it does not ship.
4. A load proof. A path is declared when the host loads it, not when it exists: add a proof script alongside `scripts/proof-cli-ux.sh` — drive the host's own loader, assert the handler blocks, and check the receipt the chain wrote.
