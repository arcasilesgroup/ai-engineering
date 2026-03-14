---
name: guard
description: "Use this skill for proactive governance advisory: check staged changes against standards, validate pre-dispatch governance compliance, detect decision drift. Invoke before committing, during build post-edit validation, or when reviewing architectural alignment."
metadata:
  version: 1.0.0
  tags: [governance, advisory, shift-left, drift, compliance, proactive, guard]
  ai-engineering:
    scope: read-only + read-write (decision-store, audit-log)
    token_estimate: 1200
---

# Guard

## Purpose

Proactive governance advisory skill. Shift-left governance checks that run during development, not after. Three modes: advise (post-edit file analysis), gate (pre-dispatch task validation), drift (decision alignment audit). All modes are fail-open -- guard advises, never blocks.

## Trigger

- Command: `/ai:guard [advise|gate|drift]`
- Implicit: build's post-edit validation invokes `advise` mode
- Implicit: execute's pre-dispatch invokes `gate` mode
- Context: governance review, architectural alignment check, pre-commit advisory

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"guard"}'` at skill start. Fail-open -- skip if ai-eng unavailable.

## When NOT to Use

- **Post-hoc governance audit** -- use `/ai:scan governance` instead. Guard is proactive; scan is forensic.
- **Security vulnerability analysis** -- use `/ai:scan security`. Guard checks governance alignment, not CVEs.
- **Code quality metrics** -- use `/ai:scan quality`. Guard warns about quality threshold trends, not exact measurements.
- **Hard enforcement** -- git hooks handle blocking. Guard advises.
- **Risk acceptance lifecycle** -- use `/ai:risk` to accept, resolve, or renew risks. Guard detects expired decisions but does not manage them.

## Mode: advise

Analyze staged changes or recently modified files against governance policies, standards, and active decisions. Produces advisory warnings integrated into build's post-edit validation loop.

### Procedure

1. **Identify changed files** -- run `git diff --staged --name-only` for staged files. If no staged files, use `git diff --name-only` for unstaged changes. If invoked during build, use the files modified in the current session.

2. **Classify file stacks** -- map each changed file to its stack by extension:
   - `.py` -> Python (standards: `stacks/python.md`)
   - `.cs`, `.csproj` -> .NET (standards: `stacks/dotnet.md`)
   - `.ts`, `.tsx` -> TypeScript (standards: `stacks/typescript.md`)
   - `.tf` -> Terraform (standards: `stacks/infrastructure.md`)
   - `.md`, `.yml` under `.ai-engineering/` -> framework governance

3. **Load applicable standards** -- always load:
   - `standards/framework/core.md` (cross-cutting governance)
   - `standards/framework/quality/core.md` (quality thresholds)
   - Stack-specific standards from step 2

4. **Load active decisions** -- read `state/decision-store.json`, filter:
   - `status == "active"`
   - Decision scope intersects changed files (by path, stack, or domain)
   - Include expired decisions as `concern`-level warnings

5. **Analyze each file** -- check for:
   - **Standard violations**: naming conventions, file placement, import patterns, documentation requirements per stack standard
   - **Boundary crossings**: file modifies a zone it should not (framework-managed vs team-managed per ownership model)
   - **Decision contradictions**: change conflicts with an active architectural decision (e.g., adding a new agent when DEC-002 caps at 7)
   - **Quality trends**: complexity approaching thresholds (cyclomatic > 8 trending toward limit of 10), coverage-impacting changes without test additions
   - **Missing artifacts**: new module without corresponding test file, new skill without manifest update, new agent without catalog entry

6. **Produce warnings** -- for each finding, emit:
   ```yaml
   severity: info | warn | concern
   file: <path>
   finding: <description>
   standard_ref: <standard section, if applicable>
   decision_ref: <decision ID, if applicable>
   recommendation: <actionable fix>
   ```

7. **Emit signal** -- `ai-eng signals emit guard_advisory --actor=guard --detail='{"mode":"advise","files_checked":<N>,"warnings":{"info":<N>,"warn":<N>,"concern":<N>}}'`. Fail-open.

### Fail-Open Contract

If any step fails (file not found, JSON parse error, standard missing), log the error as an `info`-level warning and continue. Guard MUST NOT raise exceptions that interrupt build's workflow. Return partial results over no results.

## Mode: gate

Pre-dispatch governance validation. Before execute dispatches an agent to a task, gate validates the task respects governance boundaries and the agent is appropriate.

### Procedure

1. **Receive dispatch context** -- from execute, receive:
   - Task ID and description
   - Assigned agent name
   - Target files or scope
   - Required capabilities

2. **Load agent definition** -- read `agents/<agent_name>.md`, extract:
   - `scope` (read-only vs read-write)
   - `capabilities` array
   - `boundaries` section

3. **Validate capability match** -- verify every required capability for the task exists in the agent's `capabilities` array. Flag mismatches:
   - `warn`: agent has the capability but it is tangential to the task
   - `concern`: agent lacks a required capability entirely

4. **Validate scope boundaries** -- check:
   - Code write tasks dispatched only to `build` agent
   - Governance content modifications dispatched only to authorized agents
   - Read-only agents not assigned write tasks
   - No agent assigned tasks outside its declared `tags`

5. **Check expired decisions** -- scan `state/decision-store.json` for:
   - Risk acceptances with `expires_at < today` that affect target files
   - Architectural decisions with `expires_at < today` that govern the task scope
   - Flag each expired decision as `concern` with recommendation to resolve or renew

6. **Produce gate verdict**:
   - `PASS` -- no findings, dispatch is safe
   - `WARN` -- findings exist, dispatch can proceed but review recommended
   - Provide findings list with the verdict
   - NEVER produce `BLOCK` -- guard is advisory only

7. **Emit signal** -- `ai-eng signals emit guard_gate --actor=guard --detail='{"mode":"gate","verdict":"<PASS|WARN>","task":"<task_id>","agent":"<agent_name>","findings":<N>}'`. Fail-open.

## Mode: drift

Detect when implementation has drifted from architectural decisions recorded in the decision store. Produces a drift report mapping each active decision to its current alignment status.

### Procedure

1. **Load architectural decisions** -- read `state/decision-store.json`, filter:
   - `status == "active"`
   - `category == "architecture"` (primary) or `category` in `["technology", "pattern", "convention"]` (secondary)

2. **Map decision scope** -- for each decision, determine what to check:
   - Parse `description` for concrete claims (counts, names, patterns, structures)
   - Use `spec` reference to find the originating spec for additional context
   - Identify filesystem paths, configuration files, or code patterns the decision governs

3. **Verify alignment** -- for each decision, execute the appropriate check:
   - **Count decisions** (e.g., "7 agents"): count actual files, compare
   - **Structure decisions** (e.g., "flat skill layout"): verify directory structure matches
   - **Convention decisions** (e.g., "unified namespace"): grep for invocation patterns
   - **Technology decisions** (e.g., "use ruff not flake8"): check configuration and dependencies
   - **Pattern decisions** (e.g., "agents don't write code"): verify boundary compliance

4. **Classify drift severity**:
   - `none` -- implementation matches decision exactly
   - `minor` -- cosmetic deviation, decision intent fully preserved (e.g., naming case difference)
   - `major` -- structural deviation, decision intent partially preserved (e.g., 8 agents when decision says 7, but the extra is justified)
   - `critical` -- implementation contradicts the decision (e.g., multiple agents writing code when decision restricts to build only)

5. **Produce drift report**:
   ```markdown
   # Drift Report

   ## Summary
   - Decisions checked: N
   - Aligned: N | Minor drift: N | Major drift: N | Critical drift: N

   ## Findings
   | Decision ID | Title | Expected | Actual | Drift | Action |
   ```

6. **Recommend actions** -- for each drifted decision:
   - `minor`: document the deviation, consider updating the decision
   - `major`: escalate to plan agent for decision review
   - `critical`: flag for immediate human review, potential spec needed

7. **Emit signal** -- `ai-eng signals emit guard_drift --actor=guard --detail='{"mode":"drift","decisions_checked":<N>,"aligned":<N>,"minor":<N>,"major":<N>,"critical":<N>}'`. Fail-open.

## Integration Points

### With build (advise mode)

Guard.advise runs after build's stack-specific post-edit validation (ruff check, tsc --noEmit, etc.) and before the next file edit. Build's validation loop becomes:

1. Edit file
2. Run stack linter/formatter (ruff, tsc, etc.)
3. Run guard.advise on modified files (fail-open)
4. Proceed to next edit

If guard.advise produces `concern`-level warnings, build should surface them to the user but NOT stop work.

### With execute (gate mode)

Guard.gate runs before execute dispatches each agent. Execute's dispatch loop becomes:

1. Read next task from plan
2. Match task to agent
3. Run guard.gate with dispatch context (fail-open)
4. If WARN: log warnings, proceed with dispatch
5. Dispatch agent

### With scan (complementary)

Guard and scan are complementary, not overlapping:
- Guard runs during development -> catches issues early
- Scan runs after development -> validates the complete result
- Guard findings that persist to scan indicate the advisory was ignored or insufficient

## Governance Notes

- Guard is **advisory only** -- it never blocks, never fails hard, never prevents execution.
- Guard's severity scale (`info`, `warn`, `concern`) is intentionally softer than scan's (`minor`, `major`, `critical`, `blocker`).
- Guard writes only to `state/decision-store.json` (drift annotations) and `state/audit-log.ndjson` (telemetry).
- Guard reads but never modifies source code, standards, or contracts.
- If the decision store is malformed or missing, guard degrades to standards-only checks and logs the issue.

## References

- `skills/governance/SKILL.md` -- shared governance validation (integrity, compliance, ownership)
- `skills/risk/SKILL.md` -- risk acceptance lifecycle for expired-decision context
- `standards/framework/core.md` -- governance structure and ownership model
- `standards/framework/quality/core.md` -- quality thresholds for trend warnings
