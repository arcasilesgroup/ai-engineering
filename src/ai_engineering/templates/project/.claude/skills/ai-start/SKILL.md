---
name: ai-start
description: "Bootstraps a coding session: loads project context and displays a welcome dashboard with recent activity, board items, and available commands. Trigger for 'hello', 'lets start', 'good morning', 'whats the status', 'get me up to speed', 'I am back'. Also invokable mid-session to re-bootstrap. Not for human onboarding; use /ai-onboard instead. Not for governance review; use /ai-governance instead."
effort: mid
argument-hint: ""
---

# Start

Bootstraps a coding session: a deterministic Python script (`session_bootstrap.py`) renders the whole welcome dashboard, so the agent runs one command, prints the markdown verbatim, and stops. Re-probing git/sqlite/manifests/board APIs agent-side blows the latency budget (operator-pain #18b), so the script collects every field and caches the board call — cold path <3 s with board, warm path <500 ms.

## Workflow

Principles: §10.1 KISS (one deterministic command; zero agent-side re-derivation).

1. Run exactly this argv — literal, no flags moved, no shell added:

```
uv run python .ai-engineering/scripts/session_bootstrap.py --format=markdown
```

2. Print its stdout verbatim and stop. That is the whole skill.
3. This exact argv is enrolled in the trusted-script lane (`hooks-manifest.json` `trustedArgvs`, D-131-12) so it bypasses RTK rewriting + IOC re-evaluation. Any other form (reordered flags, plain `python3`, missing `--format`) falls back to the full IOC path and degrades latency.

### Hard rules

- Do NOT read the manifest, run `git`, query `sqlite`, hit `gh`, glob the skills/agents tree, or count `LESSONS.md` from the agent side — the script already embedded all of that in the markdown.
- Do NOT rewrite the emitted markdown. The format is the cross-IDE contract (Claude Code, Codex, Antigravity, Copilot render the same bytes).
- Do NOT invoke `/ai-session-watch` from here. Observation is always-on via `PreToolUse`+`PostToolUse` hooks (`instinct-observe.py`), consolidated at session end by the `Stop` hook (`instinct-extract.py`). The dashboard surfaces an `N to review` CTA when the unconsolidated backlog exceeds `observations/meta.json` `deltaThreshold`; operators then run `/ai-session-watch --review` manually.

### What the dashboard already contains

Trust the emitted markdown — do not re-render any of these agent-side:

- **Project identity**: CONSTITUTION mission as tagline.
- **Stack posture**: `surfaces.enabled` · `gates.mode` (one line, so layer drift is obvious).
- **Counts**: skills, agents, lessons, active decisions, accepted risks, recent_events_7d.
- **Active work**: spec id + state + title, plan status (incl. `shipped-pending-pr-merge` per `plan-schema.md`), task progress.
- **Recent commits**: last 5 SHA + subject.
- **Recent lessons**: last 3 `### ` headers from `LESSONS.md` with a gist line (context prefix stripped server-side).
- **Board**: full per-status breakdown via paginated GraphQL (no sample-size truncation).
- **Compatibility**: `### ⚠ Compatibility` block appears only when the manifest deviates from defaults (today: `gates.mode != regulated`).

### Board behaviour

- The script handles `gh project item-list` with a hard 4 s subprocess timeout and a stale-while-revalidate cache at `.ai-engineering/runtime/board-cache.json` (fresh ≤60 s, stale-allowed up to 5 min).
- On board failure the JSON sets `board_summary.unavailable: true` and the markdown shows `board unavailable (reason)` — never blocks the rest of the dashboard.

### When the script is unavailable

If the script exits non-zero or the venv has no `uv`, fall back to a one-line banner: `ai-start unavailable — repo not bootstrapped, run \`ai-eng install\`.` Do NOT reconstruct the dashboard by hand.

## Examples

```
/ai-start
```

Runs the script, prints the dashboard (active spec, last 5 commits, board items by status, project counts, quick-action chips), stops. Mid-session re-bootstrap after `/clear` uses the same single command; a fresh board cache makes it near-instant.

## Integration

- **Called by**: user directly; IDE instruction files (FIRST ACTION mandate per CONSTITUTION).
- **Calls**: `session_bootstrap.py --format=markdown` (only).
- **Does not call**: `/ai-session-watch`, `/ai-board discover`, manifest readers, or any other skill. Suggestions (e.g. "no active spec — run `/ai-brainstorm`") are embedded inside the emitted markdown.
- **See also**: `/ai-onboard` (human onboarding, different audience), `/ai-branch-cleanup` (pre-start hygiene).
