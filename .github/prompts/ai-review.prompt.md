---
name: ai-review
description: Use when reviewing code changes (PRs, diffs, or files) with parallel specialized agents. 8-agent review with self-challenge protocol and cross-agent corroboration.
model: opus
effort: max
argument-hint: "review|find|learn [PR number or file paths]"
mode: agent
---



# Review

## Purpose

Parallel specialized code review. Dispatches 8 review agents, each analyzing the same code from a different angle. Every agent argues AGAINST its own findings (self-challenge). Cross-agent corroboration filters noise from signal.

## When to Use

- Before merging a PR
- After completing a feature (pre-commit review)
- When reviewing someone else's code
- Periodic architecture review

## Process

1. **Explore first** -- run `/ai-explore` on the changed files to build architectural context
2. **Dispatch reviewers** -- follow `handlers/review.md` (8 parallel specialized agents)
3. **Aggregate findings** -- correlate, deduplicate, confidence-score
4. **Self-challenge** -- each finding is argued against by its own agent
5. **Filter** -- drop solo findings below 40% confidence
6. **Report** -- produce review summary with actionable findings

See `handlers/review.md` for the full review workflow, `handlers/find.md` for finding existing reviews, and `handlers/learn.md` for the continuous improvement loop.

## Quick Reference

| Mode | What it does |
|------|-------------|
| `review` | Full parallel review (default) |
| `find` | Find and summarize existing review comments on a PR |
| `learn` | Extract lessons from past reviews for future improvement |

## The 8 Review Agents

| Agent | Focus | Looks for |
|-------|-------|-----------|
| Security | OWASP, injection, auth | SQL injection, XSS, auth bypass, secret exposure |
| Performance | Speed, memory, I/O | N+1 queries, O(n^2), memory leaks, blocking I/O |
| Correctness | Logic, edge cases | Off-by-one, null handling, race conditions, missing cases |
| Maintainability | Readability, complexity | God functions, deep nesting, unclear naming, magic numbers |
| Testing | Coverage, quality | Missing tests, weak assertions, testing implementation |
| Compatibility | Breaking changes, API | Public API changes, backward compat, deprecation |
| Architecture | Boundaries, patterns | Layer violations, circular deps, pattern inconsistency |
| Frontend | UX, a11y, rendering | Missing aria labels, layout shifts, unhandled states |

## Confidence Scoring

Each finding gets a confidence score (20-100%):

| Score | Meaning | Action |
|-------|---------|--------|
| 80-100% | High confidence, clear evidence | Must address |
| 60-79% | Moderate confidence | Should address |
| 40-59% | Low confidence, single agent | Consider |
| 20-39% | Solo finding, uncertain | Dropped unless critical severity |

**Corroboration bonus**: when 2+ agents flag the same issue, confidence increases by 20%.
**Solo penalty**: single-agent findings below 40% are dropped from the report.

## Self-Challenge Protocol

For each finding, the reviewing agent must:

1. **State the finding** (what is wrong)
2. **Argue against it** (why this might be acceptable)
3. **Resolve** (finding stands, confidence adjusted, or finding withdrawn)

Example:
```
Finding: Function handles 5 different concerns (god function)
Counter: This is a CLI command handler -- some breadth is expected in the entry point
Resolution: Finding stands but severity reduced to minor. The handler delegates
  to helpers for the complex logic. Confidence: 55%
```

## Common Mistakes

- Reviewing without architectural context (always explore first)
- Treating all findings equally (use confidence scoring)
- Not self-challenging (every finding must be argued against)
- Reviewing only the diff without understanding the surrounding code
- Flagging style preferences as bugs

## Integration

- **Called by**: user directly, `/ai-pr` (pre-merge review)
- **Calls**: `/ai-explore` (context), `handlers/review.md`, `handlers/find.md`, `handlers/learn.md`
- **Read-only**: never modifies code -- produces review findings

$ARGUMENTS

---

# Handler: Find Reviews

## Purpose

Find and summarize existing review comments on a PR or in the codebase. Useful for understanding prior feedback before starting a new review.

## Procedure

### Step 1 -- Identify Source

Determine where to look for reviews:

- **PR number provided**: use `gh api repos/{owner}/{repo}/pulls/{number}/comments` to fetch PR comments
- **No PR number**: check `git log --format='%H %s' -20` for recent review-related commits
- **File paths provided**: search for TODO/FIXME/HACK/REVIEW comments in those files

### Step 2 -- Collect Comments

For PR comments:
1. Fetch all review comments via GitHub API
2. Group by file and line number
3. Classify: approved, changes-requested, comment-only

For inline comments in code:
1. Grep for review markers: `TODO`, `FIXME`, `HACK`, `REVIEW`, `XXX`
2. Include surrounding context (3 lines before/after)
3. Check git blame for age and author

### Step 3 -- Summarize

Produce a summary grouped by theme:

```markdown
## Review Comments Summary

### Open Issues (N)
- [file:line] [severity] [comment summary]

### Resolved (N)
- [file:line] [what was resolved]

### Patterns
- [recurring themes across comments]
```

### Step 4 -- Feed Forward

If transitioning to a new review (`/ai-review review`), carry forward:
- Unresolved issues from prior reviews (check if they still apply)
- Recurring patterns (things this codebase gets wrong repeatedly)
# Handler: Learn from Reviews

## Purpose

Extract lessons from past reviews to improve future review quality. Continuous improvement loop: reviews teach the reviewer what matters in this codebase.

## Procedure

### Step 1 -- Collect Review History

Gather data from:
1. Recent PR comments: `gh api repos/{owner}/{repo}/pulls?state=closed&per_page=10`
2. Review comments on those PRs
3. Commit messages that reference review feedback (e.g., "address review comment")
4. Decision store entries tagged with review context

### Step 2 -- Identify Patterns

Classify findings by frequency and impact:

```markdown
## Recurring Findings (found 3+ times)
| Finding Pattern | Frequency | Severity | Agent(s) |
|----------------|-----------|----------|----------|
| Missing null check | 7 | major | correctness |
| No error boundary | 4 | major | frontend |
| N+1 query | 3 | critical | performance |

## False Positives (findings that were dismissed)
| Finding Pattern | Times Dismissed | Reason |
|----------------|----------------|--------|
| Complex function | 3 | CLI handlers, acceptable breadth |
```

### Step 3 -- Generate Learnings

For each recurring pattern:
1. Should this become a lint rule? (automate the check)
2. Should this become a standard? (codify in `standards/`)
3. Should the review agent's confidence be adjusted?

For each false positive pattern:
1. Should the review agent skip this in certain contexts?
2. Should the self-challenge protocol catch this?

### Step 4 -- Update Review Config

If actionable learnings exist, recommend updates to:
- Review agent confidence thresholds
- Context-aware skipping rules
- New lint rules or standards

Output as recommendations -- the user decides what to implement.
# Handler: Review

## Purpose

Full parallel code review workflow. Dispatches 8 specialized agents, each analyzing the same diff from a different angle, then aggregates findings with self-challenge and corroboration.

## Procedure

### Step 1 -- Gather Context

Before any review agent runs:

1. Run `/ai-explore` on the changed files to produce an Architecture Map
2. Identify the diff scope: `git diff --stat` for file list, `git diff` for full content
3. Detect languages in the diff (file extensions) and read:
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
