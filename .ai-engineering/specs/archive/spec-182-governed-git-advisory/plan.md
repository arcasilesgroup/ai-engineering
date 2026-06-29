---
spec: spec-182
title: Plan — Advisory nudge routing raw git/gh to /ai-commit and /ai-pr
status: approved
execution_route:
  version: 1
  spec: spec-182
  executor: build
  automation: standard
  concern_count: 1
  estimated_files: 10
  reason: >-
    Single-concern advisory hook. Mostly mechanical wiring (settings twins,
    template mirror, manifest regen, toggle doc) plus one judgment-heavy hook
    script and its tests. Single concern → build, not autopilot.
  safe_next_command: "/ai-build"
---

# Plan — spec-182 Advisory nudge routing raw git/gh to /ai-commit and /ai-pr

Pipeline: **full**. Executor: **build**. Concern count: 1. Est. files: ~10.

## Design

`--skip-design` — no user-facing UI surface. This is a backend `PreToolUse`
hook + wiring + docs. No design intent required.

## Architecture

**Hook adapter** at the IDE tool-call boundary (§10.8 Hexagonal). The new
`governed-git-advisor.py` clones the proven `no-verify-guard.py` PreToolUse
adapter shape: stdlib-only, sealed contract (no `ai_engineering.*` imports),
`get_hook_context()` → analyse `tool_input.command` → either emit a
`hookSpecificOutput` advisory (allow) or `passthrough_stdin`. It diverges from
`no-verify-guard` only in that it ALLOWS (never `sys.exit(2)`) and injects
`additionalContext` instead of a `decision: block`.

Reference shapes (from codebase extraction):
- Verb-parse + main() skeleton: `.ai-engineering/scripts/hooks/no-verify-guard.py:44-151`
- `hookSpecificOutput` stdout pattern: `.ai-engineering/scripts/hooks/runtime-guard.py:222-234`
- Ledger emit: `_lib.hook_common.emit_event(project_root, {...})` — required keys
  `kind, engine, timestamp, component, outcome, correlationId, schemaVersion, project`
- Test pattern: `tests/unit/hooks/test_spec_121_hooks.py:22-98` (`_load` + `_ctx` + monkeypatch)

## Phases

### Phase 1 — RED (TDD, §10.5)

- [x] T-1 — Write failing hook unit tests — DONE (14 cases RED→GREEN)
  - Agent: build
  - Files: `tests/unit/hooks/test_governed_git_advisor.py` (new)
  - Principles applied: §10.5 TDD, §10.7 Clean Code
  - Patch (deterministic): — (judgment: test authoring; clone `_load`/`_ctx`
    pattern from `tests/unit/hooks/test_spec_121_hooks.py:22-98`)
  - Cases (each asserts via in-process `mod.main()` + monkeypatched
    `get_hook_context`/`passthrough_stdin`, capturing stdout + emitted event):
    1. `git commit -m x` → stdout parses to
       `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":<str>}}`
    2. `git push origin main` → advisory emitted (routes to `/ai-commit`)
    3. `gh pr create ...` → advisory emitted (routes to `/ai-pr`)
    4. **Goal acceptance**: `additionalContext` contains all of
       `secret scan`, `docs gate`, `spec consolidation`, `audit chain`
    5. Compound `git add . && git commit -m x && git push` → advisory fires
       (D-182-07 sub-command split)
    6. `git -C /tmp/repo commit -m x` → advisory fires (D-182-07 path-prefix)
    7. `git log` / `git status` / `git diff` → NO advisory (`passthrough_stdin`)
    8. non-Bash tool (`tool_name="Read"`) → `passthrough_stdin`, no advisory
    9. ledger: a `policy_decision` event with `component="hook.governed-git-advisor"`
       is appended (assert via temp `framework-events.ndjson`)
    10. `AIENG_GOVERNED_GIT_ADVISOR_DISABLED=1` → no advisory, `passthrough_stdin`
    11. fail-open: malformed `tool_input` → no exception, `passthrough_stdin`
  - Gate: `pytest tests/unit/hooks/test_governed_git_advisor.py` → all FAIL
    (module not yet present / import error is acceptable RED)

### Phase 2 — GREEN (implement hook)

- [x] T-2 — Implement `governed-git-advisor.py` — DONE (14/14 pass)
  - Agent: build
  - Files: `.ai-engineering/scripts/hooks/governed-git-advisor.py` (new)
  - Principles applied: §10.1 KISS, §10.8 Hexagonal Architecture, §10.5 TDD
  - Patch (deterministic): — (judgment: new hook script)
  - Spec:
    - Clone shebang/imports from `no-verify-guard.py:1-39`
      (`from _lib.audit import passthrough_stdin`,
       `from _lib.hook_common import run_hook_safe, emit_event, get_correlation_id`,
       `from _lib.hook_context import get_hook_context`).
    - Early-exit (hot-path, R4): if `os.environ.get("AIENG_GOVERNED_GIT_ADVISOR_DISABLED") == "1"`
      → `passthrough_stdin`; if `tool_name != "Bash"` → `passthrough_stdin`.
    - Detection (D-182-02, D-182-07): split command on `&&`/`;`/`|`; per
      sub-command `shlex.split`, strip leading `VAR=val` env-prefix and
      `git -C <p>`/`--git-dir=`/`--work-tree=` tokens, then match verb ∈
      {`git commit`, `git push`, `gh pr create`}. Read-only/structural verbs
      ignored. Literal verbs only (Non-Goals: aliases/`gh api`/MCP/subshells).
    - On match: build the nudge text (MUST contain the four governance terms —
      Goal acceptance / T-1 case 4; route commit+push→`/ai-commit`, pr→`/ai-pr`;
      include the self-aware clause D-182-03 "if not already inside …";
      note `--amend`→fresh commit per D-182-02). Write
      `{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"allow","additionalContext":<nudge>}}`
      to stdout (separators `(",",":")`, like runtime-guard.py:228-233). Do NOT
      `passthrough_stdin` on this path (own stdout). Do NOT `sys.exit` (allow).
    - Ledger (D-182-05): `emit_event(ctx.project_root, {...})` with
      `kind="policy_decision"`, `component="hook.governed-git-advisor"`,
      `outcome="success"`, `detail={"hook_kind":"pre-tool-use","verb":<verb>,
      "session_seq":<first|repeat>}`. Session-sequence marker = first raw-git
      this session vs repeat (track via a runtime marker file keyed on
      `get_session_id()`; fail-open if unwritable).
    - No match: `passthrough_stdin(ctx.data)`.
    - Entry point: `run_hook_safe(main, component="hook.governed-git-advisor",
      hook_kind="pre-tool-use", script_path=Path(__file__))` (always exit 0).
  - Gate: `pytest tests/unit/hooks/test_governed_git_advisor.py` → all PASS

### Phase 3 — Wiring (mechanical)

- [x] T-3 — Mirror hook to template twin (byte-identical) — DONE
  - Agent: build
  - Files: `src/ai_engineering/templates/.ai-engineering/scripts/hooks/governed-git-advisor.py` (new)
  - Principles applied: §10.4 DRY
  - Patch (deterministic):
    ```bash
    cp .ai-engineering/scripts/hooks/governed-git-advisor.py \
       src/ai_engineering/templates/.ai-engineering/scripts/hooks/governed-git-advisor.py
    ```
  - Gate: `pytest tests/unit/test_template_parity.py::TestHookScriptParity` (count + names) → PASS

- [x] T-4 — Wire matcher into live settings.json — DONE
  - Agent: build
  - Files: `.claude/settings.json` (insert after the no-verify-guard entry, line 78)
  - Principles applied: §10.1 KISS
  - Patch (deterministic):
    ```diff
    @@ .claude/settings.json PreToolUse @@
             "timeout": 5
           }
         ]
       },
    +  {
    +    "matcher": "Bash",
    +    "hooks": [
    +      {
    +        "type": "command",
    +        "command": "bash \"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/_lib/run-hook.sh\" \"$CLAUDE_PROJECT_DIR/.ai-engineering/scripts/hooks/governed-git-advisor.py\"",
    +        "timeout": 5
    +      }
    +    ]
    +  },
       {
         "matcher": "Bash|Write|Edit|MultiEdit",
    ```
    (indentation must match the file's existing 6-space block indent)
  - Gate: `python -c "import json; json.load(open('.claude/settings.json'))"` → valid

- [x] T-5 — Wire identical matcher into template settings.json — DONE
  - Agent: build
  - Files: `src/ai_engineering/templates/project/.claude/settings.json` (PreToolUse block, after the no-verify-guard entry)
  - Principles applied: §10.4 DRY
  - Patch (deterministic): same hunk as T-4, applied to the template PreToolUse array
  - Gate: `pytest tests/unit/test_template_parity.py::TestSettingsJsonParity::test_hook_entry_count_per_event` → PASS

- [x] T-6 — Re-pin hooks-manifest sha256 — DONE (77 hooks, --check clean)
  - Agent: build
  - Files: `.ai-engineering/state/hooks-manifest.json` (regenerated output)
  - Principles applied: §10.5 TDD (integrity gate)
  - Patch (deterministic):
    ```bash
    python3 .ai-engineering/scripts/regenerate-hooks-manifest.py
    ```
  - Gate: `python3 .ai-engineering/scripts/regenerate-hooks-manifest.py --check` → exit 0
    (hook runs under `AIENG_HOOK_INTEGRITY_MODE=enforce` without self-disabling)

### Phase 4 — Docs + toggle registration

- [x] T-7 — Register the disable toggle (canonical source → mirrors) — DONE (core.py + dev sync; CLAUDE.md + template carry it)
  - Agent: build
  - Files: canonical tunables source (`CANONICAL.md` / `_CLAUDE_EXTRAS` in
    `scripts/sync_mirrors`), then regenerated `CLAUDE.md` + mirrors via `ai-eng dev sync`
  - Principles applied: §10.4 DRY (CLAUDE.md is a generated mirror — never edit directly)
  - Patch (deterministic): add to the `# spec-147 G2` escape-hatch block, after
    `AIENG_IOC_FAIL_CLOSED`:
    ```
    AIENG_GOVERNED_GIT_ADVISOR_DISABLED  # set "1" to disable the raw-git→skill advisory nudge
    ```
    then run `ai-eng dev sync`
  - Gate: `grep -q AIENG_GOVERNED_GIT_ADVISOR_DISABLED CLAUDE.md` AND mirror-parity tests green

- [x] T-8 — CHANGELOG entry (docs gate) — DONE
  - Agent: build
  - Files: `CHANGELOG.md`
  - Principles applied: §10.7 Clean Code
  - Patch (deterministic): — (judgment: one Added/Changed line referencing spec-182)
  - Gate: `python3 .ai-engineering/scripts/doc_gate.py --changed-paths "<staged>"` → exit 0

### Phase 5 — Verify

- [x] T-9 — Full verification sweep — DONE (ruff+ty+check 7/7+47 tests+enforce smoke all green)
  - Agent: verify
  - Files: — (read-only)
  - Principles applied: §10.4 Goal-Driven Execution, §10.5 TDD
  - Patch (deterministic): —
  - Gate (all must pass):
    - `pytest tests/unit/hooks/test_governed_git_advisor.py`
    - `pytest tests/unit/test_template_parity.py`
    - `pytest tests/unit/hooks/test_canonical_events_count.py` (event-type count unchanged = 11; no dead wiring)
    - `ai-eng validate` (manifest/content integrity)
    - `ruff format --check` + `ruff check` + `ty check src/`
    - hook smoke: `governed-git-advisor.py` runs under enforce mode, emits the
      confirmed `permissionDecision:"allow"` envelope (D-182-01)

## Risk → task traceability

- R1 (retroactive push/PR) — accepted; nudge text (T-2) sets expectation; no code remedy in v1.
- R2/R3 (false-neg, cry-wolf) — T-1 cases 5–6 cover compound/`-C`; R3 noise accepted v1, ledger (T-2) measures it.
- R5 (hidden gates) — T-3/T-4/T-5/T-6/T-7 each close one parity/integrity gate; T-9 verifies all.
- R6 (ledger attribution) — T-2 session-seq marker is the partial signal; documented limit, no over-claim.

## Out of scope (this plan)

In-skill suppression sentinel lockfile (Open Question, deferred v1.5);
`gh api`/MCP-git/alias detection (Non-Goals); hard-block v2.

## Quality Outcome

Final: 0 blockers, 0 criticals, 0 highs -> PASS

Initial assessment (verify + review, parallel, full changeset):
- verify: 92/100 PASS, 0 blocker/critical/high; 2 low (gh value-flag false-neg, unbounded marker).
- review: SHIP-READY, 0 blockers; 1 medium (gh value-flag), rest low/info.

No bounded remediation pass was required (no blocker/critical/high). Two
corroborated improvements applied voluntarily as surgical, Goal-serving edits:
- gh `-R`/`--repo` value-flag skip before the `pr create` subcommand
  (`_GH_VALUE_FLAGS` + `_is_gh_pr_create`, mirrors `_git_verb` `-C` handling) —
  removes the D-182-05 ledger undercount; +5 parametrized tests.
- R4 hot-path substring pre-screen (`"git"`/`"gh"`) before `shlex` — bounds the
  O(n^2) pathological-input cost; +1 test.

Accepted (low/info, not remediated): unbounded session-marker growth
(gitignored runtime file, one token/session — YAGNI); amend sentence appearing
on push/PR nudges (cosmetic); `git -c key=val commit` miss (shared
no-verify-guard precedent, edge). Tests: 18 hook cases, 39 incl. parity+events,
all green. ruff/ty/`ai-eng check` 7/7 clean; enforce-mode smoke confirms the
D-182-01 envelope.
