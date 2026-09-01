# .ai-engineering/config.toml — what CANNOT be deduced from code (§08).
# This file is the right place for your thresholds and pins: edit it by hand or
# run `ai-eng config` for surfaces. The chain reads it; it never edits it.

[surfaces]
# Which agent surfaces (IDEs/CLIs) this project is governed on. Every client uses
# the same definitions from ai-eng — no per-IDE forks. Options: claude-code,
# oh-my-pi, opencode, cursor, codex, copilot, pi-zed. `ai-eng config` rewrites
# this list and plants/removes each surface's adapter files.
enabled = [{{surfaces}}]

[models]
# The model pin (§9.4): one tier name per kind of work. Cheap for verifying,
# expensive for judging — never the reverse. Values are whatever your surfaces
# resolve natively; ai-eng never calls a model, it only injects this line.
decide  = "claude-fable-5"   # architecture, judgment, security review — expensive is fine
execute = "gpt-5.6-sol"      # end-to-end implementation, mechanical reviews
verify  = "gpt-5.6-luna"     # binary PASS/FAIL checks — cheap

[guards]
# Loop guard thresholds: identical-call repetition and failure streaks (§10).
loop_window = 6    # remembered calls
loop_repeats = 3   # same exact call → deny
loop_failures = 5  # same signature failing → deny

[gc]
# Growth caps for the NNN folders (research/, audits/, security/, reports/,
# receipts/). WARN thresholds, not FAIL — growth is hygiene, not security (§12.1).
max_files = 25        # per NNN folder — exceeding → WARN
older_than = "90d"    # minimum age to be a gc candidate
keep_runs = 5         # security/: the latest runs always stay alive
receipts_ttl = "30d"  # receipts: aggregate then delete

# notices = false   # opt out of the new-version notice (or AI_ENG_NO_UPDATE_NOTICES=1)
