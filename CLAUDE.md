# CLAUDE.md — Claude Code Overlay

> See [AGENTS.md](./AGENTS.md) for the canonical cross-IDE rules (Step 0,
> available skills, agents, and the hard rules that delegate to
> [CONSTITUTION.md](./CONSTITUTION.md)). Read those first; this file
> only adds Claude-Code-specific specifics.

## Native Surface

- **Slash commands** — invoke skills via `/ai-<name>` in the Claude Code agent
  surface. Do not invent `ai-eng <skill>` terminal equivalents that are not
  listed in the CLI reference.
- **Skill location** — Claude Code project-scope skills live under
  `.claude/skills/` (one directory per skill, `SKILL.md` inside). User-scope
  copies live under `~/.claude/skills/` and are loaded as a fallback. The
  authoritative path is the one referenced from
  [AGENTS.md → Skills Available](./AGENTS.md#skills-available); see
  Article V of [CONSTITUTION.md](./CONSTITUTION.md) for the SSOT contract.
- **Subagents** — the dispatch surface is the 10 first-class agents listed in
  [AGENTS.md → Agents Available](./AGENTS.md#agents-available). Each runs in
  its own context window; offload research and parallel analysis to them.

## Hooks Configuration

Claude Code reads its hook wiring from `.claude/settings.json`:

- `UserPromptSubmit` runs the `/ai-*` dispatcher and emits `skill_invoked`
  telemetry events.
- `PostToolUse` runs the agent observability hooks (`agent_dispatched`,
  `ide_hook` events).
- All hook outcomes flow to `.ai-engineering/state/framework-events.ndjson`
  for the audit chain.

### Hook layout

Canonical scripts live under `.ai-engineering/scripts/hooks/` so the
cross-IDE mirrors (Copilot, Gemini, Codex) share the same source of
truth. `.claude/hooks/` is a symlink to that canonical directory, so
external tooling that follows the native Claude Code convention
(`.claude/hooks/<name>.py`) resolves to the same file. Edits go in the
canonical path; the symlink is read-only.

### Integrity verification

Hook bytes are pinned in `.ai-engineering/state/hooks-manifest.json`
(sha256 per script). `run_hook_safe` verifies the calling script
against this manifest on every invocation. Behaviour is governed by
the env var `AIENG_HOOK_INTEGRITY_MODE`:

- `enforce` (default, spec-120 follow-up) — mismatch refuses execution
  (exit 2) and logs a `framework_error` event with
  `detail.error_code = hook_integrity_violation`. Use in CI and any
  production-like context. Default flipped from `warn` after the
  spec-120 governance review confirmed the manifest stays clean under
  `--check`.
- `warn` — mismatch logs the `framework_error` event but allows the
  hook to run. Set `AIENG_HOOK_INTEGRITY_MODE=warn` in your shell rc
  to opt out of fail-closed in dev workflows that change hooks
  frequently and don't want to regenerate the manifest after every
  edit.
- `off` — skip the check entirely (no audit event).

After any intentional edit to a hook script, regenerate the manifest:

```
python3 .ai-engineering/scripts/regenerate-hooks-manifest.py
```

Run with `--check` in pre-commit / CI to fail loudly on stale manifests
without rewriting the file.

The deny rules in `.claude/settings.json` are tracked in source control
— treat them and the hooks manifest as read-only at the IDE layer.

### Runtime layer hooks

Spec-116 added a runtime layer that closes the harness gaps surfaced by
the 2026 industry survey (Fowler, Osmani, OpenAI Codex, Anthropic):

- **`runtime-progressive-disclosure.py`** (UserPromptSubmit) — ranks the
  49 skills against the incoming prompt and surfaces the top-K so the
  model considers a focused slash command before going free-form. No
  effect on prompts that already start with `/ai-*`.
- **`runtime-guard.py`** (PostToolUse) — combines tool-call offload and
  loop detection. Outputs above `AIENG_TOOL_OFFLOAD_BYTES` (default 4
  KB) move to `.ai-engineering/state/runtime/tool-outputs/<id>.txt`
  with head + tail kept inline. A sliding window
  (`AIENG_LOOP_WINDOW`, default 6) flags repeated signatures or
  failures (`AIENG_LOOP_REPEAT_THRESHOLD`, default 3) and emits a
  `framework_error` of kind `loop_detected`.
- **`runtime-stop.py`** (Stop) — writes
  `.ai-engineering/state/runtime/checkpoint.json` (active work-plane,
  recent edits, last tool calls) and, when the recent history shows
  failure markers, stamps `runtime/ralph-resume.json` so `/ai-start`
  can resume mid-task. The Ralph retry counter is bounded by
  `AIENG_RALPH_MAX_RETRIES` (default 5).
- **`runtime-compact.py`** (PreCompact + PostCompact) — snapshots
  critical runtime state before context compaction (Anthropic: "never
  rely on compaction for critical rules") and emits a verification
  event afterwards.
- **Ralph Loop convergence** (in `runtime-stop.py` + `_lib/convergence.py`)
  — convergence sweep on Stop. Fast mode runs `ruff check` +
  `pytest --collect-only` (~5s budget); full mode adds `pytest -x` and
  `ruff format --check` (~60s budget). Missing tools fail-open
  (treat as converged). On non-converged state emits `ralph_reinject`
  telemetry and increments `runtime/ralph-resume.json`. **Reinjection
  is opt-in**: default observes only and never writes
  `decision: block` to stdout (avoids trapping repos with pre-existing
  lint/test debt). Set `AIENG_RALPH_BLOCK=1` to enable the actual
  reinjection path. `AIENG_RALPH_DISABLED=1` skips the convergence
  sweep entirely. Bounded by `AIENG_RALPH_MAX_RETRIES` (default 5,
  ceiling 50).
- **Risk accumulator (PRISM-style)** (in `_lib/risk_accumulator.py` +
  wired into `prompt-injection-guard.py` and `runtime-guard.py`) —
  per-session risk score with exponential decay and threshold ladder.
  Severity mapping: `LOW=1`, `MEDIUM=5`, `HIGH=20`, `CRITICAL=50`.
  Threshold ladder: `silent < 10 ≤ warn < 30 ≤ block < 60 ≤ force_stop`.
  TTL decay `0.95^minute` (~13.5 min half-life, 0.1 noise floor).
  Repeat-signal weighting: `1.5x` for 1 prior fire of the same IOC in
  60 min, `2.5x` for 2+ fires. Block / force_stop applied by
  `prompt-injection-guard.py` (exit 2 + framework_error). Warn surfaced
  by `runtime-guard.py` as a hint in `additionalContext`. Disable via
  `AIENG_RISK_ACCUMULATOR_DISABLED=1`. State at
  `.ai-engineering/state/runtime/risk-score.json` (gitignored,
  session-scoped, atomic writes, corruption-tolerant).

Tunables (all optional, env-driven):

```
AIENG_TOOL_OFFLOAD_BYTES         # default 4096
AIENG_TOOL_OFFLOAD_HEAD          # default 1024
AIENG_TOOL_OFFLOAD_TAIL          # default 512
AIENG_LOOP_WINDOW                # default 6
AIENG_LOOP_REPEAT_THRESHOLD      # default 3
AIENG_TOOL_HISTORY_MAX           # default 500
AIENG_RALPH_MAX_RETRIES          # default 5
AIENG_RALPH_BLOCK                # default 0 (observe-only)
AIENG_RALPH_DISABLED             # default 0
AIENG_RISK_ACCUMULATOR_DISABLED  # default 0
AIENG_HOOK_INTEGRITY_MODE        # default warn (set to enforce in CI)
```

State lives under `.ai-engineering/state/runtime/`. Checkpoint and
tool-history files are intentionally local (gitignored) — they capture
session state, not source of truth.

### Cross-IDE coverage

The runtime layer hooks are cross-IDE: a single Python script per
primitive runs unchanged across Claude Code, Codex, Gemini CLI, and
GitHub Copilot via `_lib/hook_context.py:get_hook_context()`. Wiring
lives in each IDE's native config file. Event-name mapping:

| Primitive                         | Claude Code  | Codex            | Gemini       | Copilot              |
|-----------------------------------|--------------|------------------|--------------|----------------------|
| Progressive disclosure            | UserPromptSubmit | UserPromptSubmit | BeforeAgent  | userPromptSubmitted  |
| Tool-call offload + loop detect   | PostToolUse  | PostToolUse      | AfterTool    | postToolUse          |
| Checkpoint + Ralph Loop           | Stop         | Stop             | AfterAgent   | sessionEnd           |
| Pre/Post compact snapshot         | PreCompact / PostCompact | ❌ (event missing) | ❌ | ❌ |

PreCompact / PostCompact are Claude-Code-only — the other runtimes do
not surface compaction events, so the snapshot primitive degrades
gracefully there (compaction still happens; it just isn't observed).
Copilot uses bash + PowerShell wrappers
(`copilot-runtime-{guard,stop,progressive-disclosure}.{sh,ps1}`) that
translate the Copilot payload shape to the Claude convention before
delegating to the canonical Python script.

## Hot-Path Discipline

Claude Code triggers pre-commit and pre-push hooks on every save/commit, so
the local critical path must stay fast:

- **Pre-commit budget**: under 1 second wall-clock for the deterministic
  Layer-1 gate (lint, format check, secret scan on staged hunks only).
- **Pre-push budget**: under 5 seconds for the residual checks before the
  push pipeline takes over.
- Anything heavier (full test suite, dependency audit, governance
  evaluation) belongs in CI, not on the local hot path.

If a check exceeds budget, profile it and move work off the hot path before
adding new logic to the hook.

## Token Efficiency Tips

- Use `/clear` when context is no longer load-bearing rather than letting
  the conversation balloon — Claude Code keeps the full transcript in
  context until cleared.
- For deep codebase research, dispatch the `ai-explore` agent (read-only,
  fresh context) instead of having the main thread read the whole tree.
- Cite files with `startLine:endLine:filepath`; never paste large code
  blocks the user did not ask for.
- Treat `/ai-start` as the session bootstrap — it loads only what the
  current task needs and avoids re-reading already-loaded context.

## Observability

Telemetry is automatic — refer to
[AGENTS.md → Skills Available → `/ai-start`](./AGENTS.md#skills-available)
for the bootstrap that registers hooks. Session discovery and transcript
viewing are delegated to the separately installed `agentsview` companion
tool.

### Audit observability (spec-120)

The framework projects the NDJSON audit stream into a SQLite database
and an OTLP/JSON exporter so sessions become queryable and portable.
See [AGENTS.md → Audit observability (spec-120)](./AGENTS.md#audit-observability-spec-120)
for the field-mapping reference; the five subcommands are:

```bash
ai-eng audit index                       # build / refresh the SQLite projection
ai-eng audit query "SELECT ..."          # read-only SQL over the index
ai-eng audit tokens --by skill|agent|session   # token rollup
ai-eng audit replay --session <id>       # depth-first span-tree walk
ai-eng audit otel-export --trace <id>    # OTLP/JSON envelope (Langfuse, Phoenix, …)
ai-eng audit otel-tail --collector <url> # live stream to OTLP/JSON collector (P4.1)
```

The otel-tail subcommand (added 2026-05-04 / harness gap closure)
turns the audit log into a live stream. Tested collector endpoints:

* **Langfuse**: http://localhost:3000/api/public/otel/v1/traces
  (self-hosted) or https://cloud.langfuse.com/api/public/otel/v1/traces.
* **Phoenix**: http://localhost:6006/v1/traces (local) or the
  managed endpoint.
* **Generic OTLP/HTTP collector** (otel-collector-contrib, Tempo,
  Honeycomb, etc.): http://<host>:4318/v1/traces.

The tail loop fail-soft on POST failures: dropped batches emit a
framework_error event (error_code = otel_tail_post_failed) so
the audit chain itself records the gap.
