# Platform Support Audit — Report Template

Determine the TARGET_PLATFORM from `$ARGUMENTS`. If it is a single platform (`claude-code`, `github-copilot`, `gemini`, or `codex`), the Capability Matrix has **one data column** for that platform only. If it is `all`, use four columns. Never add columns for platforms outside the scope.

```
# Platform Support Audit — [TARGET_PLATFORM] — [DATE]

## Executive Summary
[Fill last — 2–3 sentences on overall posture and gap count]

## Capability Matrix
| Capability           | [Platform(s)] |
|---------------------|--------------|
| Instruction Surface  | ?            |
| Hooks Wired          | ?            |
| Skills Distributed   | ?            |
| Agents Distributed   | ?            |
| Skill Count Accurate | ?            |
| Agent Count Accurate | ?            |
| Installer Coverage   | ?            |

Replace each ? with: SUPPORTED · PARTIAL · UNSUPPORTED · NOT_APPLICABLE
— SUPPORTED: evidence found, count matches, no gaps
— PARTIAL: file exists but count wrong, hook exists but not wired, or mirror incomplete
— UNSUPPORTED: no evidence at expected path
— NOT_APPLICABLE: platform intentionally does not support this capability

## Platform Inventory
[Sub-section per platform in scope: files found, counts, verbatim paths]

## What Works ✅
[Each bullet cites a file path]

## What's Wrong ❌
[Each bullet cites a file path and assigns P0 / P1 / P2]

## Remediation
### P0 — Blocking (auto-fix or immediate action)
### P1 — High Priority (next session)
### P2 — Housekeeping (backlog)

## Auto-Fix Log
[Populated only if fixes were applied. Empty otherwise.]

## Final Verdict
| Platform | Verdict | Confidence |
|---------|---------|-----------|
| [in-scope platforms] | PRODUCTION_READY / DEGRADED / BROKEN | High / Med / Low |
```
