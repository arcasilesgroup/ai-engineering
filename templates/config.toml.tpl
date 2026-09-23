# .ai-engineering/config.toml — what CANNOT be deduced from code (§08).
# This file is the right place for your thresholds and pins: edit it by hand or
# run `ai-eng config` for surfaces. The chain reads it; it never edits it.

[surfaces]
# Which agent surfaces (IDEs/CLIs) this project is governed on. Every client uses
# the same definitions from ai-eng — no per-IDE forks. Options: claude-code, oh-my-pi, opencode, cursor, codex, copilot, pi, zed.
# `ai-eng config` rewrites this list and installs/removes each surface's adapter files.
enabled = [{{surfaces}}]


[guards]
# Loop guard thresholds: identical-call repetition and failure streaks (§10).
loop_window = 6    # remembered calls
loop_repeats = 3   # same exact call → deny
loop_failures = 5  # same signature failing → deny

# Command-scope policy (ported from bash-guard): four octal digits, left to
# right system/external/network/workspace, bits 4:read 2:write 1:execute.
# Default 0467 — workspace everything, network read+write, external read,
# system nothing. An invalid value fails closed as 0000.
# policy_mode = "0467"

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

# Circuit breaker — protects against external service failures (Jev, MCP).
# After failure_threshold consecutive failures, the circuit opens and rejects
# immediately for reset_ms milliseconds, then tries once to recover.
# [guards.circuit_breaker]
# failure_threshold = 5   # consecutive failures before opening (default: 5)
# reset_ms = 30000        # milliseconds before half-open recovery (default: 30000)

[gc]
# Growth caps for the NNN folders (research/, audits/, security/, reports/,
# receipts/). WARN thresholds, not FAIL — growth is hygiene, not security (§12.1).
max_files = 25        # per NNN folder — exceeding → WARN
receipts_ttl = "30d"  # receipts: aggregate then delete


# notices = false   # opt out of the new-version notice (or AI_ENG_NO_UPDATE_NOTICES=1)
