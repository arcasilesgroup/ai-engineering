# plan-121: Self-Improvement + Hook Completion — Phased Plan

**Spec**: spec-121
**Owner**: ai-engineering (autonomous)
**Status**: in_progress

## Phase 1 — Hook event coverage (G)

**Tasks**

- T1.1 `runtime-notification.py` — minimal observer hook. Pattern: import `_lib/hook_common.run_hook_safe`, `_lib/hook_context.get_hook_context`, append observation, passthrough.
- T1.2 `runtime-session-end.py` — read `runtime/checkpoint.json` (written by runtime-stop), emit `framework_operation` `session_end_summary` with counts.
- T1.3 Wire both events in `.claude/settings.json` (no matcher → applies to all).
- T1.4 `_lib/hook_http.py` — `urllib.request` based POST helper, 5 s timeout, fail-open. Used by hooks that opt-in via env `AIENG_HOOK_HTTP_SINK_URL`.

**Gates**

- Hook scripts exit 0 on empty stdin.
- Unit tests (T7.1) green.
- `regenerate-hooks-manifest.py --check` clean post-edit.

## Phase 2 — Self-improvement loop (F)

**Tasks**

- T2.1 Edit `.claude/skills/ai-learn/SKILL.md`: add "AGENTS.md proposal mode" section. When category lesson count ≥ 5 in `LESSONS.md`, draft proposal block, append to `.ai-engineering/state/agents-proposals.md`. Hard rule: never edit AGENTS.md directly (D-118-04 mirror).
- T2.2 Mirror change to `.github/skills/ai-learn/SKILL.md` (Copilot mirror).
- T2.3 `.ai-engineering/scripts/scheduled/entropy-gc.sh` — wrapper that invokes `/ai-entropy-gc --no-pr=false` via `ai-eng` CLI when present, else logs `entropy_gc_scheduled_run` no-op.
- T2.4 `.claude/skills/ai-entropy-gc/SKILL.md`: append "Scheduled cadence" section showing exact `/schedule` cron + the wrapper path. Mirror to `.github/`.

**Gates**

- Scheduled wrapper executable (`chmod +x`).
- SKILL.md frontmatter unchanged (only body appends).

## Phase 3 — Validation + delivery

**Tasks**

- T3.1 `tests/test_spec_121_hooks.py` — pytest covering: empty stdin, valid Notification payload, valid SessionEnd payload, unknown event, http helper with mock URL.
- T3.2 `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py` — refresh sha256 manifest.
- T3.3 `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py --check` — verify manifest stable.
- T3.4 Smoke: invoke each new hook script with `echo '{}' | python3 <script>` — assert exit 0.
- T3.5 `ai-commit` style: write conventional commit `feat(spec-121): close self-improvement loop + hook event coverage`.

## Dependencies

- spec-120 lib helpers (`_lib/hook_common`, `_lib/hook_context`, `_lib/observability`) — already in place.
- No external runtime additions; stdlib only (urllib).

## Out-of-scope confirmations

- No E2B sandbox.
- No pgvector.
- No `prompt` type executor.
- No new agents.
