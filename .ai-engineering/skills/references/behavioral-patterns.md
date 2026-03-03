# Behavioral Patterns

Standard behavioral patterns that agents and skills should adopt. These patterns were identified through cross-industry analysis of 35+ AI tool system prompts (Claude Code, Cursor, Windsurf, Devin, Manus, Kiro, Amp, Google Antigravity, RooCode, Bolt, v0, Same.dev, Orchids) and codified as framework norms.

## Escalation Ladder

All agents and procedural skills must implement iteration limits:

- **Max 3 attempts** to resolve the same issue before escalating to the user.
- Each attempt must try a **different approach** — repeating the same action is not a valid retry.
- **Escalation format**: present what was tried, what failed, and options for the user.
- **Never loop silently**: if stuck, surface the problem immediately.

Agents implement this in `## Boundaries → ### Escalation Protocol`. Skills implement this in `## Governance Notes → ### Iteration Limits`.

## Confidence Signaling

Read-only audit and review agents include a confidence signal in their output:

- **Confidence**: HIGH (0.8-1.0) | MEDIUM (0.5-0.79) | LOW (0.0-0.49) — with brief justification.
- **Blocked on user**: YES/NO — whether user input is needed to proceed.

Applicable agents: review, scan.

## Post-Edit Validation

Read-write agents and skills must validate after every file modification:

- **Code files**: run applicable linter (`ruff check` + `ruff format --check` for Python).
- **Governance files** (`.ai-engineering/`): run `integrity-check`.
- **Never proceed** to the next step if validation fails — fix first, then continue.

Agents implement this as an explicit behavior step. Skills implement this in `## Governance Notes → ### Post-Action Validation`.

## Headless Mode

Interactive skills that normally prompt for user input must provide a headless fallback:

- **Default to standard options** when no user input is available (e.g., Standard depth, complete output).
- **Skip interactive follow-up** prompts and generate complete output directly.
- **Note assumptions** made in headless mode so the user can adjust after the fact.

## When NOT to Use (Routing)

Skills with high confusion risk must include a `## When NOT to Use` section that routes users to the correct skill:

- List 2-4 common misuse scenarios with the correct alternative skill.
- Format: `**<Scenario>** — use `<correct-skill>` instead. <Brief reason>.`
- This prevents skill confusion and reduces wasted execution.

## Holistic Analysis Before Action

Agents and skills must analyze the full system context before modifying any file:

- **Read affected dependencies**: before editing a file, identify its importers/consumers and assess downstream impact.
- **Anticipate cascading changes**: if modifying a shared module, enumerate all callers and verify none will break.
- **No isolated edits**: treat each change as part of a system, not a standalone fix.
- **Implementation**: agents add a "Map context" or "Analyze dependencies" step before any edit step in their Behavior section.

Derived from audit patterns: Leap.new (holistic thinking protocol), Manus (event stream analysis), Google Antigravity (Knowledge Item context).

## Exhaustiveness Requirement

When a skill or agent identifies N issues, ALL N must be addressed or explicitly deferred with rationale:

- **No partial solutions**: if a review finds 5 issues, all 5 must appear in the output — not just the first 3.
- **No early exits**: complete all procedure steps. If a step is not applicable, state why and proceed.
- **Explicit deferral**: if an issue cannot be resolved in the current scope, log it with rationale and severity.
- **Implementation**: skills include "Enumerate all findings before proceeding" in their procedure. Agents include "Validate completeness against initial scope" in their final steps.

Derived from audit patterns: Comet (no early exits), Same.dev (complete resolution required), Trae (task state completion enforcement).

## Parallel-First Tool Execution

When multiple independent operations are needed, execute them in parallel by default:

- **Default to parallel**: when checks, scans, or reads have no data dependencies, batch them.
- **Sequential only on dependency**: explicitly document why sequential execution is needed when used.
- **Batch operations**: minimize tool round-trips. Group related file reads, lint checks, and scan operations.
- **Implementation**: agents structure their Behavior steps to identify parallelizable operations. Skills document parallelizable vs sequential steps in their procedure.

Derived from audit patterns: Same.dev (emphatic parallel execution), Cursor (parallel tool calls), Lovable (batch tool operations).
