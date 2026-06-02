---
status: approved
spec: spec-161
title: "Spec-lifecycle approval gate + integrity hardening"
execution_route:
  version: 1
  spec: spec-161
  executor: autopilot
  automation: supervised
  concern_count: 4
  estimated_files: 11
  reason: >
    Four independent concerns (numbering fix, reconcile gh-classify, two new
    lifecycle verbs + frontmatter mirror, three-skill gate wiring) plus a
    one-time data reconciliation, spanning spec_lifecycle.py, three SKILL.md
    surfaces (each with byte-parity mirrors), a data ledger, and tests.
    Multi-concern + >5 files routes to autopilot.
  safe_next_command: "/ai-autopilot"
pipeline: full
architecture_pattern: existing-hexagonal-one-file
design_routed: skipped (no UI surface; CLI + skill-doc + data work)
---

# Plan — spec-161 Spec-lifecycle approval gate + integrity hardening

Contract for execution. `/ai-plan` is planning-only — no code written here.
Pipeline `full`. Executor route `autopilot`. Architecture: extend the existing
hexagonal one-file layout of `spec_lifecycle.py` (Domain FSM already carries
`APPROVED`/`IN_PROGRESS`; we add Application verbs + one Infra frontmatter
mirror). Skill edits land on canonical `.claude/` surfaces, then
`ai-eng dev sync` regenerates `.codex/`, `.agents/`, `.github/` mirrors.

## Concern → Phase map

| Concern | Phases | Independent? |
|---|---|---|
| Bug 1 — archive-blind numbering | P1 | yes |
| Bug 2 — reconcile gh-classify | P2 | yes |
| approve/start verbs + frontmatter mirror | P3 | needs nothing |
| Skill gate wiring (plan/brainstorm/build) | P4 | depends P3 |
| Installer id data reconciliation | P5 | yes |
| Mirror sync + CHANGELOG + final gate | P6 | depends P1–P5 |

P1, P2, P5 are fully parallel. P3 is independent. P4 depends on P3 (verbs must
exist before skills call them). P6 is the convergence/seal phase.

---

## Phase 1 — Archive-blind numbering (#574 Bug 1)

- [x] **T-1** — RED: next-number must skip archived numbers
- Agent: build
- Files: `tests/unit/specs/test_spec_lifecycle.py`
- Principles applied: §10.5 TDD
- Patch (deterministic): none — new test fixture creating
  `specs/archive/spec-207-foo/` with live max 158, asserting
  `_next_spec_number(root) == 208`. Also assert a sidecar-only and ledger-only
  case still pass (no regression).
- Gate: `pytest tests/unit/specs/test_spec_lifecycle.py -k next_number` RED.

- [x] **T-2** — GREEN: union archive dir numbers into `_scan_spec_numbers`
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py:790-809`
- Principles applied: §10.4 DRY (reuse `_ARCHIVE_DIR_RE`/`_archive_dir`), §10.2 YAGNI
- Patch (deterministic):
```diff
@@ def _scan_spec_numbers(project_root: Path) -> set[int]:
     for hid in _history_spec_ids(project_root):
         match = _SPEC_NUMBER_RE.match(hid)
         if match:
             numbers.add(int(match.group(1)))
         elif hid.isdigit():
             numbers.add(int(hid))
+    archive = _archive_dir(project_root)
+    if archive.is_dir():
+        for child in archive.iterdir():
+            if not child.is_dir():
+                continue
+            amatch = _ARCHIVE_DIR_RE.match(child.name)
+            if amatch:
+                numbers.add(int(amatch.group(1)))
     return numbers
```
- Gate: T-1 test GREEN; `pytest tests/unit/specs/test_spec_lifecycle.py` all pass.

- [x] **T-3** — Update `_scan_spec_numbers` docstring (archive source now included)
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py:780-789`
- Principles applied: §10.7 Clean Code
- Patch (deterministic): none — prose: append a line documenting that
  `archive/spec-NNN-*` dir names are now a scan source (the docstring currently
  says only sidecars + ledger).
- Gate: docstring matches behavior; no test asserts the old text.

---

## Phase 2 — Reconcile gh-classify (#574 Bug 2)

- [x] **T-4** — RED: merged branch classified via gh even when local ref absent
- Agent: build
- Files: `tests/unit/specs/test_spec_lifecycle.py`
- Principles applied: §10.5 TDD
- Patch (deterministic): none — test monkeypatches the gh call to return a
  merged-PR row for a branch with NO local ref; asserts `reconcile_merged`
  marks the sidecar SHIPPED. Second case: gh returns nothing → falls back to
  `_branch_is_merged` (monkeypatched) → unmerged path preserved.
- Gate: `pytest -k reconcile_gh` RED.

- [x] **T-5** — GREEN: add gh PR-state classifier as primary merge signal
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py:915-942, 981-1017, 1069`
- Principles applied: §10.3 SOLID (single classify helper), §10.4 DRY (reuse gh-subprocess shape from `_resolve_merged_pr`)
- Patch (deterministic): none — judgment required. Add
  `_pr_merged_via_gh(project_root, branch) -> bool` running
  `gh pr list --head <branch> --state merged --json number`; ≥1 row ⇒ True;
  gh absent/err/empty ⇒ False (mirror `_resolve_merged_pr` fail-open). In
  `reconcile_merged` (L1069) classify as merged when
  `_pr_merged_via_gh(...) or _branch_is_merged(...)`. Keep the `_history.md`
  idempotency guard ahead of any git/gh work.
- Gate: T-4 GREEN; existing reconcile tests still pass (no double-ship).

- [x] **T-6** — Doc: branch-cleanup Phase-5 reconcile note reflects gh-primary classify
- Agent: build
- Files: `.claude/skills/ai-branch-cleanup/SKILL.md:90`
- Principles applied: §10.7 Clean Code (docs match behavior)
- Patch (deterministic): none — prose: update the Phase-5 description to state
  reconcile classifies merge via `gh` PR state (survives Phase-1 prune), with
  the local-ref check as fallback. Note explicitly that composite phase order is
  unchanged (D-161-04 / Non-Goal).
- Gate: `grep` shows gh-primary wording; mirror parity deferred to P6.

---

## Phase 3 — `approve` + `start` verbs + frontmatter mirror

- [x] **T-7** — RED: approve transitions DRAFT→APPROVED, emits event, idempotent
- Agent: build
- Files: `tests/unit/specs/test_spec_lifecycle.py`
- Principles applied: §10.5 TDD
- Patch (deterministic): none — tests: (a) `approve` on DRAFT → sidecar
  `state=approved`, exit 0, `spec_approved` event appended; (b) re-`approve` on
  APPROVED → no-op 0, no duplicate event; (c) `approve` on SHIPPED → FSM raises
  (exit 1). Symmetric `start` tests: APPROVED→IN_PROGRESS, idempotent, illegal
  from DRAFT raises.
- Gate: `pytest -k "approve or start_verb"` RED.

- [x] **T-8** — RED: frontmatter mirror writes mapped `status:` for active spec
- Agent: build
- Files: `tests/unit/specs/test_spec_lifecycle.py`
- Principles applied: §10.5 TDD
- Patch (deterministic): none — test: a `spec.md` whose frontmatter `spec:`
  matches the record → after `approve`, frontmatter `status: approved`; after
  `start`, `status: in-progress` (vocab map D-161-02). Mirror only fires when
  frontmatter id/slug matches the record (no cross-spec write).
- Gate: `pytest -k frontmatter_mirror` RED.

- [x] **T-9** — GREEN: `approve()` + `start()` application functions
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py` (new fns near `start_new`/`mark_shipped`, ~L483)
- Principles applied: §10.3 SOLID, §10.6 SDD, §10.4 DRY (compose `_load_state`+`transition`+`_write_state`+`_append_event`)
- Patch (deterministic): none — `approve(spec_id, project_root)`: load; if
  already APPROVED return no-op; else `transition(DRAFT→APPROVED)`,
  `_write_state`, `_append_event("spec_approved", …)`, mirror frontmatter.
  `start(spec_id, project_root)`: same shape APPROVED→IN_PROGRESS, event
  `spec_started_impl` (distinct from `start_new`'s create event).
- Gate: T-7 GREEN.

- [x] **T-10** — GREEN: `_mirror_frontmatter_status` infra helper
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py` (new fn near `_spec_frontmatter_id`:1129)
- Principles applied: §10.3 SOLID (Infra layer), §10.2 YAGNI
- Patch (deterministic): none — read `specs/spec.md`; only rewrite the
  frontmatter `status:` line when frontmatter `spec:` == record.spec_id OR
  `slug:` == record.slug; map state→status per D-161-02; best-effort (log on
  failure, never raise — D-161-08). Called by `approve()`/`start()`.
- Gate: T-8 GREEN.

- [x] **T-11** — GREEN: register `approve`/`start` subparsers + dispatch
- Agent: build
- Files: `.ai-engineering/scripts/spec_lifecycle.py:1377-1411, 1426-1455`
- Principles applied: §10.4 DRY (mirror existing subparser idiom)
- Patch (deterministic):
```diff
@@ sn = sub.add_parser("start_new", help="Create DRAFT spec record")
     sn.add_argument("slug")
     sn.add_argument("title")
     _common(sn)
+    ap = sub.add_parser("approve", help="Transition DRAFT → APPROVED")
+    ap.add_argument("spec_id")
+    _common(ap)
+    sta = sub.add_parser("start", help="Transition APPROVED → IN_PROGRESS")
+    sta.add_argument("spec_id")
+    _common(sta)
     ms = sub.add_parser("mark_shipped", help="Mark spec SHIPPED post-merge")
@@ elif args.cmd == "start_new":
             record = start_new(args.slug, args.title, project_root)
             print(json.dumps(record.to_json(), indent=2))
+        elif args.cmd == "approve":
+            record = approve(args.spec_id, project_root)
+            print(json.dumps(record.to_json(), indent=2))
+        elif args.cmd == "start":
+            record = start(args.spec_id, project_root)
+            print(json.dumps(record.to_json(), indent=2))
```
- Gate: `spec_lifecycle.py approve --help` and `start --help` exit 0; T-7 CLI-level cases pass.

---

## Phase 4 — Skill gate wiring (depends P3)

- [x] **T-12** — `/ai-plan` Step 1: hard approval gate (canonical sidecar read)
- Agent: build
- Files: `.claude/skills/ai-plan/SKILL.md:21-23`
- Principles applied: §10.6 SDD, §10.1 KISS
- Patch (deterministic): none — judgment. Insert a Step 1 sub-step BEFORE
  decomposition: resolve the active spec's canonical state — `spec_lifecycle.py
  status <id>` (id from frontmatter `spec:` then `slug:`); if `state != approved`
  and state is resolvable → HARD STOP with the issue-#551 error text
  (`Error: spec-<id> is in '<state>' state. Complete /ai-brainstorm approval
  before running /ai-plan.`), write NO plan.md. If neither sidecar nor
  frontmatter `status` resolves → loud warning + proceed (D-161-03). No
  `--force` (Non-Goal).
- Gate: doc states block-on-known + fail-open-on-indeterminate; manual dry-run
  on a draft sidecar STOPs.

- [x] **T-13** — `/ai-brainstorm` Step 9: call `approve` at the approval gate
- Agent: build
- Files: `.claude/skills/ai-brainstorm/SKILL.md:60`
- Principles applied: §10.6 SDD
- Patch (deterministic): none — prose: at Step 9, when the operator approves,
  call `python .ai-engineering/scripts/spec_lifecycle.py approve <spec_id>`
  (fail-open — log and continue the STOP on non-zero, D-161-08) so the sidecar
  reaches APPROVED and frontmatter mirrors before handing to `/ai-plan`.
- Gate: doc shows the approve call wired into Step 9.

- [x] **T-14** — `/ai-build` Step 1: call `start` (APPROVED→IN_PROGRESS)
- Agent: build
- Files: `.claude/skills/ai-build/SKILL.md:25`
- Principles applied: §10.6 SDD
- Patch (deterministic): none — prose: alongside the existing board sync,
  call `spec_lifecycle.py start <spec_id>` to mark the sidecar IN_PROGRESS
  (fail-open). Mirrors `status: in-progress`.
- Gate: doc shows the start call; fail-open noted.

---

## Phase 5 — Installer id data reconciliation (#574 Bug 1b)

- [x] **T-15** — Reconcile `_history.md` installer row spec-158 → spec-159
- Agent: build
- Files: `.ai-engineering/specs/_history.md`
- Principles applied: §10.7 Clean Code (single SoT id), §10.4 DRY
- Patch (deterministic): none — judgment (verify exact row first). Locate the
  installer-parity row; correct its id cell `spec-158` → `spec-159` to match the
  archive dir/branch/PR (D-161-07). Confirm no other row legitimately owns
  spec-158 before editing.
- Gate: `grep -n "installer" .ai-engineering/specs/_history.md` shows spec-159;
  no duplicate spec-158 collision.

- [x] **T-16** — Guard test: id reconciliation has no frozen-ledger test pinning old text
- Agent: verify
- Files: `tests/` (read-only scan)
- Principles applied: §10.5 TDD
- Patch (deterministic): none — confirm no test asserts the spec-158 installer
  row literal (R-161-07). If one exists, flag for update in the same phase.
- Gate: `grep -rn "spec-158" tests` returns nothing load-bearing.

---

## Phase 6 — Sync, changelog, seal (convergence)

- [x] **T-17** — Regenerate IDE mirrors for the three edited skills + cleanup doc
- Agent: build
- Files: `.codex/`, `.agents/`, `.github/` (generated)
- Principles applied: §10.4 DRY (single canonical source)
- Patch (deterministic): none — run `ai-eng dev sync`; do not hand-edit mirrors.
- Gate: `pytest tests/unit -k surface_parity` (and mirror-parity tests) green.

- [x] **T-18** — CHANGELOG entry
- Agent: build
- Files: `CHANGELOG.md`
- Principles applied: §10.7 Clean Code
- Patch (deterministic): none — prose: add a spec-161 entry covering the
  `approve`/`start` verbs, the `/ai-plan` gate, archive-aware numbering, gh-based
  reconcile, and the installer-id data fix (Hard Rule #3 documents the breakage:
  `/ai-plan` now blocks unapproved specs).
- Gate: CHANGELOG lints clean; docs gate (`pytest tests/docs`) green.

- [x] **T-19** — Final full gate
- Agent: verify
- Files: repo-wide
- Principles applied: §10.5 TDD, §10.7 Clean Code
- Patch (deterministic): none.
- Gate: `pytest` green; `ai-eng spec verify --sections` valid; secrets/lint
  pre-push gates pass; `spec_lifecycle.py status spec-161` resolves.

---

## Phase ordering & gates summary

```
P1 (numbering) ─┐
P2 (reconcile) ─┼─ parallel ──┐
P5 (data fix)  ─┘             │
P3 (verbs+mirror) ───────────┼─→ P4 (skill wiring, needs P3) ─→ P6 (sync+seal)
                             ─┘
```

- Every GREEN task is preceded by its RED test (TDD §10.5).
- `verify` agent tasks (T-16, T-19) are read-only.
- No `/ai-build` invocation from this plan (No-Execution Protocol).

## safe_next_command

`/ai-autopilot` — multi-concern (4) + 11 est. files. Operator approves this plan
(`status: approved`) before execution.
