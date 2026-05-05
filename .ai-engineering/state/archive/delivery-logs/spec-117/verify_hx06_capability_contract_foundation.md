# Verification: HX-06 Capability Contract Foundation

## Passing Focused Evidence

- `15 passed`: `python -m pytest tests/unit/test_capabilities.py tests/unit/test_framework_observability.py tests/unit/test_validator.py::TestManifestCoherence::test_task_capability_acceptance_passes_for_build_source_write tests/unit/test_validator.py::TestManifestCoherence::test_task_capability_acceptance_rejects_illegal_source_writer -q`
- `ruff`: `python -m ruff check src/ai_engineering/state/models.py src/ai_engineering/state/capabilities.py src/ai_engineering/state/observability.py tests/unit/test_capabilities.py tests/unit/test_framework_observability.py`
- `ruff syntax/import`: `python -m ruff check --select I,F,E9 src/ai_engineering/validator/categories/manifest_coherence.py tests/unit/test_validator.py`
- Live `manifest-coherence` HX-06 checks:
  - `framework-capabilities-snapshot`: OK
  - `capability-card-contract`: OK
  - `task-capability-acceptance-validation`: OK

## Known Unrelated Residuals

- Full `tests/unit/test_validator.py` still has two unrelated pre-existing failures in specialist mirror generation and non-source instruction contract behavior.
- Live `manifest-coherence` remains overall failing from unrelated `control-plane-authority-contract` drift already observed before this HX-06 slice.
- Sonar/Pylance diagnostics still report pre-existing issues in `models.py` and `observability.py`; the new `capabilities.py`, `manifest_coherence.py`, and focused tests report no IDE errors.

## Result

The capability-card foundation is implemented, projected, and covered by focused deterministic checks. The remaining HX-06 work is prompt/internal topology parity, deferred guard review, and final end-to-end proof.