---
title: spec-184 — Field-level manifest ownership + framework version-drift UX — execution plan
spec: spec-184
status: draft
pipeline: full
execution_route:
  version: 1
  spec: spec-184
  executor: autopilot
  automation: assisted
  concern_count: 4
  estimated_files: 18
  reason: "Four coupled concerns (field-level ownership resolver, update→framework_version advancement, drift detector, 4 differentiated UX surfaces) across ~18 files, spanning a gated 2-phase boundary (foundation gates UX). Multi-concern + broad surface → autopilot with wave decomposition."
  safe_next_command: "/ai-autopilot"
---

## Design

Design-intent is PRE-SETTLED in brainstorm (D-184-04 ◈-vs-⟳ differentiation,
D-184-05 surfaces, D-184-06 writer). `--skip-design` rationale: the two-mark
two-verb model, the surface set (status row / doctor CheckResult / ai-start
block / advisory banner), and the writer choice were all decided and
operator-approved during /ai-brainstorm.
Phase-2 visual contract:
- **◈** = PyPI package upgrade → `ai-eng version upgrade` (unchanged, existing).
- **⟳** = project files update → `ai-eng update` (NEW drift signal).
- Label/row TEXT is the primary signal; mark + colour reinforce only (a11y).
- Advise-only: never blocks, never changes exit code. stderr-only banner,
  `--json`-suppressed, fail-open.

## Architecture

Pattern: **layered extension + reuse** (no new architectural layer). Reused seams:
- `control_plane.manifest_field_roles` (`framework_defaults.py:41-65`) — the field-role source of truth for the ownership resolver.
- `update_manifest_field` (`config/loader.py:106-159`) — ruamel comment-preserving field writer for the `framework_version` advance.
- `is_newer` / `packaging.version` (`version/compare.py:16-25`) — PEP 440 comparison for the drift check.
- `_stack_drift_middleware` (`cli_factory.py:292-351`) — the WARNING/detail/Recovery banner shape + exempt set to mirror.
- Existing renderers: `_render_config.py` (status), `doctor/phases/detect.py:173` `_check_stack_drift` (doctor), `session_bootstrap._version_status` + `⚠ Compatibility` (ai-start), `cli_ui` THEME/marks.

Gate boundary: **Phase 1 (A–C) MUST be green before Phase 2 (D) starts** — the
UX reads the drift detector and the reliably-advanced datum.

---

## Phase A — Field-level manifest ownership resolver (Goal 1)

- [ ] T-A1 — RED: resolver classifies manifest keys FRAMEWORK vs TEAM from manifest_field_roles
- Agent: build
- Files: tests/unit/config/test_manifest_field_ownership.py (new)
- Principles applied: §10.5 TDD, §10.3 SOLID
- Patch (deterministic): none — assert a new `is_framework_owned_manifest_key(key)` returns True for `framework_version`/`schema_version`/`skills`/`agents` (descriptive_metadata + generated_projection) and False for `providers`/`surfaces`/`quality`/`gates`/`telemetry` (canonical_input). Assert an unknown key defaults to TEAM-owned (fail-safe: framework never writes an unclassified key).
- Gate: pytest tests/unit/config/test_manifest_field_ownership.py (RED)

- [ ] T-A2 — GREEN: implement the ownership resolver over manifest_field_roles
- Agent: build
- Files: src/ai_engineering/config/framework_defaults.py:41-65 (read manifest_field_roles) or a sibling src/ai_engineering/config/manifest_ownership.py (new resolver)
- Principles applied: §10.4 DRY (single source = the existing role map), §10.1 KISS
- Patch (deterministic): none (synthesis) — `is_framework_owned_manifest_key(key)` returns True iff key ∈ (descriptive_metadata ∪ generated_projection); everything else (incl. unknown) → False. v1 only needs framework_version, but the resolver reads the full framework-owned set so a later spec can advance more without re-plumbing.
- Gate: pytest tests/unit/config/test_manifest_field_ownership.py (GREEN)

## Phase B — `ai-eng update` advances framework_version (Goals 2–4)

- [ ] T-B1 — RED: update advances framework_version, preserves user keys + comments, inserts if missing
- Agent: build
- Files: tests/integration/test_update_advances_framework_version.py (new)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — fixture: a project manifest with stale `framework_version: "0.10.0"`, user keys (providers/surfaces/quality) + comments. Run `update`. Assert: (a) `framework_version` == installed `__version__`; (b) every user key byte-unchanged; (c) comments/blank lines/key order preserved; (d) a slim manifest omitting `framework_version` gets it INSERTED, not crashed; (e) the whole path is fail-open (a locked/broken manifest logs and does not fail update).
- Gate: pytest tests/integration/test_update_advances_framework_version.py (RED)

- [ ] T-B2 — GREEN: wire the update apply phase to advance framework_version
- Agent: build
- Files: src/ai_engineering/updater/service.py (apply phase, after file reconcile ~:504-520) or src/ai_engineering/cli_commands/core.py:1102-1139 (update_cmd → run_update_workflow); reuse src/ai_engineering/config/loader.py update_manifest_field
- Principles applied: §10.4 DRY (reuse update_manifest_field, not a 3rd writer — D-184-06), §10.2 YAGNI (only framework_version)
- Patch (deterministic): none (synthesis) — post-reconcile step: resolve installed `__version__`; if `is_framework_owned_manifest_key("framework_version")`, call `update_manifest_field(root, "framework_version", __version__)` with a setdefault/insert fallback. Restrict the write STRICTLY to the descriptive_metadata allowlist so no canonical_input key is touched. Bypass the whole-file DENY for this one key ONLY (the file stays DENY for whole-file replacement). Wrap in try/except → fail-open.
- Gate: pytest tests/integration/test_update_advances_framework_version.py (GREEN); existing updater suite green (no regression to DENY skip for the rest of the file)

## Phase C — Drift detector (Goal 5) [gates Phase 2]

- [ ] T-C1 — RED: drift detector compares project framework_version vs installed __version__
- Agent: build
- Files: tests/unit/version/test_framework_drift.py (new)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — assert a new `detect_framework_drift(root)` returns: BEHIND when manifest `framework_version` < installed `__version__` (PEP 440), UP_TO_DATE when equal, and a safe/None result when the manifest or version is unreadable (fail-open). Reuse `is_newer`.
- Gate: pytest tests/unit/version/test_framework_drift.py (RED)

- [ ] T-C2 — GREEN: implement the drift detector
- Agent: build
- Files: src/ai_engineering/version/framework_drift.py (new) reusing version/compare.py is_newer + config manifest loader
- Principles applied: §10.4 DRY (reuse is_newer), §10.7 Clean Code
- Patch (deterministic): none (synthesis) — read `manifest.framework_version` (applied) + `__version__` (installed); return a small dataclass {applied, installed, state}. Pure, fail-open, zero network (this is the LOCAL axis, not PyPI).
- Gate: pytest tests/unit/version/test_framework_drift.py (GREEN)

## Phase D — Differentiated UX surfaces (Goals 6–8) [GATED on A–C green]

- [ ] T-D1 — GREEN: add the ⟳ drift mark/token (distinct from ◈)
- Agent: build
- Files: src/ai_engineering/cli_ui.py (mark constant + optional THEME accent, near the ◈ update-notice constants ~:377-465)
- Principles applied: §10.1 KISS, D-184-04
- Patch (deterministic): none — add a `⟳` drift mark constant; reuse an existing THEME colour (e.g. warning/muted) — do NOT reuse the ◈ brand-teal so the two axes read distinctly. Plain-ASCII fallback for non-TTY/NO_COLOR.
- Gate: pytest tests/unit -k cli_ui green

- [ ] T-D2 — RED+GREEN: `ai-eng status` Framework row
- Agent: build
- Files: tests/unit/cli/test_status_framework_row.py (new); src/ai_engineering/cli_commands/_render_config.py:33-61 (add a Framework section) + status.py
- Principles applied: §10.5 TDD, D-184-05
- Patch (deterministic): none (synthesis) — RED: assert status output shows a Framework row `project {applied} · installed {installed}` and, when behind, `⟳ behind — run ai-eng update`; when equal, up-to-date; JSON mode includes the fields, no banner. GREEN: render it from `detect_framework_drift`.
- Gate: pytest tests/unit/cli/test_status_framework_row.py green

- [ ] T-D3 — RED+GREEN: `ai-eng doctor` framework-drift CheckResult
- Agent: build
- Files: tests/unit/cli/test_doctor_framework_drift.py (new); src/ai_engineering/doctor/phases/detect.py:173 (sibling to _check_stack_drift) + doctor/runtime as needed
- Principles applied: §10.5 TDD, §10.3 SOLID (mirror the stack-drift check shape)
- Patch (deterministic): none (synthesis) — a `framework-drift` CheckResult: WARN (not FAIL — advise-only, D-184-03) when behind, PASS when current; message names `ai-eng update`; `--fix` runs update. Exit code unchanged by this check.
- Gate: pytest tests/unit/cli/test_doctor_framework_drift.py green

- [ ] T-D4 — RED+GREEN: `/ai-start` dashboard ⚠ Framework drift block
- Agent: build
- Files: tests/unit/... session_bootstrap drift test (new); the session-bootstrap dashboard renderer (`session_bootstrap._version_status` / `_render_markdown`, mirror the `⚠ Compatibility` block)
- Principles applied: §10.5 TDD, D-184-05
- Patch (deterministic): none (synthesis) — conditional `⚠ Framework drift — project on {applied}, ai-eng {installed} · run \`ai-eng update\`` block, shown only when behind; distinct from the existing `◈ … version upgrade` line.
- Gate: pytest for the session-bootstrap dashboard green

- [ ] T-D5 — RED+GREEN: advisory drift banner (mirrors stack-drift shape, gated)
- Agent: build
- Files: tests/unit/test_framework_drift_banner.py (new); src/ai_engineering/cli_factory.py:292-351 (a sibling to _stack_drift_middleware) + reuse the exempt set
- Principles applied: §10.5 TDD, D-184-03 (advise-only), D-184-06 (gating)
- Patch (deterministic): none (synthesis) — stderr banner `WARNING: framework drift detected / Project applied: {a} / Installed: {i} / Recovery: ai-eng update`. Advise-only (never blocks / never changes exit). Exempt on the same automation/hot-path set as the PyPI notice + on `update`/`doctor`/`version` themselves; suppressed in `--json`; throttled so it does not spam. Composes with (does not stack noisily against) the ◈ PyPI notice.
- Gate: pytest tests/unit/test_framework_drift_banner.py green; assert NO block / exit-code change; assert absent in --json + on exempt commands

## Final gate (autopilot Phase 5)

- [ ] T-F1 — Full verify + review + guard on the complete changeset
- Agent: verify
- Files: (whole diff)
- Principles applied: §10.6 SDD, §10.7 Clean Code
- Patch (deterministic): none
- Gate: full `pytest`, `ai-eng gate pre-push`, `ai-eng check` green; prove user manifest keys/comments untouched by an update; prove advise-only (no exit-code/block change); prove ◈ (PyPI) and ⟳ (drift) render distinctly and both suppressed in `--json`
