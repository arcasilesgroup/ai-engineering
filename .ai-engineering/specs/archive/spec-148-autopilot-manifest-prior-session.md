# Autopilot Manifest: spec-148 (Files-only persistence + obvious-by-default)

## Run parameters
- Mode: DIRECT, controlled, wave-by-wave (operator chose — no autonomous build agents, per the spec-147 rogue-agent incident). Main thread implements each wave, TDD, commit+test+push per wave.
- Delivery: all waves on branch `spec-147-wave-1` / PR #532 (operator: same branch/PR).
- HARD PAUSE before Wave P5 (irreversible state.db deletion).
- spec: `.ai-engineering/specs/spec.md` (spec-148, approved). plan: `.ai-engineering/specs/plan.md` (approved).

## Waves (9) — DAG: P1→P2→P3→P4→P5(gated)→P6 ; then W7→W8→W9 (W8 may overlap W7). SKILL.md-touching waves P6→W7→W9 serialized for mirror regen.

| Wave | Title | Status |
|------|-------|--------|
| P1 | events/audit off SQLite (D-148-05/06) | DONE — pushed #532, CI green (98bffc93) |
| P2 | decisions/risk off SQLite (D-148-02/03/07) | DONE — pushed #532 (43ad5397); CI Integration red (telemetry seed + install-schema snapshot) → fixed in P3 commit |
| P3 | ownership off SQLite (D-148-02) + P2 CI fixes | DONE — pushed #532 (ed1e5701), CI green |
| P4 | install-state + capabilities off SQLite (D-148-04/08) — hardest | DONE — pushed #532 (8e7636d1 + CI-fix 435a0b8e), CI watching. P4 push was red (E2E + Unit: state.db assertions + stale _STATE_FILES tests + spec-125 state_canonical contract); all fixed in 435a0b8e. Local migration: exported state.db install_state → install-state.json (preview of P5) to restore hook hashes (gitignored). LESSON: re-run full unit+e2e+integration after EVERY change (the _STATE_FILES edit slipped through on a stale green; e2e was never run pre-push first time). |
| P5 | DELETE SQLite layer + export migration (D-148-01/09) | DONE — operator-approved. Pushed #532: migration b79266ce (Phase A) + deletion eb67d41f (Phase B/C). CI watching. Deleted state_db.py + migrations/ + audit_index.py + retention.py + doctor_state_db cmd + 5 audit verbs + ~14 tests; export→verify→delete in `ai-eng update`; test_no_sqlite guard; gitignored the per-install file SoTs. G1 met: no SQLite anywhere (except the one-shot migration reader). |
| P6 | persistence doctrine/docs/skills/tests (D-148-09/G9) | DONE — pushed #532: P6.1 doctrine rewrite (133ce726) + P6.2 sweep+mirrors (4d11b5ba), CI watching. persistence-doctrine.md three-tier; CANONICAL + ~31 skills/agents + _CLAUDE_EXTRAS swept; 1352 mirrors in sync; cross-ref allowlist for gitignored state files. NOTE: .agent/.opencode are UNTRACKED user surfaces (local-only link fails, CI-clean). |
| W7 | one-obvious-way: triggers + branch-cleanup (D-148-11/12) | NOT STARTED — scoped. Two parts: (a) de-collide 5 contested phrases [blog post→ai-prose; pre-release→ai-verify; architecture→ai-explore; scan-for-security→ai-security; implement-it→ai-build] across ~10 SKILL.md `description:` fields, others cross-ref, +gate "no phrase in >1 description" +mirror regen; (b) branch-cleanup: maintenance_branch_cleanup → delegate to cleanup_branches_cmd, DELETE run_branch_cleanup (branch_cleanup.py:271; used ONLY by maintenance.py; cleanup.py/report.py import OTHER helpers so module stays), +test_branch_cleanup_single_impl, fix test_branch_cleanup.py (drop TestRunBranchCleanup), CHANGELOG. DECISION NEEDED: maintenance's --target/--base don't map to cleanup_branches_cmd (cwd-based, hardcoded base) — either drop them (thin alias) or keep as documented no-ops. |
| W8 | deterministic-done: method tag + STOP (D-148-13) | NOT STARTED. Add `method: deterministic|llm` to verify Finding model + assembly (tool runners=deterministic, verifier-acceptance=llm); make quality.md Step 2d cond 4 deterministic-or-advisory; replay test same-diff→same-STOP. |
| W9 | poka-yoke: §10.x + naming + dry-run + suppression DEC (D-148-14..17) | NOT STARTED. 5 gates: backfill §10.x into ~22 Workflow-less skills + test_workflow_principle_citation; naming-grammar test; cleanup branches no-flag deletes nothing (W9.4, also touches the cleanup.py:258 default-merged); nosemgrep-without-dec_id fails allowlist + author DECs. |

## SESSION CHECKPOINT (Part A complete)
P1-P6 DONE + CI-green on #532 (HEAD 06b4bb10): files-only persistence, state.db DELETED, doctrine/mirrors updated. spec-148 Part A fully delivered. W7-9 (Part B conventions) NOT STARTED — intricate (behavioral branch-cleanup mapping + judgment-heavy de-collide owner decisions + Finding-model + 5 CI gates); recommended for a fresh session to hold the staff-engineer quality bar. Local install-state.json was manually exported from state.db (gitignored) to restore hook-integrity post-P4.

## P1 progress (events/audit off SQLite)
- [x] step 1 — NDJSON token-rollup module `src/ai_engineering/state/audit_rollup.py` + 5 tests (committed). Replaces skill/agent/session_token_rollup SQL views.
- [x] step 2 — `audit_cmd.audit_tokens` rewired → audit_rollup (committed; 7 CLI tests green).
- [x] step 3 — `audit replay` ported to NDJSON (committed; build_span_tree(ndjson_path) + _event_to_row; sqlite3 import gone from audit_replay; 24 tests green state+CLI).
- [x] step 4 — `audit otel-export` REMOVED (committed): function + cli_factory reg + audit_otel_export.py module + 2 tests deleted; build_otlp_spans/_empty_token_rollup gone.
- [x] step 5a — `audit query` REMOVED (committed): fail-loud stub; query-only helpers (_is_select/_ensure_limit/_strip_sql_comments/_TOKEN_VIEWS/_DEFAULT_QUERY_LIMIT) + unused sqlite3/open_index_readonly imports gone; test_audit_query_cli rewritten (3 stub tests).
- [x] step 6a-i — `runtime-stop.py` rewired (committed): _ndjson_session_rollup (stdlib) replaces the SQLite session_token_rollup read; sqlite3/_AUDIT_INDEX_REL gone; template synced; hooks-manifest regenerated; test rewired to NDJSON (4 pass). Behavior: missing source → silent skip (was framework_error).
- [ ] step 6a-ii — `runtime-session-end.py`: drop the `PRAGMA incremental_vacuum` on state.db (~237) + the `ai-eng audit index --json` subprocess call (~139). + template copy + tests (test_state_db_incremental_vacuum). Regenerate manifest.
- [ ] step 6a-iii — `session_bootstrap.py`: decisions/risk counts (~473) read state.db → read decision-store.json (stdlib json). + its dashboard tests.
- [ ] step 6b — remove `audit index` (no hook calls it after 6a-ii) + drop `_index_is_stale`/`_ensure_fresh_index`/`build_index`/`index_path` from audit_cmd + cli_factory `index` reg + test_audit_index_cli. Update audit_cmd module docstring (still describes index/query as SQL).
- [ ] Gate: `audit verify` green; hot-path <1s/<5s; no sqlite in hooks/audit path. Then P1 done → push #532.
- FOLLOWUP (cheap, Wave-1 leftover): integrity.py:52 + _lib/hook-common.py:543 hint says `scripts/regenerate-hooks-manifest.py` but it's `.ai-engineering/scripts/regenerate-hooks-manifest.py` — fix the path (obvious-by-default trap I introduced in Wave 1).

## Branch state
spec-147-wave-1: origin has Waves 1/2a (spec-147, green #532). Local ahead: A1+revert, spec-148 spec/plan, P1 rollup module. Not yet pushed (push at a wave boundary).

## OQs to resolve in-flight
- Exact contested-phrase → skill assignments (W7).
- `audit otel-export`: reimplement over NDJSON vs drop (P1).
