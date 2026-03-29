---
id: sub-006
parent: spec-087
title: "Test Suite Updates"
status: planning
files:
  - tests/unit/test_sync_mirrors.py, tests/unit/test_validator.py, tests/unit/installer/test_autodetect.py, tests/integration/test_install_matrix.py
depends_on:
  - sub-002, sub-003, sub-005
---

# Sub-Spec 006: Test Suite Updates

## Scope

Update all test files referencing .agents/ to .codex/. test_sync_mirrors.py: path assertions (lines 190, 417, 438, 510). test_validator.py: rename TestAgents* to TestCodex* (lines 765-815). test_autodetect.py: add .codex/ detection test. test_install_matrix.py: update expected dirs.

## Exploration
[EMPTY -- populated by Phase 2]
