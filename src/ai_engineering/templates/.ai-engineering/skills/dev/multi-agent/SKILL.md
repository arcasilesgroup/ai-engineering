---
name: multi-agent
description: "Coordinate multiple agent personas in parallel or sequence using Task tool patterns; use for full-spectrum audits, cross-cutting reviews, or batch operations."
version: 1.0.0
category: dev
tags: [orchestration, parallel, agents, task-tool]
metadata:
  ai-engineering:
    scope: read-only
    token_estimate: 1125
---

# Multi-Agent Orchestration

## Purpose

Patterns for coordinating multiple agent personas in parallel or sequence. Covers parallel execution via Task tool, result consolidation, workspace isolation, and common orchestration recipes for audits, reviews, and spec work.

## Trigger

- Command: agent invokes multi-agent skill or user requests parallel agent execution.
- Context: full-spectrum audits, cross-cutting reviews, parallel spec phases, batch operations across multiple files or domains.

## When NOT to Use

- **Single-agent tasks** — if the work fits one agent persona, invoke that agent directly.
- **Sequential dependency chains** — if each step depends on the previous result, use a single agent with phased procedure.
- **Simple tool parallelism** — if you just need parallel Glob/Grep/Read calls, use multiple tool calls in one message without this skill.

## Procedure

### Pattern 1: Parallel Audit

Launch multiple specialized agents simultaneously for comprehensive assessment.

1. **Identify audit dimensions** — determine which agents cover the scope:
   - `agent:security-reviewer` — security findings.
   - `agent:quality-auditor` — quality metrics.
   - `agent:architect` — architecture assessment.
   - `agent:docs-writer` — structural documentation.

2. **Launch agents in parallel** — use Task tool with `subagent_type` in a single message:
   ```
   Task(subagent_type="general-purpose", prompt="Activate agent:security-reviewer. Scan...")
   Task(subagent_type="general-purpose", prompt="Activate agent:quality-auditor. Run...")
   Task(subagent_type="general-purpose", prompt="Activate agent:architect. Analyze...")
   ```

3. **Consolidate results** — after all agents complete, merge findings:
   - Deduplicate overlapping findings.
   - Resolve conflicting assessments (security vs performance trade-offs).
   - Produce unified report with per-dimension sections.

### Pattern 2: Parallel Review

Run code review and security review simultaneously on the same changeset.

1. **Launch review agents** — two Task calls in one message:
   - `dev:code-review` focused on correctness and patterns.
   - `review:security` focused on vulnerabilities.

2. **Merge review feedback** — combine into single review output:
   - Security findings take priority over style suggestions.
   - Deduplicate items found by both reviewers.

### Pattern 3: Batch File Operations

Apply the same transformation across many files in parallel.

1. **Partition files** — split the target file list into groups (max 10-15 files per agent).
2. **Launch one agent per partition** — each agent processes its file group independently.
3. **Verify consistency** — after all agents complete, spot-check results for consistency.

### Pattern 4: Workspace Isolation with Git Worktrees

For operations that modify files, use git worktrees to avoid conflicts.

1. **Create worktrees** — one per parallel workstream:
   ```bash
   git worktree add -b task/agent-1 /tmp/agent-1 HEAD
   git worktree add -b task/agent-2 /tmp/agent-2 HEAD
   ```

2. **Launch agents with isolated workdirs** — each agent operates in its own worktree.

3. **Merge results** — after agents complete:
   - Review changes in each worktree.
   - Cherry-pick or merge branches back.
   - Remove worktrees: `git worktree remove /tmp/agent-1`.

### Pattern 5: Structured Context Gathering

Dispatch read-only agents to gather and summarize context before planning or auditing.

1. **Identify context dimensions** — determine what areas need exploration:
   - Governance surface (`.ai-engineering/` — skills, agents, standards, state)
   - Implementation surface (`src/`, `scripts/`, `tests/`)
   - Integration surface (`.claude/`, `.github/`, CI/CD workflows)

2. **Launch explorer agents** — max 3 in parallel, each with a focused scope:
   ```
   Task(subagent_type="Explore", prompt="Explore governance surface: skills inventory, agent capabilities, standards structure, state files...")
   Task(subagent_type="Explore", prompt="Explore implementation surface: Python modules, CLI commands, test coverage...")
   Task(subagent_type="Explore", prompt="Explore integration surface: command mirrors, CI workflows, IDE config...")
   ```

3. **Structured output** — each agent MUST produce a context summary per framework-contract §4.7:
   - `## Findings` — key observations and discovered patterns.
   - `## Dependencies Discovered` — cross-file and cross-module dependencies.
   - `## Risks Identified` — gaps, inconsistencies, staleness.
   - `## Recommendations` — suggested actions for the planning phase.

4. **Consolidate** — the dispatching agent merges all summaries:
   - Deduplicate overlapping findings across agents.
   - Resolve conflicts using priority: security > governance > quality > style.
   - Build unified dependency graph from individual discoveries.

5. **Use as input** — consolidated context feeds Pattern 1 (audit), direct planning, or orchestrator PLANNING mode.

### Safety Rules

- **Max parallel agents**: 3 (avoid context fragmentation and resource contention).
- **Read-only by default**: parallel agents should read and report, not modify, unless using workspace isolation.
- **No shared state mutation**: parallel agents must not write to the same files simultaneously.
- **Result validation**: always review consolidated output before acting on it.

## Output Contract

- Per-agent results with clear source attribution.
- Consolidated report with deduplication and conflict resolution.
- Execution summary: agents launched, duration, findings per agent.

## Governance Notes

- Multi-agent orchestration does not bypass governance gates — each agent must follow its own governance rules.
- Parallel modifications to governance content (`.ai-engineering/`) are prohibited — use sequential execution for governance changes.
- Decision store writes must be serialized — only one agent may write to `decision-store.json` at a time.
- Audit log appends are safe for parallel execution (append-only).

## References

- `agents/platform-auditor.md` — orchestrates 8 audit dimensions (uses pattern 1).
- `agents/principal-engineer.md` — cross-cutting review perspective.
- `agents/security-reviewer.md` — security-focused review agent.
- `agents/quality-auditor.md` — quality gate enforcement agent.
- `skills/dev/code-review/SKILL.md` — code review skill (used in pattern 2).
- `skills/review/security/SKILL.md` — security review skill (used in pattern 2).
