# Verify: HX-09 Runtime Core Extraction Track B

## Focused Proof

```bash
.venv/bin/python -m pytest tests/unit/test_reconciler.py tests/unit/installer/test_pipeline.py tests/unit/test_doctor_service.py tests/unit/test_updater.py -q
```

Result: `51 passed in 0.21s`.

## Adjacent Updater And Install Proof

```bash
.venv/bin/python -m pytest tests/unit/updater/test_update_provider_filtering.py tests/unit/updater/test_update_orphan_detection.py tests/e2e/test_install_pipeline.py tests/e2e/test_install_existing.py -q
```

Result: `25 passed in 65.28s`.

After Sonar-driven cleanup, the focused plus adjacent slice was re-run together:

```bash
.venv/bin/python -m pytest tests/unit/test_reconciler.py tests/unit/installer/test_pipeline.py tests/unit/test_doctor_service.py tests/unit/test_updater.py tests/unit/updater/test_update_provider_filtering.py tests/unit/updater/test_update_orphan_detection.py tests/e2e/test_install_pipeline.py tests/e2e/test_install_existing.py -q
```

Result: `76 passed in 58.96s`.

## Broader Phase Compatibility Proof

```bash
.venv/bin/python -m pytest tests/unit/test_doctor.py tests/unit/test_doctor_models.py tests/unit/test_doctor_phase_parity.py tests/unit/test_doctor_phases_detect.py tests/unit/test_doctor_phases_governance.py tests/unit/test_doctor_phases_hooks.py tests/unit/test_doctor_phases_ide_config.py tests/unit/test_doctor_phases_state.py tests/unit/test_doctor_phases_tools.py tests/unit/test_doctor_phase_tools.py tests/unit/test_installer_phase_tools.py tests/unit/test_installer_tools.py -q
```

Result: `245 passed in 10.53s`.

After cleanup, the same broader phase compatibility slice was re-run.

Result: `245 passed in 4.04s`.

## Static Checks

```bash
.venv/bin/python -m ruff check src/ai_engineering/reconciler.py src/ai_engineering/installer/phases/pipeline.py src/ai_engineering/doctor/service.py src/ai_engineering/updater/service.py tests/unit/test_reconciler.py tests/unit/installer/test_pipeline.py tests/unit/test_doctor_service.py tests/unit/test_updater.py --select I,F,E9
```

Result: `All checks passed!`.

Editor diagnostics reported no errors for touched source and test files.

## SonarQube For IDE

Touched-file analysis returned `findingsCount: 0`.

## Structural Validation

```bash
.venv/bin/python -m json.tool .ai-engineering/specs/task-ledger.json >/dev/null
```

Result: passed with no output.

```bash
.venv/bin/python -m ai_engineering.cli validate -c cross-reference -c file-existence
```

Result: `Validate [PASS]` with `Categories 7/7 passed`.

## Coverage Notes

- Reconciler preview stops before apply and verify.
- Reconciler apply runs postcondition verification and finalize on success.
- Apply exceptions and verification failures call rollback.
- Installer dry-run remains plan-only.
- Doctor fix dry-run continues to call legacy phase fixers with `dry_run=True` for compatibility.
- Updater dry-run no longer migrates legacy hooks.
- Updater apply failure after orphan deletion restores deleted orphan files.
- Existing updater provider filtering, orphan deletion, update rollback, install pipeline e2e, doctor phase, and installer phase tests remain green.

## Final Deferred Review

Completed in the final end-of-implementation review pass requested by the user. Governance review reconciled preview purity, rollback boundaries, and the ownership split with `HX-04`, `HX-05`, and `HX-10`; no implementation tasks reopened.