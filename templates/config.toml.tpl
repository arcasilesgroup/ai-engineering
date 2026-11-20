# .ai-engineering/config.toml — what CANNOT be deduced from code.
# This file is the right place for your thresholds and pins: edit it by hand or
# run `ai-eng config` for surfaces. The chain reads it; it never edits it.
# Skills: every shipped skill and its resources install by default; there is no
# pack selection. A legacy [canon].packs value is ignored and never rewritten.

[surfaces]
# Which agent surfaces (IDEs/CLIs) this project is governed on. Every client uses
# the same definitions from ai-eng — no per-IDE forks. Options: claude-code, oh-my-pi, opencode, cursor, codex, copilot-cli, pi, zed.
# `ai-eng config` rewrites this list and installs/removes each surface's adapter files.
enabled = [{{surfaces}}]

[ci]
# Where this project's merge gate runs: github-actions | azure-pipelines | none.
# github-actions → .github/workflows/ai-eng-check.yml
# azure-pipelines → .azure-pipelines/ai-eng-check.yml
# none → no CI file; bring your own gate. Change it here, then run `ai-eng update`:
# the new provider's file is written and the old one is removed.
provider = "{{ci}}"

[guards]
# Loop guard thresholds: identical-call repetition and failure streaks.
loop_window = 6    # remembered calls
loop_repeats = 3   # same exact call → deny
loop_failures = 5  # same signature failing → deny

# Command-scope policy (ported from bash-guard): four octal digits, left to
# right system/external/network/workspace, bits 4:read 2:write 1:execute.
# Default 4667 — workspace everything, network read+write, external read+write,
# system read (system write and execute stay denied). An invalid value fails
# closed as 0000.
# policy_mode = "4667"

# Local rules — declarative injection rules evaluated by the injection guard.
# Each rule matches against a scope (all_text, tool_name, or raw_json) with
# contains or equals semantics. Actions: "block" (deny immediately) or "review"
# (log but allow). Risk 0–1 determines priority (higher = checked first).
# Rules are sorted: block before review, highest risk first.
# Example:
# [[guards.local_rules]]
# id = "no-curl-bash"
# name = "No curl pipe to shell"
# enabled = true
# scope = "all_text"
# match = "contains"
# pattern = "curl.*\\|.*(bash|sh|zsh)"
# action = "block"
# risk = 0.9

# Git — optional; leave commented out to let ai-eng detect it.
# base: the branch your work merges into. Without it the base is the default branch
# of the current branch's upstream remote (or origin), read from local refs; when
# nothing answers, or it equals the current branch, ai-eng asks.
# worktrees_dir: where `ai-eng worktree new` creates worktrees.
# [git]
# base = "develop"
# worktrees_dir = "../<repo>.worktrees"

# Lanes (ai-eng work): how many may be active at once, how many days without a commit,
# a PR or a park make a lane an orphan, and how many minutes without a write free a
# folder another session was writing in. Uncomment to change.
# [work]
# max_active = 3
# orphan_days = 3
# lease_minutes = 15

[gc]
# What `ai-eng doctor --gc` keeps. The artifact folders are research/, reports/,
# design/audits/, security/ and workflow/; a file there goes only once git holds it,
# it is older than older_than, and DECISIONS.md, NOTICE or the layer rules do not cite it.
max_files = 25        # per artifact folder: more than this is a WARN, never a FAIL
receipts_ttl = "30d"  # receipts: aggregate then delete
# older_than = "90d"  # an artifact folder's file is collected past this age
# keep_runs = 5       # the newest security runs, always kept

# Uncomment to turn off the new-version notice (AI_ENG_NO_UPDATE_NOTICES=1 does the same).
# [notices]
# enabled = false
