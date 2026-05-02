# Build HX-03 T-4.2 Public Root And Local Reference Contracts

## Scope

- Finish the remaining negative-validation half of `HX-03 T-4.2` by rejecting ungoverned public root entries and non-Claude `.claude/skills|agents` leaks.

## Changes

- Added `public-agent-root-contract` so provider public `agents/` roots may contain only governed public agent files plus the provider-local `internal/` specialist namespace.
- Added `public-skill-root-contract` so provider public `skills/` roots may contain only governed `ai-*` and `_shared` directories.
- Added `non-claude-local-reference-contract` so non-Claude mirrors now fail if `.claude/skills/` or `.claude/agents/` appear outside the allowed `canonical_source` provenance line.
- Updated `scripts/sync_command_mirrors.py` to translate `skills/*/scripts/*` for Codex, Gemini, and Copilot mirrors instead of copying those script files verbatim.
- Regenerated the repo mirrors so the `ai-create/scripts/scaffold-skill.sh` provider copies no longer leak `.claude/skills/...`.