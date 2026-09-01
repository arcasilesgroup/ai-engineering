# .ai-engineering/overrides.toml — the ONLY mechanism to turn a guard off (§09.1).
# Every exception needs a reason and an end date: they travel to the receipt, the
# commit-msg hook requires the reason in the footer, and doctor shows them as WARN
# until they expire.

# [[guard.off]]
# name   = "loop"
# reason = "batch migration: 400 identical failures expected this week"
# until  = "2026-09-05"
