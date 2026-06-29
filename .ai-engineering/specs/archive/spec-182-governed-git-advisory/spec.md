---
spec: spec-182
title: Advisory nudge routing raw git/gh to /ai-commit and /ai-pr
status: in-progress
effort: small
summary: Add a non-blocking PreToolUse advisory that fires on raw git commit/push and gh pr create, steering the agent to /ai-commit and /ai-pr so governed pipelines (secret scan, docs gate, spec consolidation, audit chain) are not silently skipped.
---

# Advisory nudge routing raw git/gh to /ai-commit and /ai-pr

## Summary

When the agent issues a raw `git commit`, `git push`, or `gh pr create`
mid-task, it silently bypasses the governed pipelines. The losses are real,
not cosmetic: `/ai-commit` carries the secret scan (`gitleaks protect
--staged`), docs gate, `ruff` format/fix, conventional-commit composition and
work-item trailers; `/ai-pr` additionally carries the pre-push `semgrep` +
`pip-audit` gates, spec consolidation (`mark_shipped` — without it the spec
FSM never advances, the `spec_shipped` audit event is never written, and the
**live spec slot stays occupied and reds idle-slot gates on every later CI
run**), docs auto-update, the spec-derived PR body, board sync, and the CI
watch-and-fix loop.

There are two distinct reasons raw git/gh happens, and the design must own
both:

1. **Genuine drift** — for a standalone user request ("commit this", "open a
   PR") the agent reaches for raw git instead of `/ai-commit` / `/ai-pr`.
   Nothing reminds it at the decision moment. This is the case the advisory
   solves.
2. **Correct in-skill calls** — `/ai-commit`, `/ai-pr` (and its watch loop),
   `/ai-branch-cleanup`, `/ai-resolve-conflicts`, `/ai-autopilot`, `/ai-build`
   all run raw `git commit`/`git push`/`gh pr create` internally, by design.
   These are not drift — the advisory must NOT pull the agent off behavior it
   is correctly performing.

Today nothing intercepts these verbs. The only git-related `PreToolUse` guard
is `no-verify-guard.py` (`--no-verify` only). The skill-steer hook
(`runtime-progressive-disclosure.py`) fires on `UserPromptSubmit` and is
suppressed during `/ai-*` execution — exactly the moment the agent issues raw
git mid-task. CLAUDE.md/CONSTITUTION say "use the chain" as prose the model
drifts past. This spec adds a reminder at the decision moment (case 1), and
accepts — as a v1 limitation — that the same reminder fires on case 2 and
relies on the agent recognizing it is already governed (see D-182-03, R3).

## Goals

- A `PreToolUse` hook on the `Bash` tool detects raw `git commit`, `git push`,
  and `gh pr create` and emits an advisory steering the agent to `/ai-commit`
  (commit + push) or `/ai-pr` (PR).
- The advisory is **non-blocking** — it returns `permissionDecision: "allow"`
  and never denies the tool call.
- The advisory names the concrete governance lost. **Acceptance:** a unit test
  asserts the emitted `additionalContext` for each detected verb contains the
  canonical terms (secret scan, docs gate, spec consolidation, audit chain) so
  a later message simplification cannot silently gut the steer.
- Every detection is recorded to the audit ledger with enough context to
  inform the v2 (hard-block) decision (see D-182-05 for the data's limits).
- The hook is fail-open and disableable via a documented env toggle.
- The hook stays within the Claude Code hook hot-path budget (stdlib-only,
  early-exit on non-git/gh commands).

## Non-Goals

- **Hard block / deny** of raw git. Deferred to a data-justified v2 gated on
  this spec's ledger evidence.
- A **governed-signal mechanism** (per-call env-prefix, sentinel lockfile) to
  deterministically suppress the nudge during in-skill calls. The
  non-persistent shell-env constraint means this would require per-call
  prefixing across ~6 skills (the same retrofit a block needs) or a sentinel
  lockfile; both are deferred to a v1.5/v2 refinement (see Open Questions).
- **Retrofitting** any governed prefix into the git-using skills. Zero skill
  edits in v1.
- **Recovering governance for a bypass that already ran.** An exit-0 advisory
  lets the current call complete; it cannot retroactively apply gates to a
  commit/push/PR that already happened (see R1).
- Detecting PR creation via **`gh api`** REST calls (`gh api .../pulls`) — only
  the `gh pr create` CLI verb is in scope.
- Detecting commits made through **MCP git tools** (e.g. `mcp__git__*`) — those
  route through the `mcp__` matcher, not `PreToolUse:Bash`.
- Resolving **git aliases** (e.g. `git ci`) — alias expansion would require
  shelling out to `git`, violating the hot-path budget. Literal verbs only.
- Detecting verbs inside **subshells, heredocs, or process substitution**.
- Affecting the **human operator's** own `!`-prefixed terminal commands — those
  do not pass through `PreToolUse`.
- Changing the CLAUDE.md/CONSTITUTION posture from governed-by-default-advisory
  to governed-by-force.

## Decisions

### D-182-01 — Advisory (allow), not a hard block

The hook always allows the tool call and injects steering context; it never
denies.

**Output shape (confirmed against the official hook protocol):** the hook
exits 0 and writes to stdout the nested envelope
`{"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision":
"allow", "additionalContext": "<nudge>"}}`. This is verified against
code.claude.com/docs/en/hooks "Add context for Claude" — `additionalContext`
on a `PreToolUse` allow IS injected into the model's context. The flat
`{"decision": "allow", ...}` form is for other events and must NOT be used
here. This is the repo's first `PreToolUse` advisory (existing
`additionalContext` emitters are `PostToolUse`/`UserPromptSubmit`/`SessionStart`),
so the plan MUST include a smoke test asserting the exact envelope.

**Rationale**: A hard block needs a governed-signal the skills set so their own
git calls survive — but that signal must be readable by the same agent (it
lives in CLAUDE.md / skill files), so the agent can replay it under pressure,
making the "wall" a speed bump while adding a fragile per-call retrofit across
every git-using skill (miss one → that skill bricks, and the framework
dogfoods itself). An advisory attacks the real root cause (case 1 drift) with
zero breakage and full reversibility. Operator chose advisory over block this
session after the fragility was made explicit.

### D-182-02 — Intercept three verbs: `git commit`, `git push`, `gh pr create`

Detection targets exactly these verbs. Read-only and structural git (`log`,
`diff`, `status`, `rebase`, `stash`, `add`) is never nudged.

**Rationale**: These three are the only operations with a governed equivalent
(`/ai-commit` covers commit + push; `/ai-pr` covers the PR). Nudging verbs with
no governed alternative is noise that trains the agent to ignore the hook.
`git commit --amend` is intercepted as a commit; the nudge text notes that
`/ai-commit` does not rewrite history, so the agent should prefer a fresh
conventional commit (aligns with the §13.6 never-rewrite posture).

### D-182-03 — Self-aware nudge phrasing (the v1 in-skill disambiguator)

The advisory text is conditional: "if you are not already inside `/ai-commit`
or `/ai-pr`, prefer them."

**Rationale**: The skills themselves run these verbs (Summary case 2).
Deterministic suppression of the in-skill case would need either per-call
env-prefixing across ~6 skills (defeated by non-persistent shell env) or a
sentinel lockfile — both rejected for a v1 sold as zero-retrofit. Self-aware
phrasing is the cheapest disambiguator that adds no shared state: the agent
reading the nudge mid-`/ai-pr` recognizes it is already governed and proceeds.
This is an **accepted v1 limitation** — it relies on the agent inferring its
own execution context, the same inference the spec elsewhere calls unreliable.
R3 quantifies the resulting noise; the sentinel-lockfile upgrade is the leading
v1.5 item (Open Questions).

### D-182-04 — Fail-open, env-only toggle

Any hook error (parse failure, missing dependency) allows the call and logs.
`AIENG_GOVERNED_GIT_ADVISOR_DISABLED=1` disables the hook entirely.

**Rationale**: An advisory must never become a new failure mode on the hot
path; fail-open + a kill switch match the framework escape-hatch convention.
Following the established pattern (`AIENG_RALPH_DISABLED`,
`AIENG_RISK_ACCUMULATOR_DISABLED`, `AIENG_INSTINCT_BATCH_DISABLED` are all
env-only, read via `os.environ` inside the hook), **no `manifest.yml` twin is
added** — the env toggle is the sole control. Per
`.ai-engineering/reference/gate-policy.md`, advisory hooks are explicitly named
as plumbing that fails open and must log, so the classification is correct.

### D-182-05 — Record every detection to the audit ledger (with honest limits)

Each detection emits a lightweight event to the framework audit ledger,
carrying the verb, and a per-session sequence marker (first raw-git call this
session vs. a repeat after a prior nudge).

**Rationale**: v2 (hard block) must be data-justified. **Known limit:** without
the deferred governed-signal, the ledger CANNOT cleanly separate case-1 drift
from case-2 in-skill calls — a raw `git push` from `/ai-commit` Step 8 looks
identical to an ad-hoc push. So the count alone does not prove "the agent
ignored the nudge." The session-sequence marker gives partial signal (a
*repeat* raw-git after a nudge in the same session is a stronger ignored-signal
than a first call). v1 collects gross frequency + sequence; clean
attribution waits for the v1.5 sentinel. This honesty is itself a decision —
do not over-claim what the v1 data proves.

### D-182-06 — New `PreToolUse:Bash` hook, not the existing disclosure hook

The steer rides a new hook, not an extension of
`runtime-progressive-disclosure.py`.

**Rationale**: The disclosure hook fires on `UserPromptSubmit` and is
suppressed for `/ai-*` prompts — structurally unable to fire at the mid-task
`PreToolUse:Bash` moment when the agent issues raw git. The decision point is
the tool call, so the hook lives there. Per `knowledge-placement.md`, a
`PreToolUse:Bash` hook is the correct surface for a mid-task tool-call
intervention.

### D-182-07 — Detection scope: parse compound commands and path-prefix forms

Detection is not "first token after `git`". The hook splits compound Bash
strings on shell operators (`&&`, `;`, `|`) and applies verb detection to each
sub-command, and it consumes `git -C <path>` / `--git-dir=` / `--work-tree=`
path-prefix tokens before reading the verb.

**Rationale**: The dominant real-world pattern is one chained Bash call
(`git add . && git commit -m … && git push`). A naive first-token parser sees
`add` and misses the commit entirely — for a detect-to-nudge hook, false
negatives are the primary failure mode (opposite of `no-verify-guard.py`, where
they are a tolerated security weakness). `git -C <path> commit` is common in
multi-repo autopilot runs and must also resolve. Coverage explicitly stops at
the Non-Goals boundary (`gh api`, MCP git, aliases, subshells) — those pass
through silently and are acknowledged gaps, not promises.

## Risks

- **R1 — Advisory is retroactive for push/PR.** For `git commit` the nudge
  fires before the commit runs (pre-bypass — the right moment). For `git push`
  the pre-commit gates (secret scan, docs gate) were already bypassed; only
  pre-push `semgrep`/`pip-audit` remains preventable. For `gh pr create` the
  whole commit pipeline AND spec consolidation already ran — the nudge is
  largely after-the-fact and re-routing cannot un-bypass them. *Mitigation:*
  the commit-verb nudge (the highest-value one) is genuinely preventive; ledger
  data tells us whether push/PR warrant a v1.5 block even if commit does not.
  Accepted as the price of zero breakage.
- **R2 — Detection errors.** *False positives:* verb-precise parse; worst case
  one harmless hint, never a block. *False negatives:* compound commands are
  handled (D-182-07), but `gh api`, MCP git, aliases, and subshells are out of
  scope (Non-Goals) and pass through silently — the ledger will undercount real
  PRs relative to `gh pr create` detections, signalling the gap.
- **R3 — Cry-wolf in autonomous runs (primary noise path).** The `/ai-pr` watch
  loop issues raw `git commit`/`git push` on every CI-fix iteration (up to
  ~12 per PR on a multi-check failure); `/ai-autopilot` dispatches subagents
  that commit/push. The nudge fires each time. If the agent learns to ignore an
  advisory that fires repeatedly without consequence, the steer decays across
  ALL git ops. *Mitigation (v1):* self-aware phrasing (D-182-03); monitor
  per-session nudge counts via D-182-05 segmented by session type. *Upgrade:*
  the sentinel-lockfile suppression (Open Questions) removes this noise — its
  necessity is exactly what the ledger will confirm.
- **R4 — Hot-path cost.** `PreToolUse` fires on every Bash call. *Mitigation:*
  pure stdlib, early-exit when the command is not `git`/`gh`; stay well under
  the hook hot-path budget.
- **R5 — Hidden parity/integrity gates (under-declared elsewhere; named here).**
  A new hook reds several CI gates unless all twins land in the SAME commit:
  - `tests/unit/test_template_parity.py::TestHookScriptParity` —
    `test_hook_script_count_matches` + `test_hook_script_names_match` require a
    byte-identical twin at
    `src/ai_engineering/templates/.ai-engineering/scripts/hooks/governed-git-advisor.py`.
  - `tests/unit/test_template_parity.py::TestSettingsJsonParity::test_hook_entry_count_per_event`
    requires the new `PreToolUse` matcher be added to BOTH `.claude/settings.json`
    and `src/ai_engineering/templates/project/.claude/settings.json`.
  - `test_canonical_events_count.py::test_no_dead_wirings` fails on a hook
    script wired in only one place.
  - `hooks-manifest.json` must be re-pinned (sha256) via
    `regenerate-hooks-manifest.py`, or the hook self-disables under
    `AIENG_HOOK_INTEGRITY_MODE=enforce`.
  - the toggle must be registered in the CLAUDE.md Runtime Layer Tunables table.
  *Mitigation:* the plan carries each as an explicit checkbox; note there is NO
  CI guard for scripts/template parity beyond hooks — the hook-suite parity
  tests above ARE the guard, so they must be green (the spec-161
  missing-from-installs failure class).
- **R6 — Ledger attribution limit.** Per D-182-05, v1 data cannot cleanly
  separate drift from in-skill calls. *Mitigation:* collect the session-sequence
  marker for partial signal; do not gate v2 on a clean count the data cannot
  produce — gate it on the sentinel-equipped v1.5 measurement if needed.

## References

- doc: https://code.claude.com/docs/en/hooks.md — PreToolUse `additionalContext`
  + `permissionDecision` contract (confirms D-182-01 output shape)
- doc: CLAUDE.md §11 Canonical Chain — the workflow the advisory protects
- doc: .ai-engineering/reference/gate-policy.md — advisory hooks = plumbing,
  fail-open; what `/ai-commit` and `/ai-pr` enforce that raw git skips
- doc: .ai-engineering/scripts/hooks/no-verify-guard.py — the `PreToolUse:Bash`
  verb-parsing guard the new hook is modeled on
- doc: .ai-engineering/scripts/hooks/runtime-guard.py — `additionalContext`
  emit precedent (PostToolUse)
- doc: tests/unit/test_template_parity.py — the parity gates R5 must satisfy

## Open Questions

- **In-skill suppression (leading v1.5 item):** adopt a sentinel lockfile
  (`.ai-engineering/runtime/governed-git.active`, touched at skill entry /
  removed at exit across the ~6 git-using skills, read by the hook to stay
  silent) now, or defer? It is the clean fix for R3 cry-wolf and R6 ledger
  attribution. A stale lock fails toward silence (benign for an advisory).
  Recommended: ship v1 without it (honors "simple, zero-retrofit"), let the
  ledger prove whether the noise/attribution problem justifies the ~6-skill
  edit. **Operator decision pending.**
- Event-count gates: confirmed NOT at risk — `test_canonical_events_count.py`
  counts the 11 top-level event-type keys, and the new matcher sits under the
  existing `PreToolUse` key. The real gates are the `test_template_parity.py`
  trio in R5.
- Does `gh pr create` warrant stronger treatment (block) than commit/push in
  v1 given a PR is hardest to undo (R1)? Default v1: uniform advisory.
