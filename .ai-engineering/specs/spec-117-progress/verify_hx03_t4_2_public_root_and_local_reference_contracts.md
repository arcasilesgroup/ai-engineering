# Verify HX-03 T-4.2 Public Root And Local Reference Contracts

## Focused Validation

- `uv run pytest tests/unit/test_validator.py -k 'PublicSkillRootContract or PublicAgentRootContract or NonClaudeLocalReferenceLeaks or GeneratedMirrorProvenance'`
  - `5 passed, 136 deselected`

## Materialization

- `uv run ai-eng sync`
  - `PASS`

## Real Repo Validation

- `uv run ai-eng validate -c mirror-sync`
  - `PASS`
  - `non-claude-local-reference-contract: Validated non-Claude local references in 978 generated files`
  - `public-skill-root-contract: Validated governed public skill roots in 6 surfaces`
  - `public-agent-root-contract: Validated governed public agent roots in 6 surfaces`

## Broader Mirror Suite

- `uv run pytest tests/unit/test_sync_mirrors.py tests/unit/test_validator.py -k 'Mirror or LocalReference or PublicAgentRootContract or GeneratedMirrorProvenance'`
  - `93 passed, 114 deselected`