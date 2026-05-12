# Getting Started

3-minute path from clone to merged PR. No ceremony. No internals.

You are here: first time using ai-engineering. By the end you will
have shipped a real PR through the canonical chain.

## Frame 1 — Install

```bash
git clone https://github.com/arcasilesgroup/ai-engineering.git
cd ai-engineering
ai-eng install .
```

`install` answers two yes/no prompts (telemetry, IDE) and scaffolds the
governance root in your project. All defaults are safe. Engram is no
longer prompted during install — see
[docs/integrations/engram.md](integrations/engram.md) if you want to
wire it up separately.

## Frame 2 — `/ai-start`

Open your IDE (Claude Code, Copilot, Gemini, or Codex) and run:

```
/ai-start
```

You will see a dashboard: current branch, active spec, board state,
and a single next-action arrow pointing at the next command.

## Frame 3 — `/ai-brainstorm`

Tell the framework what you want to build:

```
/ai-brainstorm "I want to add a CSV export for the dashboard"
```

A 3-question interrogation refines the idea. The output is a
patch-ready `spec.md` saved at `.ai-engineering/specs/spec.md`.

## Frame 4 — `/ai-plan`

Decompose the spec into executable tasks:

```
/ai-plan
```

The plan lands with patch hunks per task and a checklist. Approve it
by typing `apruebo` (or your reviewer keyword).

## Frame 5 — `/ai-build` then `/ai-pr`

Execute the plan. For multi-concern specs use `/ai-autopilot` instead.

```
/ai-build
/ai-pr
```

`/ai-build` runs the tasks. A single final quality loop runs verify
and review on the full changeset. Blockers stop and ask you. Clean
runs flow into `/ai-pr`, which commits, pushes, opens the pull
request, and waits for green CI before merging.

You shipped a PR through the canonical chain. End.

See [AGENTS.md](../AGENTS.md) for the full canonical chain and
engineering principles.
