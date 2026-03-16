# Code Review Standards

## Update Metadata
- Rationale: Standardize code review process across all stacks with confidence scoring, self-challenge gates, and uniform output contracts.
- Expected gain: Reduced false positives, consistent review quality, actionable findings.
- Potential impact: All review-producing skills (pr, quality review, verify).

## Confidence Scoring Scale

All review findings MUST include a confidence score:

| Range | Level | Criteria | Example |
|-------|-------|----------|---------|
| 90-100% | Definite | Measurable, objective evidence | Direct SQL concatenation, cyclomatic >15, hardcoded secret |
| 70-89% | Clear problem | Violates established patterns | Missing index on queried column, N+1 in loop |
| 50-69% | Likely issue | Code smell with contextual evidence | Overly complex function, unclear naming |
| 30-49% | Subjective | Style preference, debatable | Variable naming convention mismatch |
| 20-29% | Suggestion | Minor, low-impact improvement | Comment could be clearer |

Findings below 50% SHOULD be grouped separately as "Suggestions" rather than "Issues".

## Self-Challenge Gate

Before including ANY finding, the reviewer MUST pass all 4 self-challenge questions:

1. **"What's the strongest case this is a false positive?"** — Actively argue against your own finding.
2. **"Can you point to specific problematic code?"** — Vague concerns without concrete code references are dropped.
3. **"Did you verify your assumptions?"** — Check that the pattern you flagged actually exists (not inferred).
4. **"Is the argument against stronger than the argument for?"** — If yes, drop the finding.

If ANY question fails → **drop the finding**.

## Severity Scale

| Severity | Criteria | Action |
|----------|----------|--------|
| Critical | Security vulnerability, data loss risk, production breaking | Must fix before merge |
| Moderate | Performance issue, maintainability concern, test gap | Should fix, may defer with justification |
| Minor | Style, naming, documentation improvement | Nice to have, no block |

## Output Contract

Every review finding MUST include:

```
### [Severity] [Category]: [Title]

**File:** `path/to/file.ext:line`
**Confidence:** N%

[Description of the issue]

**Remediation:**
[Concrete fix with code example]
```

## Review Dimensions

| Dimension | Focus | When to Apply |
|-----------|-------|---------------|
| Security | OWASP, secrets, auth, injection | Always |
| Performance | N+1, O(n²), memory, I/O | Always |
| Correctness | Intent alignment, logic errors, boundaries | Always |
| Maintainability | Clarity, naming, simplification, duplication | Always |
| Testing | Coverage gaps, test quality, mocking scope | When tests changed or code lacks tests |
| Compatibility | Breaking changes, API contracts, schema | When public interfaces modified |
| Architecture | YAGNI, patterns, code reuse, idioms | When new abstractions or dependencies added |

## Context Loading Order

When performing a review:

1. Detect languages from file extensions in the diff
2. Load matching files from `standards/framework/review/languages/`
3. Detect frameworks from imports/config files
4. Load matching files from `standards/framework/review/frameworks/`
5. Load team overrides from `standards/team/review/` if present

## Chunked Review for Large PRs

When diff exceeds 2000 lines:
1. Split by directory or logical feature area into 3-5 chunks
2. Review each chunk independently with focused dimensions
3. Merge findings with cross-chunk corroboration
4. Deduplicate findings that appear in multiple chunks

## References

- Quality thresholds: `standards/framework/quality/core.md`
- Security controls: `standards/framework/security/owasp-top10-2025.md`
- Stack-specific enforcement: `standards/framework/stacks/<stack>.md`

## Update Contract

Framework-managed. Changes require spec + review.
