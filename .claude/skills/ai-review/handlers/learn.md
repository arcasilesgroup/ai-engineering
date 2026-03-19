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
