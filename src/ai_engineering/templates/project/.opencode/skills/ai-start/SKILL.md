---
name: ai-start
description: "Bootstraps a coding session: loads project context, activates session observation, displays a welcome dashboard with recent activity, board items, and available commands. Trigger for 'hello', 'lets start', 'good morning', 'whats the status', 'get me up to speed', 'I am back'. Also invokable mid-session to re-bootstrap. Not for human onboarding; use /ai-onboard instead. Not for governance review; use /ai-governance instead."
effort: mid
argument-hint: 
model_tier: sonnet
mirror_family: codex-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-start/SKILL.md
edit_policy: generated-do-not-edit
---


# Start

## Purpose

Session welcome dashboard. The dashboard is fully rendered by a deterministic
Python script (`session_bootstrap.py`). The IDE agent does no per-field
derivation — it runs **exactly one command**, prints the markdown verbatim,
and stops.

Why this contract exists: re-probing git, sqlite, manifests, board APIs, etc.
from the IDE side blows the latency budget (operator-pain #18b). The script
collects every field, caches the board call (stale-while-revalidate), and
emits ready-to-display markdown. Cold path: < 3 s wall (with board). Warm
path: < 500 ms.

## Process

Run exactly this argv — literal, no flags moved or shells added — and print
its stdout verbatim:

```
uv run python .ai-engineering/scripts/session_bootstrap.py --format=markdown
```

That is the whole skill. The script is enrolled in the trusted-script lane
(`hooks-manifest.json` `trustedArgvs`, D-131-12) so this exact argv bypasses
RTK rewriting and IOC re-evaluation. Any other invocation form (positional
flag order changes, plain `python3`, missing `--format`) falls back to the
full IOC path and degrades latency.

### Hard rules

- Do **not** read the manifest, run `git`, query `sqlite`, hit `gh`, glob
  the skills/agents tree, or count `LESSONS.md` from the agent side. The
  script already did all of that and embedded the result inside the
  markdown payload.
- Do **not** rewrite the markdown the script emits. The format is the
  cross-IDE contract (Claude Code, Codex, Antigravity, Copilot all render
  the same bytes).
- Do **not** invoke `/ai-session-watch` from inside this skill. Observation is
  always-on via the `PreToolUse` + `PostToolUse` hooks (`instinct-
  observe.py`) and consolidated at session end by the `Stop` hook
  (`instinct-extract.py`). The dashboard surfaces an `N to review`
  CTA when the unconsolidated backlog exceeds the
  `observations/meta.json` `deltaThreshold` — operators run
  `/ai-session-watch --review` manually when they see that CTA.

### What the dashboard already contains

Trust the markdown the script emits. It surfaces every field the
operator typically asks for next:

- **Project identity**: the CONSTITUTION mission as the tagline.
- **Stack posture**: `surfaces.enabled` ·
  `gates.mode` — visible in one line so layer drift is obvious.
- **Counts**: skills, agents, lessons, active decisions, accepted
  risks, recent_events_7d.
- **Active work**: spec id + state + title, plan status (including the
  `shipped-pending-pr-merge` exemption per `plan-schema.md`),
  task progress.
- **Recent commits**: last 5 SHA + subject from `git log`.
- **Recent lessons**: last 3 `### ` headers from `LESSONS.md` with a
  gist line (no `**Context**:` prefix noise — stripped server-side).
- **Board**: full per-status breakdown via paginated GraphQL (no
  sample-size truncation).
- **Compatibility**: a `### ⚠ Compatibility` block appears only when
  the manifest deviates from defaults (today: `gates.mode != regulated`).

Do not duplicate or re-render any of these from the agent side.

### Board behaviour

The script handles the `gh project item-list` call with a hard 4 s
subprocess timeout and a stale-while-revalidate cache at
`.ai-engineering/runtime/board-cache.json` (fresh ≤ 60 s, stale-allowed up
to 5 min). On board failure the JSON includes `board_summary.unavailable:
true` and the markdown shows `board unavailable (reason)` — never blocks
the rest of the dashboard.

### When the script is unavailable

If the script exits non-zero or the venv has no `uv`, fall back to a
one-line banner: `ai-start unavailable — repo not bootstrapped, run \`ai-eng
install\`.` Do **not** reconstruct the dashboard by hand.

## Examples

### Example 1 — morning bootstrap

```
/ai-start
```

Runs the script, prints the dashboard, stops. The dashboard already lists
the active spec, last 5 commits, board items by status, project counts,
and the quick-action chips.

### Example 2 — mid-session re-bootstrap after `/clear`

```
/ai-start
```

Same single command. The board cache (if still fresh) makes this nearly
instantaneous.

## Integration

- **Called by**: user directly; IDE instruction files (FIRST ACTION mandate
  per CONSTITUTION).
- **Calls**: `session_bootstrap.py --format=markdown` (only).
- **Does not call**: `/ai-session-watch`, `/ai-board discover`, manifest readers,
  or any other skill. Suggestions (e.g. "no active spec — run
  `/ai-brainstorm`") are embedded inside the markdown the script emits.
- **See also**: `/ai-onboard` (human onboarding, different audience),
  `/ai-branch-cleanup` (pre-start hygiene).
