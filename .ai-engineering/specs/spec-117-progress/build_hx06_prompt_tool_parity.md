# Build Handoff: HX-06 Prompt And Tool Parity

## Scope

- Added generator-level coverage that Copilot agent frontmatter tool declarations stay in sync with `AGENT_METADATA`.
- Verified delegated agents receive the `agent` tool and matching `agents` frontmatter, while leaf agents do not expose delegation metadata.

## Implemented Files

- `tests/unit/test_sync_mirrors.py`
- `.ai-engineering/specs/plan-117-hx-06-multi-agent-capability-contracts.md`

## Result

Public Copilot agent prompt/tool metadata is now pinned to the metadata source of truth rather than relying on prompt prose drift.