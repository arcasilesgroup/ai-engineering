# Security review - ai-engineering 2.6.0

## Executive summary

**No-go for production use as a security boundary.** Four new exploitable issues survived independent validation: three HIGH and one MEDIUM. They affect shell-command rewriting, repository-root selection, the Copilot CLI hook contract, and human approval of protected configuration changes. Each was reproduced in a local scratch repository. No source fixes were made during the audit itself; the fixes that followed are listed under [Remediation status](#remediation-status-uncommitted-working-tree) and stay `open` until committed.

The target is a local CLI and host-hook system, so its security boundary is the agent host's event payload and the CLI's allow/deny decision. No direct product comparator was used; host hook documentation was used only to establish payload and working-directory contracts. The audit did not exercise a live host session.

## Findings

| # | Severity | Title | Impact |
|---|---|---|---|
| 1 | HIGH | Copilot CLI camelCase payload bypasses all guards | Destructive calls on the installed Copilot surface receive allow with no applicable guard or receipt. |
| 2 | HIGH | Nested `.git` marker moves the governed root | A governed session can enter a nested directory and silently disable all guards. |
| 3 | HIGH | `adapt apply` accepts an agent-generated self-hash as approval | An agent can replace protected governance files and create a false `Approved-by` commit. |
| 4 | MEDIUM | Wrapped command is reparsed by a second shell | Quoted metacharacters become live shell syntax and can bypass self-protect on rewrite-capable surfaces. |

### 1. Copilot CLI payload bypass

- **Location:** `src/payload.ts:66-71`; `templates/settings.copilot.json.tpl:4-7`; `templates/settings.copilot.cli.json.tpl:4-7`.
- **Scenario:** A Copilot agent invokes a destructive Bash or file operation using the documented camelCase `preToolUse` event shape (`toolName`, `toolArgs`).
- **Impact:** `normalise()` reads only snake_case tool fields, leaves `tool_name` empty, and the chain allows calls without the relevant guards. A local CLI reproduction allowed `git commit --no-verify` and a write to `.ai-engineering/config.toml` for camelCase payloads while the snake_case control was denied.
- **Fix direction:** Map Copilot fields and tool names to the canonical payload, or register an event that supplies the expected shape. Fail closed on an empty tool name.
- **Confidence:** 9/10; the CLI behavior was reproduced. The documented host payload was not captured from a live Copilot process.

### 2. Nested `.git` disables governance

- **Location:** `src/env.ts:25-33`; `src/chain/mod.ts:128-150`.
- **Scenario:** In a host that reports the new working directory, an agent creates `nested/.git` and changes into `nested`.
- **Impact:** The nearest `.git` marker is treated as the repository root; the nested directory has no governance config, so the chain returns allow before running any guard or recording a receipt. Writes to the parent repository's protected config and hooks then pass.
- **Fix direction:** Pin the governed root to the session/workspace or resolve the outermost governed ancestor; judge paths against the repository that owns each target.
- **Confidence:** 7/10; the code path and local behavior were reproduced. Host `cwd` propagation was confirmed from documentation, not a live session.

### 3. `adapt apply` self-approves protected changes

- **Location:** `src/commands/adapt.ts:77-109,124-125`.
- **Scenario:** An agent writes a proposal page with a matching SHA-256 and runs `ai-eng adapt apply`.
- **Impact:** The hash is computed from attacker-controlled proposal data, not a human-held approval. The command replaces protected config, commits it with an `Approved-by` trailer derived from Git identity, and can disable governance.
- **Fix direction:** Require out-of-band human approval that the agent cannot generate, and block governance-changing commands from the governed session.
- **Confidence:** 8/10; reproduced through the chain and CLI in a local Git repository.

### 4. Wrapped command is reparsed

- **Location:** `src/guards/wrap.ts:17-18`; `src/wrap/index.ts:33-46`; `src/chain/mod.ts:265`.
- **Scenario:** On a rewrite-capable surface, issue `npm test '>' .ai-engineering/config.toml`.
- **Impact:** The original quoted `>` passes the guard, the wrapper joins argv with spaces, and `/bin/sh -c` interprets `>` as a live redirect. The governed config is truncated. Incremental attacker advantage is limited because other shell substitutions already pass some guard paths, so the independent validator rated this MEDIUM.
- **Fix direction:** Preserve the original command as one value rather than joining argv and reparsing it, and do not skip later guards after a rewrite.
- **Confidence:** 8/10; reproduced with the real chain and shell on rewrite-capable surfaces. Claude Code does not apply this rewrite.

## Hardening and assurance notes

- The Copilot machine carrier ends its chain invocation with `|| exit 0`; a chain error is therefore not a denial on that carrier.
- The previous run's report and machine-readable dispositions disagree; open findings must not be treated as fixed without a landed commit.
- The runtime install path relies on Bun, while the npm launcher itself runs under Node. Record and test both runtime prerequisites on clean hosts.
- A local `doctor` result or checkout-based CI job cannot prove the published tarball and every release binary behave on clean machines.

## Positive patterns

- Guard crashes fail closed in the chain.
- Unquoted writes to protected governance paths are denied by self-protect.
- The workflow definitions use SHA-pinned actions and mostly default to read-only repository permissions.
- Reproductions used isolated local repositories; no external target was attacked and no source files were changed.

## Remediation status (uncommitted working tree)

All four findings are fixed in the working tree, together with the bypasses that two independent adversarial reviews found while testing those fixes. **Nothing is committed yet**, so every disposition in `findings.json` stays `open` until a commit SHA exists.

| # | Finding | What changed | Regression tests |
|---|---|---|---|
| 1 | Copilot CLI payload bypass | `normalise()` maps Copilot runtime names (`bash`, `create`, `edit`, `str_replace_editor`, `view`, `apply_patch`, …) and `toolArgs` (object or JSON string) to the guard shape, including `path`, `old_str`, `new_str` and `file_text`. Required arguments are checked. Unknown tools, MCP names, `write_bash`, malformed arguments, an empty tool name, `sql` that attaches or writes files, and a call naming two different target paths all deny. The agent's own bookkeeping tools (`report_intent`, `sql`, `read_bash`, `task_complete`, …) pass, so a governed Copilot session no longer blocks itself. `apply_patch` is parsed strictly: every Add/Update/Delete/Move path in every block is judged, governance and checkpoint files deny, and an unreadable patch denies. | `payload-dialect.spec.ts`, `chain-dispatch.spec.ts`, `checkpoint-guard.spec.ts` |
| 2 | Nested `.git` moves the governed root | The root is the outermost governed ancestor. Relative paths are judged from both the repo root and the shell's cwd. Governance files are protected by name wherever they sit (`*/.ai-engineering/{config.toml,overrides.toml,ai-eng.lock,arch.rules.json}`, `*/.git/hooks`, `*/.git/config`). That last rule closes a hijack the first fix introduced: writing a config *above* the repo would otherwise have moved the root. | `chain-dispatch.spec.ts`, `self-protect.spec.ts` |
| 3 | `adapt apply` self-approval | The writer is removed. `ai-eng adapt apply` exits 2: a hash beside agent-written content cannot prove a person approved it. The person applies approved changes by hand, outside the agent session. The verb is also denied from agent shells. | `adapt.spec.ts`, `self-protect.spec.ts` |
| 4 | Wrapped command reparsed | The rewrite passes the original command as one base64url token (`ai-eng wrap test --base64 …`), so quoting survives byte for byte. The wrapper runs only a test-runner command, only inside a governed repo, and only after self-protect, no-verify, policy, injection and checkpoint allow it from there. It is no longer a trampoline. Wrap now runs after every other guard. | `wrap.test.ts`, `chain-dispatch.spec.ts` |

### Bypasses found while validating the fixes (also fixed in the working tree)

- **Shell commands that hide what they run:** base64 decode, `curl … | sh` in every spelling, process substitution, `eval`/`iex`, a verb computed at run time, an interpreter reading its program from stdin, and an encoded PowerShell command.
- **Redirections:** those written before the verb, and every redirect spelling (`>&`, `&>`, `>|`, `&>>`, `>>|`, `>!`, `{fd}>`, `<&`).
- **Path spellings:** quote splicing, `\` escapes, `$'…'`, globs and braces, same-command variables, `$HOME`, `cd`/`pushd` targets, `//` and `..`.
- **Verbs that write but were not on the writer list:** any verb that is not a known reader is now denied when it names a governed path. Verbs that act on a whole tree are denied on an ancestor of a governed path (`mv .git x`). Writers fed by `xargs` or `find -exec`, and `git apply`/`patch`, are denied too.
- **Restricted `ai-eng` verbs reached indirectly:** anywhere in a segment or substitution, behind flags, through git `!` aliases or heredocs fed to a shell, and by copying or linking the binary.
- **PowerShell:** writer cmdlets naming governed paths.
- **Git floor:** `--no-veri` prefixes, quoted spellings, `GIT_CONFIG_*`/`--config-env`, and a `core.hooksPath` that is not this repo's `.git/hooks`.
- **Second review round:**
  - Case-insensitive governance names (`.Ai-Engineering/CONFIG.TOML`).
  - Host carriers protected by name (`.github/hooks/*`, `.claude/settings*.json`, `.cursor/hooks.json`, `~/.gitconfig`).
  - Code hidden inside commands: `sh -ce`, `trap`, `find -exec sh -c`, `alias`/`hash -p`, git config keys that run programs, `GIT_EDITOR`-style variables and `BASH_ENV`.
  - Restricted `ai-eng` text handed to other code runners (`osascript`, `at`, `xonsh`).
  - Extra PowerShell forms: encoded-command prefixes, `.NET` calls, the call operator, string concatenation.
  - `apply_patch` read from stdin or an unquoted heredoc.
  - Archive extraction into the repo.
  - Writes into checkpoint files from the shell.
  - git: `--no-verify` produced by a variable, substitution, glob or brace; `include.path`; aliases expanding to `--no-verify`; `GIT_DIR`/`HOME`/`--git-dir`.
  - Words that follow a `$(…)` in the same command.
- **Other:** extra argument keys that hid the real target path, and several patch blocks in one shell command.

Shell parsing moved to `src/guards/shell.ts`. It is a reader, not a shell: anything it cannot read is denied.

### Residual risk (open, accepted ceiling)

These checks read commands. They are not an OS sandbox and do not replace one.

- **Opaque programs:** an interpreter given an opaque program (`python3 -c "…b64decode…"`, `node -e …`) can still write anywhere.
- **Staged scripts:** a script written in one call and run in a later one is judged only by its visible text.
- **Sessions outside the repo:** a session whose working directory is outside every governed repository is ungoverned, because the gate resolves the root from the payload `cwd`. Pinning the governed root per session is the upgrade path.
- **Copilot fail-open:** the Copilot machine carrier still ends with `|| exit 0`, so a crash there is not a denial. Guard denials themselves exit 0 with a deny body and are unaffected.
- **Unmeasured tools:** MCP tools and any Copilot tool not in the measured list are denied in governed Copilot sessions until someone adds them deliberately.
- **Accepted over-denials:** process substitution (`diff <(a) <(b)`), `find . -delete`, archive extraction in the repo root, copying a governance file elsewhere, and a commit message that names an absolute governed path. Each denial says what to do instead.
- **Persistent state from earlier calls:** an alias, git config value or script set up in an earlier call that the guards allowed is judged only by its visible text when it runs.

### Validation (uncommitted working tree)

- **Regressions:** attack and benign-control regressions are in `tests/self-protect.spec.ts`, `tests/no-verify.spec.ts`, `tests/payload-dialect.spec.ts`, `tests/chain-dispatch.spec.ts`, `tests/wrap.test.ts` and `tests/checkpoint-guard.spec.ts`.
- **Fresh clone with this tree applied:** `bun run lint` exit 0, `bun run typecheck` exit 0, `bun test --parallel=1` 1745 pass / 0 fail / 16 skip, and `bun run build` exit 0. The original checkout fails 77 tests only because of untracked leftovers (`tests/.worktree-lifecycle-*`, `src/.DS_Store`), which were left in place.
- **Bundle:** `bun scripts/gen-assets.ts` regenerated `skills/.chain-bundle/ai-eng-chain.ts`. `src/assets.ts` did not change.
- **Binary:** the source map of `dist/ai-eng` embeds the final text of every changed module. A smoke test through `ai-eng chain PreToolUse --surface copilot-cli` behaved as expected:
  - internal tools, source edits and patches were allowed;
  - governance patches, decode-to-shell, `--no-verify` and unknown tools were denied;
  - `npm test` was rewritten to the base64 wrapper.
- **Independent adversarial review (Claude Opus 5.5):**
  - Two complete rounds ran. Every bypass they reproduced is fixed, and their attack batteries now deny everything except the accepted ceiling.
  - A third round was cut short when the model became unavailable. Its partial batteries found two more classes, both now fixed: computed output paths (`sort -o "$(printf …)"`) and `git … --output=`.
  - A fresh review of the final tree could not run for the same reason.

## Disposition

All four findings remain `open` in `findings.json`. The fixes are in the uncommitted working tree and are not yet identifiable by a commit. Set each disposition to `fixed` with the fixing commit SHA once it lands.
