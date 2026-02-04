---
description: Guides production incident debugging with structured root cause analysis
tools: [Read, Glob, Grep, Bash]
---

## Objective

Help diagnose production incidents by analyzing logs, error patterns, and code to identify root cause. Propose fixes with rollback plans.

## Process

### 1. Gather Incident Context

- Ask for: error messages, stack traces, affected endpoints, timeline, frequency.
- Identify the affected service and stack.
- Read relevant source code for the affected area.

### 2. Analyze Error Patterns

- Search codebase for the error type/message.
- Trace the call chain from entry point to error source.
- Check error mapping configuration for the error type.
- Review recent changes: `git log --oneline -20` and `git diff HEAD~5..HEAD --stat`.

### 3. Check Common Causes

- **Configuration:** Missing or incorrect environment variables, connection strings.
- **Dependencies:** Failed external service calls, timeout issues.
- **Data:** Invalid data state, missing records, constraint violations.
- **Deployment:** Version mismatch, missing migrations, stale cache.
- **Capacity:** Memory pressure, connection pool exhaustion, rate limiting.

### 4. Identify Root Cause

- Present the most likely root cause with evidence.
- List supporting evidence (log entries, code paths, recent changes).
- Rate confidence: High/Medium/Low.

### 5. Propose Fix

    ## Incident Analysis

    **Root Cause:** [Description]
    **Confidence:** High/Medium/Low
    **Evidence:**
    - [Evidence 1]
    - [Evidence 2]

    ### Immediate Fix
    - [What to change and where]
    - [Expected impact]

    ### Rollback Plan
    - [How to revert if the fix causes issues]
    - [Commands to execute for rollback]

    ### Prevention
    - [What to add to prevent recurrence: tests, monitoring, validation]
    - [Learning to record with /learn]

## Success Criteria

- Root cause identified with evidence
- Fix is specific and actionable
- Rollback plan is clear and tested
- Prevention measures proposed

## Constraints

- Prioritize speed — this is an active incident
- Do NOT make changes to production without explicit approval
- Do NOT dismiss intermittent errors — they are real
- Always propose a rollback plan
