# Verify HX-03 T-4.2 Generated Mirror Provenance Validation

## Focused Validation

- `uv run pytest tests/unit/test_validator.py -k 'CopilotSkillsMirror or CodexSkillsMirror or CodexAgentsMirror or CopilotAgentsMirror or GeneratedMirrorProvenance'`
  - `12 passed, 126 deselected`

## Broader Mirror Validation

- `uv run pytest tests/unit/test_validator.py -k 'Mirror'`
  - `24 passed, 114 deselected`

## Real Repo Validation

- `uv run ai-eng validate -c mirror-sync`
  - `PASS`
  - `generated-mirror-provenance: Validated provenance in 444 generated mirror files`

## Notes

- The first real-repo run exposed a local classification bug where Codex and Gemini `internal/*.md` specialist mirrors were temporarily treated as public agents; tightening the public-agent glob to `ai-*.md` resolved that without broadening the rule.
- A second real-repo run exposed Copilot `canonical_source` derivation for filenames that already include `ai-`; normalizing that derivation closed the last false positive and left `mirror_sync` fully green again.