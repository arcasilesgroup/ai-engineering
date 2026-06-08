---
title: "Plan — Runbook header translations: template parity + cross-IDE"
spec: runbook-template-parity
status: approved
pipeline: standard
architecture_pattern: ad-hoc
execution_route:
  version: 1
  spec: runbook-template-parity
  executor: build
  automation: assisted
  concern_count: 1
  estimated_files: 15
  reason: "Single concern (runbook template parity) — 14 mechanical template translations + 1 parity-guard test. Low risk, no cross-module coupling, no design surface. Routes to /ai-build, not /ai-autopilot."
  safe_next_command: "/ai-build"
---

# Plan — Runbook header translations: template parity + cross-IDE

Implements spec `runbook-template-parity` (sidecar `spec-169`). Completes
PR #585 by translating the 14 template runbook twins and adding a byte-parity
guard.

## Architecture

**Pattern: ad-hoc.** Mechanical content parity + one test. No new module, no
interface change, no data flow. The only structural addition is a CI assertion
in an existing test module that already imports both `RUNBOOK_ROOT` and
`TEMPLATE_ROOT`.

## Base branch (delivery)

Work targets the PR #585 fork branch `eramos/ai-engineering:feat_translations`
(`maintainerCanModify: true`), where the 14 **live** runbooks are already
English. `/ai-build` must base its worktree on that branch (not `main`), so the
parity guard (T-1) goes RED before T-2 (live English vs template Spanish) and
GREEN after. Delivery is a push back onto that same branch — one PR, original
author retained (spec D-runbook-template-parity-03).

## Phase 1 — Parity guard (RED)

- [x] T-1 — Add repo↔template runbook byte-parity test
- Agent: build
- Files: tests/unit/test_runbook_contracts.py
- Principles applied: §10.5 TDD (RED before GREEN), §10.7 Clean Code (reuse existing roots/list)
- Patch (deterministic): append a test that fails loud on any twin mismatch, reusing the module's existing `RUNBOOK_ROOT`, `TEMPLATE_ROOT`, and `ALL_RUNBOOKS`.

```diff
--- a/tests/unit/test_runbook_contracts.py
+++ b/tests/unit/test_runbook_contracts.py
@@
+@pytest.mark.parametrize("name", ALL_RUNBOOKS)
+def test_runbook_template_byte_parity(name: str) -> None:
+    """Each live runbook must be byte-identical to its install-template twin.
+
+    Guards the silent drift fixed in PR #585: a live edit (e.g. header
+    translation) that never reached ``src/ai_engineering/templates/`` would
+    ship Spanish headers to downstream installs. (spec runbook-template-parity
+    D-runbook-template-parity-02.)
+    """
+    live = RUNBOOK_ROOT / f"{name}.md"
+    template = TEMPLATE_ROOT / f"{name}.md"
+    assert live.read_bytes() == template.read_bytes(), (
+        f"runbook drift: {name}.md differs between "
+        f".ai-engineering/runbooks/ and the install template — "
+        f"re-sync the template twin."
+    )
```

- Gate: `.venv/bin/python -m pytest tests/unit/test_runbook_contracts.py -k byte_parity` — RED on the fork branch (live English, template Spanish) before T-2.

## Phase 2 — Template translation (GREEN)

- [x] T-2 — Translate the 3 headers in all 14 template runbook twins
- Agent: build
- Files: src/ai_engineering/templates/.ai-engineering/runbooks/*.md (14 files)
- Principles applied: §10.4 DRY (single canonical content, twin re-synced), §10.5 TDD (GREEN)
- Patch (deterministic): apply the identical substitution PR #585 made to the live copies. Verified: exactly 3 header swaps per file, all 14 files carry all 3 headers, no other Spanish remains.

```bash
sed -i '' \
  -e 's/^## Objetivo$/## Objective/' \
  -e 's/^## Precondiciones$/## Prerequisites/' \
  -e 's/^## Procedimiento$/## Procedure/' \
  src/ai_engineering/templates/.ai-engineering/runbooks/*.md
```

- Gate: `.venv/bin/python -m pytest tests/unit/test_runbook_contracts.py` — all GREEN, including the new parity test for every one of the 14 runbooks.

## Phase 3 — Verify

- [x] T-3 — Full runbook-contract suite + lint
- Agent: verify
- Files: tests/unit/test_runbook_contracts.py, src/ai_engineering/templates/.ai-engineering/runbooks/*.md
- Principles applied: §10.7 Clean Code (no residual drift), §10.5 TDD (suite green)
- Gate: `.venv/bin/python -m pytest tests/unit/test_runbook_contracts.py` AND `ruff check tests/unit/test_runbook_contracts.py` AND a final `diff` sweep proving all 14 live↔template pairs identical. No `## Objetivo|Precondiciones|Procedimiento` remain anywhere under `src/ai_engineering/templates/.ai-engineering/runbooks/`.

## Gate criteria (plan-level)

- New parity test goes RED before T-2, GREEN after — proves the guard works.
- All 14 template twins byte-identical to live copies post-T-2.
- No Spanish headers remain in template runbooks.
- `ruff check` clean on the touched test file.
- No CHANGELOG entry (not user-facing runtime behavior; matches PR #585 scope).

## Quality Outcome

- **T-1 RED → GREEN proven:** parity test failed on all 14 twins before
  translation (live English vs template Spanish), passes after.
- **Extra bug caught + fixed (in scope):** PR #585 translated the runbook
  headers but left `REQUIRED_SECTIONS` in `test_runbook_contracts.py` pointing
  at the old Spanish names (`## Objetivo`, `## Precondiciones`,
  `## Procedimiento`), so `test_runbook_contract_schema` was already RED on the
  PR branch. Updated the constant to the English names. Also fixed an inline
  cross-reference `(see Precondiciones)` → `(see Prerequisites)` in the
  `performance.md` template twin to match the live copy.
- **Suites:** `tests/unit/test_runbook_contracts.py` (73) +
  `test_template_parity.py` + `test_sync_mirrors.py` → **132 passed**.
- **Lint:** `ruff check tests/unit/test_runbook_contracts.py` clean.
- **Sweep:** zero `Objetivo|Precondiciones|Procedimiento` remaining under the
  template runbooks; all 14 live↔template pairs byte-identical.
- **Changed set:** 14 template runbooks + 1 test file — matches plan scope, no
  drive-by edits.

## Out of scope (from spec Non-Goals)

- No body/frontmatter/other-file translation.
- No per-IDE mirroring (`.codex/`, `.github/`, `.agents/`).
- No parity guard for other template trees.
- No separate upstream branch or second PR.
