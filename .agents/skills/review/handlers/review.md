# Handler: Review

## Purpose

Full parallel code review workflow. Dispatches 8 specialized agents, each analyzing the same diff from a different angle, then aggregates findings with self-challenge and corroboration.

## Procedure

### Step 0 -- Read Manifest Stacks

Read `.ai-engineering/manifest.yml` field `providers.stacks` for the project's declared stacks. Use this as the authoritative stack list for context loading and review dispatch.

### Step 1 -- Gather Context

Before any review agent runs:

1. Dispatch the Explore agent (`ai-explore`) on the changed files to produce an Architecture Map
2. Identify the diff scope: `git diff --stat` for file list, `git diff` for full content
3. Supplement with languages detected in the diff (file extensions) and read:
   - `.ai-engineering/contexts/languages/{lang}.md` for each language found
   - `.ai-engineering/contexts/frameworks/{framework}.md` if framework imports detected
   - `.ai-engineering/contexts/team/*.md` for team conventions
4. Read `decision-store.json` for relevant architectural decisions

### Step 2 -- Dispatch 8 Agents

Each agent reviews the same diff independently. For each agent:

**Input**:
```
You are reviewing code as the [AGENT] specialist.
Context: [Architecture Map from Step 1]
Diff: [full diff]
Standards: [applicable standards]
Focus: [agent-specific focus area]
```

**Each agent produces**:
```yaml
findings:
  - id: [AGENT]-1
    severity: blocker|critical|major|minor|info
    confidence: 20-100
    file: path/to/file
    line: N
    finding: "What is wrong"
    evidence: "Code snippet or reasoning"
    remediation: "How to fix"
    self_challenge:
      counter: "Why this might be acceptable"
      resolution: "Finding stands|withdrawn|severity adjusted"
      adjusted_confidence: N
```

### Step 2b -- Language-Specific Review

For each language detected in the diff:
1. If a dedicated handler exists (`lang-{language}.md`), dispatch it
2. Otherwise, dispatch `lang-generic.md` with the detected language

Dedicated handlers exist for: cpp, flutter, go, java, kotlin, python, rust, typescript.
All other languages use the generic handler.

Language handler findings feed into Step 3 aggregation with the same YAML format.

### Step 3 -- Aggregate and Correlate

After all 8 agents report:

1. **Deduplicate**: merge findings that flag the same line/issue
2. **Corroborate**: when 2+ agents flag the same issue:
   - Merge into one finding with combined evidence
   - Add 20% confidence bonus (capped at 100%)
   - List contributing agents
3. **Filter**: drop solo findings with adjusted_confidence < 40%
   - Exception: solo findings with severity `blocker` or `critical` are never dropped

### Step 4 -- Produce Review Report

```markdown
## Code Review Summary

**Files reviewed**: N
**Findings**: N (blocker: N, critical: N, major: N, minor: N, info: N)
**Corroborated findings**: N (flagged by 2+ agents)

### Blockers (must fix before merge)
[findings with severity: blocker]

### Critical (should fix before merge)
[findings with severity: critical]

### Major (address in this PR or follow-up)
[findings with severity: major]

### Minor (nice to have)
[findings with severity: minor]

### Observations (informational)
[findings with severity: info]

### Dropped Findings (low confidence, for transparency)
[findings that were dropped with reasons]
```

## Agent Specialization Details

### Security Agent
- OWASP Top 10 2025 mapping
- Input validation: SQL injection, XSS, command injection, path traversal
- Authentication: token handling, session management, privilege escalation
- Data exposure: logging sensitive data, error message information leaks
- Dependencies: known CVEs in imports

### Performance Agent
- Query patterns: N+1, missing indexes, full table scans
- Algorithmic: O(n^2) in loops, unnecessary allocations, blocking I/O
- Memory: unbounded collections, missing cleanup, reference cycles
- Bundle: tree-shaking opportunities, code splitting

### Correctness Agent
- Logic: off-by-one, wrong operator, missing early return
- Null safety: unhandled None/null/undefined, optional chaining gaps
- Concurrency: race conditions, deadlocks, lost updates
- Edge cases: empty input, max values, unicode, timezone

### Maintainability Agent
- Complexity: cyclomatic > 10, cognitive > 15, nesting > 3 levels
- Naming: unclear variable/function names, misleading names
- Structure: god functions (> 50 lines), god classes, hidden coupling
- DRY: duplicated logic (> 3 occurrences)

### Testing Agent
- Missing tests for new public functions
- Weak assertions (assertTrue with no condition, no assert at all)
- Testing implementation details instead of behavior
- Missing edge case tests for changed code

### Compatibility Agent
- Public API changes without deprecation
- Breaking changes in function signatures
- Version compatibility (Python 3.9+, Node 18+, etc.)
- Config format changes

### Architecture Agent
- Layer violations (controller calling repository directly)
- Circular dependencies (import cycles)
- Pattern inconsistency (some modules use pattern A, this uses B)
- Missing abstractions (concrete dependencies where interfaces belong)

### Frontend Agent (skip if no frontend files in diff)
- Missing aria labels on interactive elements
- Layout shift risks (images without dimensions, dynamic content)
- Unhandled loading/error/empty states
- Accessibility: color contrast, keyboard navigation, screen reader support
