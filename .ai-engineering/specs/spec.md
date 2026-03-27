# Spec 080 - Hook Simplification and Instinct Learning v1

Status: draft
Created: 2026-03-27

## Problem

The current hook surface is only partially aligned between Claude Code and GitHub Copilot, still carries legacy naming, and includes capabilities that are either host-specific or not fully functional. In particular:

- `instinct-extract` is incomplete because it has no complete observation pipeline feeding it.
- `auto-format` and `strategic-compact` are not fully automatic across both IDEs.
- `cost-tracker` adds host-specific complexity without enough value for the framework.
- The current instinct direction risks recreating ECC-scale complexity inside `ai-engineering`.

## Goals

- Make `auto-format`, `strategic-compact`, and instinct capture/extraction fully automatic and robust in both Claude Code and GitHub Copilot.
- Keep the learning pipeline local-first, simple, and low-maintenance.
- Capture enough session/tool data to enable useful instinct consolidation without background daemons or always-on analysis.
- Generate a bounded instinct context that can be consumed efficiently at session start.
- Clean up hook naming so the canonical logic and IDE adapters are obvious.

## Non-Goals

- `cost-tracker`
- observer daemon, PID files, signals, or background processes
- promotion/evolution/global instincts in v1
- confidence scoring systems
- transcript storage
- raw tool payload retention
- dashboards or viewer logic inside `ai-engineering`
- Copilot per-agent hook dependency for retained capabilities

## Chosen Direction

Use ECC as a reference for observation capture patterns, sanitization, and compact suggestion logic, but do not replicate its daemon, global scope, promotion, evolution, or homunculus storage model.

`ai-engineering` v1 should:

- capture observations automatically in hooks
- consolidate instincts using a skill plus LLM during `onboard`
- persist instincts in a single project-local canonical file
- generate a small derived context file for session loading

## Decisions

- Remove `cost-tracker` from `ai-engineering`.
- Keep `auto-format` and make it fully automatic in Claude Code and GitHub Copilot.
- Keep `strategic-compact` and make it fully automatic in Claude Code and GitHub Copilot.
- Keep instinct learning, but redesign it around observation capture plus explicit LLM consolidation.
- Store raw observations at `.ai-engineering/state/instinct-observations.ndjson`.
- Store canonical project instincts at `.ai-engineering/instincts/instincts.yml`.
- Store the derived bounded context at `.ai-engineering/instincts/context.md`.
- Store consolidation bookkeeping at `.ai-engineering/instincts/meta.json`.
- Consolidate instincts during `onboard`, not during `brainstorm`.
- Trigger consolidation when there is enough new observation delta or the derived context is too old.
- Retain observations for 30 days.
- Use canonical hook names plus IDE adapters:
  - `auto-format.py` + `copilot-auto-format.sh`
  - `strategic-compact.py` + `copilot-strategic-compact.sh`
  - `instinct-observe.py` + `copilot-instinct-observe.sh`
  - `instinct-extract.py` + `copilot-instinct-extract.sh`

## Functional Requirements

### 1. Hook Parity

Claude Code and GitHub Copilot must both run these capabilities automatically:

- `auto-format`
- `strategic-compact`
- `instinct-observe`
- `instinct-extract`

For these retained capabilities, Copilot must not rely on optional per-agent hook settings.

### 2. Observation Capture

Pre-tool and post-tool hooks must write sanitized observations to `.ai-engineering/state/instinct-observations.ndjson`.

The observation stream must be sufficient to derive:

- repeated tool sequences
- error recovery patterns
- skill-to-agent and agent-to-skill preferences

The observation stream must exclude:

- transcripts
- raw tool payloads
- large unbounded inputs or outputs
- secrets and credential-like strings

### 3. Instinct Consolidation

`onboard` is responsible for deciding whether instinct consolidation should run.

The consolidation decision must use:

- new observation delta since the last consolidation
- age of `.ai-engineering/instincts/context.md`

When consolidation runs, it must use:

- recent observation delta
- existing `.ai-engineering/instincts/instincts.yml`
- LLM assistance via instinct skill flow

The consolidation flow must update:

- `.ai-engineering/instincts/instincts.yml`
- `.ai-engineering/instincts/context.md`
- `.ai-engineering/instincts/meta.json`

### 4. Instinct Scope

Instincts are project-local only in v1.

There is no:

- global instinct store
- promotion
- evolution
- `personal`/`inherited` split
- background observer

### 5. Context Consumption

Downstream skills and session-start flows should consume `.ai-engineering/instincts/context.md`, not raw observations or raw instinct YAML.

The derived context must stay intentionally small and optimized for context efficiency.

### 6. Retention

`.ai-engineering/state/instinct-observations.ndjson` must retain only the last 30 days of observations.

Retention must be enforced automatically and locally without archive pipelines or external services.

## Data Artifacts

- `.ai-engineering/state/instinct-observations.ndjson`
- `.ai-engineering/instincts/instincts.yml`
- `.ai-engineering/instincts/context.md`
- `.ai-engineering/instincts/meta.json`

## Success Criteria

- Claude Code and GitHub Copilot both run `auto-format`, `strategic-compact`, `instinct-observe`, and `instinct-extract` automatically after standard install.
- `instinct-extract` is end-to-end functional because observations are actually captured before extraction.
- `onboard` can consolidate instinct knowledge without daemons, observers, or background workers.
- `.ai-engineering/instincts/context.md` stays bounded and useful for session start.
- Legacy naming is reduced and retained hook capabilities are clearly organized into canonical logic plus IDE adapters.
- `cost-tracker` is removed from the supported framework surface.

## Implementation Notes for Planning

- Exact thresholds for "enough delta" and "context too old" are implementation details to resolve in `/ai-plan`.
- ECC should be treated as a source of capture and sanitization patterns, not as an architecture to copy wholesale.
