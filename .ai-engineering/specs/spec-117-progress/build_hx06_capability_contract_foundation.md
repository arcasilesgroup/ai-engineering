# Build Handoff: HX-06 Capability Contract Foundation

## Scope

- Added the canonical capability-card schema for first-class skills and agents.
- Added mutation classes, write-scope classes, tool-scope classes, topology roles, and provider compatibility status to the state models.
- Added `ai_engineering.state.capabilities` to derive capability cards from manifest metadata and validate task packets against capability authority.
- Extended `framework-capabilities.json` generation so capability cards are derived projection output, not peer authority.
- Wired `manifest-coherence` to validate capability-card coverage and active task-packet acceptance.

## Implemented Files

- `src/ai_engineering/state/models.py`
- `src/ai_engineering/state/capabilities.py`
- `src/ai_engineering/state/observability.py`
- `src/ai_engineering/validator/categories/manifest_coherence.py`
- `.ai-engineering/state/framework-capabilities.json`
- `tests/unit/test_capabilities.py`
- `tests/unit/test_framework_observability.py`
- `tests/unit/test_validator.py`

## Behavior

- Task packets are accepted or rejected by owner capability, mutation class, write-scope class, requested tool scope, and provider compatibility.
- Broad or unknown write scopes are advisory warnings instead of hard failures.
- Minimal manifests without generated capability cards skip task-packet acceptance with a warning for compatibility.
- Source repositories now check that every manifest skill and first-class agent has a generated capability card.

## Deferred Review Gates

- Formal guard review for topology role, provider degradation semantics, and artifact ownership remains deferred to the final review pass per user instruction.
- Internal specialist parity and prompt-surface drift checks remain open for the next HX-06 slice.