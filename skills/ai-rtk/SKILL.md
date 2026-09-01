---
name: ai-rtk
description: >-
  Use when you are about to run shell commands with long output — tests, builds, git,
  searches, docker/kubectl logs, cloud CLIs — to route them through rtk and read 60-90%
  less output; also to install or configure rtk, verify what gets rewritten with
  `rtk rewrite`, or report savings with `rtk gain`. Not for file/directory reads or
  searches the harness tools already cover — use the native read/grep/glob tools; not
  for a command whose output you need byte-exact.
license: MIT
---

# ai-rtk

rtk is a CLI proxy that filters and compresses command output before it reaches the model. `rtk cargo test` runs the same suite but returns failures only; `rtk git push` returns `ok main` instead of fifteen lines of progress. It does not change what a command *does* — only how much of its output you read.

## When to Use

- Any shell command whose base binary rtk has a filter for (see the table below) — prefix it with `rtk`.
- Reading a large file or running a broad search from the shell: `rtk read -l aggressive`, `rtk grep`.
- Installing, configuring, or verifying rtk; reporting savings with `rtk gain` / `rtk discover`.

Don't use for: shell builtins and file mutations, pipeline text filters, inline interpreters, or shell control flow — the full exclusion list is in **What NOT to Prefix**. Don't use when you need byte-exact output; see **Pitfalls**.

## Prerequisites

`rtk --version` should print a version. If not:

```bash
brew install rtk
curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh
cargo install --git https://github.com/rtk-ai/rtk
```

Hand-prefixing is always correct — rtk never double-wraps a command that already starts with `rtk`.

## How to Run

**The rule: prefix every supported shell command with `rtk`.**

```bash
rtk git status
rtk cargo test
rtk grep "parse_config" src/
rtk read src/main.rs -l aggressive
```

Prefix when the base command is one rtk has a filter for:

| Area | Commands |
|---|---|
| Files & search | `ls` `tree` `find` `grep` `rg` `wc` `diff` `du` `df` `cat`/`head`/`tail` (→ `rtk read`) |
| Git & forges | `git` `gh` `glab` `gt` |
| Rust | `cargo` |
| JS/TS | `npm` `npx` `pnpm` `jest` `vitest` `playwright` `tsc` `next` `prettier` `prisma` `lint` (eslint/biome) |
| Python | `pytest` `ruff` `mypy` `pip` `uv` `poetry` |
| Go | `go` `golangci-lint run` |
| Ruby | `rspec` `rubocop` `rake` `bundle` |
| PHP | `php` `composer` `phpunit` `phpstan` `pest` `pint` `paratest` `ecs` |
| JVM / other | `mvn` `gradlew` `sbt` `mix` `swift` `dotnet` `make` |
| Containers | `docker` `kubectl` `oc` `helm` |
| Infra | `terraform` `tofu` `pulumi` `ansible-playbook` `liquibase` |
| Cloud & net | `aws` `gcloud` `curl` `wget` `psql` `ping` `rsync` |
| Lint & system | `shellcheck` `yamllint` `markdownlint` `hadolint` `pre-commit` `trunk` `sops` `systemctl` `brew` `ps` |

Per-command reduction figures and behavior: `references/commands.md`.

Three generic wrappers cover anything not in that table:

```bash
rtk test <any test command>   # failures only
rtk err <any command>         # errors only
rtk summary <long command>    # heuristic summary
```

## What NOT to Prefix

- **Anything already starting with `rtk`** — never `rtk rtk git status`.
- **Shell builtins and file mutations**: `cd` `echo` `printf` `export` `source` `mkdir` `rm` `mv` `cp` `chmod` `chown` `touch` `which` `type` `test` `kill` `sleep` `set`/`unset` `pwd` `true`/`false`.
- **Pipeline text filters**: `sed` `awk` `sort` `uniq` `cut` `tr`.
- **Inline interpreters**: `python -c` `node -e` `ruby -e`.
- **Shell control flow**: `if` `for` `while` `case` `do` `then` `else`.
- **`cat`/`head`/`tail` with a redirect** (`cat x > y`) — a write, not a read. Leave it raw.

For a compound command, prefix each supported segment — this is exactly what rtk's own rewriter does with `&&` chains:

```bash
rtk git add . && rtk git commit -m "fix" && rtk git push
```

## When Unsure, Ask rtk

`rtk rewrite` is the single source of truth for what gets rewritten:

```bash
rtk rewrite "cargo test --nocapture"   # prints: rtk cargo test --nocapture
```

Exit codes: `0` = printed rewrite applies · `1` = nothing printed, no rewrite · `2` = deny rule matched · `3` = rewrite applies but needs approval. Exit **3 is the normal case** with no allow-rules configured; treat 0 and 3 alike — both print a usable command.

## Reading Files and Searching

**`rtk read` does not filter unless you ask it to.** The default level is `none`, which returns the file byte-for-byte. The reduction comes from `-l`:

```bash
rtk read src/main.rs                  # level none (default): FULL content, 0% saved
rtk read src/main.rs -l minimal       # comments and blank lines stripped (~20%)
rtk read src/main.rs -l aggressive    # signatures only, bodies stripped (~80%)
rtk read file.rs --max-lines 50       # first 50 lines
rtk read app.log --tail-lines 20      # last 20 lines
rtk smart src/main.rs                 # 2-line heuristic summary (~99%)
rtk grep "TODO" src/                  # grouped by file, long lines truncated
rtk find "*.rs" src/                  # compact tree of results
```

Use `-l aggressive` or `rtk smart` to orient in an unfamiliar file, then read the region exactly when you need to edit it.

A built-in file-read/grep/glob **tool** does not pass through rtk; only shell commands do. When a large file or broad search would otherwise dump a lot of text, reach for `rtk read` / `rtk grep` in the shell.

## Bypassing the Filter

```bash
rtk proxy <cmd>       # run raw, no filtering, still tracked in analytics
RTK_DISABLED=1 <cmd>  # skip the filter for this one invocation
```

On failure rtk saves the full unfiltered output and prints the path — read that log instead of re-running:

```
FAILED: 2/15 tests
[full output: ~/.local/share/rtk/tee/1707753600_cargo_test.log]
```

## Configuration

`~/.config/rtk/config.toml` (macOS: `~/Library/Application Support/rtk/config.toml`):

```toml
[hooks]
exclude_commands = ["curl", "playwright"]   # never rewrite these

[tee]
enabled = true
mode = "failures"      # "failures" | "always" | "never"
```

## Reporting Savings

```bash
rtk gain                    # summary
rtk gain --graph            # ASCII graph, last 30 days
rtk gain --daily            # day-by-day
rtk gain --all --format json
rtk discover                # commands that ran raw but had an rtk equivalent
rtk session                 # rtk adoption across recent sessions
```

## Global Flags

```
--ultra-compact   # ASCII icons, inline format, further reduction
--skip-env        # sets SKIP_ENV_VALIDATION=1 for Next.js/tsc/lint/prisma
-v / -vv / -vvv   # show what rtk is filtering, on stderr
```

## Pitfalls

- **`rtk read` with no `-l` saves nothing.** Verified on a 173,652-byte file: default returned all 173,652 bytes; `-l aggressive` returned 35,461.
- **`-v` is only recognized before the subcommand** — `rtk -vvv git status`, not `rtk git status -vvv`. rtk's own docs show the broken form.
- **There is no `-u` short form** for `--ultra-compact` in v0.45.0, despite the README. Write it out.
- **Exit 1 from `rtk rewrite` means "the hook won't rewrite this", not "rtk can't handle it".** `npm test` and `brew list` both exit 1, yet `rtk npm test` and `rtk brew list` run fine — unknown subcommands fall through to the real binary, so prefixing is safe even where no filter exists.
- **`rtk grep` drops line numbers** even when the raw command would print them.
- **Filtering is lossy by design.** Bypass it when you need verbatim output (parsing, diffing exact text, quoting an error message), when filtered output looks self-contradictory, or when a pass/fail signal is missing from the summary.
- **On small outputs rtk can be net-negative** — filtering has fixed overhead, so a two-line diff may come back slightly larger. The savings are real on large outputs.
- **`rtk gain` measures bash output bytes removed, not money saved.** Token counts are estimated as `bytes / 4` with no tokenizer: percentages are sound, absolute token numbers approximate. Report them as output reduction, never as bill reduction.

## The ai-engineering seam

1. rtk is an external binary: ai-eng OFFERS it in init — it prints `brew install rtk · rtk init` (with the pinned version and the license) and the human runs it. It is never executed from ai-eng and never bundled; the rewrite hook is planted per surface.
2. This skill is the thin routing layer over that binary: it routes shell commands through rtk and cuts output tokens by 60-90%. Lowering the cost of reading the output lowers the cost of verifying.

Source: rtk (autometa / Hermes Agent), MIT — https://github.com/rtk-ai/rtk ·
flags and behavior verified against the binary v0.45.0.
