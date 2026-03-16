---
name: ai-quality
version: 2.0.0
description: "Unified quality assessment: coverage, complexity, duplication, code review. Modes: code | sonar | review | docs."
argument-hint: "all|code|sonar|review|docs"
tags: [quality, coverage, complexity, duplication, review, sonar]
---


# Quality

## Purpose

Unified quality assessment covering code metrics, Sonar integration, code review, and documentation audit. Consolidates audit, sonar, code-review, and docs-audit into four modes. Each mode produces a scan report with a 0-100 score so results are comparable across runs and reviewers.

## Trigger

- Command: `/ai:verify quality` or `/ai:quality [code|sonar|review|docs]`
- Context: quality gate, code review, pre-release quality check.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"quality"}'` at skill start. Fail-open -- skip if ai-eng unavailable.

## When NOT to Use

- **Security vulnerabilities** -- use `security`. Quality measures structure; security measures safety.
- **Architecture drift or coupling** -- use `architecture`. Quality checks metrics; architecture checks design.
- **Refactoring execution** -- use `refactor`. Quality diagnoses; refactor treats.
- **Test writing or execution** -- use `test`. Quality reports gaps; test fills them.
- **Performance profiling** -- use `perf`. Quality flags complexity; perf measures latency.

## Quality Thresholds

Project baselines. Modes reference these when scoring.

| Metric | Threshold | Severity | Source |
|--------|-----------|----------|--------|
| Line coverage | >= 80% | major | `quality/core.md` |
| Governance path coverage | 100% | blocker | `quality/core.md` |
| Cyclomatic complexity | <= 10 / function | major | `quality/core.md` |
| Cognitive complexity | <= 15 / function | major | `quality/core.md` |
| Duplicated lines (changed) | <= 3% | major | `quality/core.md` |
| Reliability | zero blocker/critical | blocker | `quality/core.md` |
| Maintainability debt (changed) | zero critical items | critical | `quality/core.md` |

Scoring formula: start at 100, deduct per finding (blocker: -20, critical: -10, major: -5, minor: -1, floor 0).

## Modes

### code -- Quality metrics

Measure coverage, complexity, and duplication for the codebase or scoped changed files.

1. **Coverage** -- run `uv run pytest --cov --cov-report=term-missing` scoped to changed modules. Compare against 80%.
   - Below 80%: list uncovered files, flag lowest-coverage first (highest remediation impact).
   - Governance paths (hooks, gates, CLI) below 100%: flag as blocker.

2. **Complexity** -- run `ruff check --select C901 --statistics` for cyclomatic violations. Each finding includes function name and score.
   - Complexity 12 = 2 over threshold, major. Complexity 25 = design problem, escalate to `refactor`.

3. **Duplication** -- run `ruff check --select CPY` or manual block inspection (3+ identical occurrences). Calculate as percentage of changed lines against 3% threshold.

4. **Lint** -- run `ruff check --statistics` for all rules. Group by category: E=critical, F=major, W/I/N=minor.

5. **Score** -- apply deduction formula.

**Example**: "Check code quality on the CLI module." -- Scope to `src/ai_eng/cli/`, find 74% coverage (major) and `dispatch_command` at complexity 14 (major). Score: 85/100, two major findings.

### sonar -- SonarCloud gate

Run Sonar-equivalent quality gate locally. Advisory if SonarCloud is unconfigured.

1. **Check config** -- look for `sonar-project.properties` or `sonar.projectKey` in CI. If absent, proceed local-only with advisory notice.

2. **Local analysis** -- map ruff rules to Sonar domains:
   - Reliability: ruff E/F rules. Security: ruff S rules (bandit). Maintainability: ruff C/W rules.

3. **Read Sonar report** (if configured) -- fetch quality gate status. Key metrics: coverage on new code, duplication on new code, reliability/security/maintainability ratings (A-E). Below B on security or reliability = gate failure.

4. **Map severities** -- Sonar blocker/critical -> project blocker/critical (merge blocked). Major -> fix before merge. Minor/info -> track incrementally.

5. **Score** -- use Sonar gate as primary signal when available; otherwise local ruff deduction formula.

**Example**: "Run Sonar gate before the PR." -- `sonar-project.properties` found, gate Failed: 65% coverage (needs 80%), 2 reliability bugs. Score: 60/100.

### review -- Deep code review

Multi-dimension review for PR-level or pre-merge assessment.

1. **Scope** -- determine diff via `git diff main...HEAD`. Read changed files in full for context, not just diff lines.

2. **Review dimensions** (priority order):
   - **Security**: injection, auth gaps, secrets, unsafe deserialization, path traversal. Critical/blocker.
   - **Correctness**: logic errors, off-by-one, null handling, exception swallowing. Major.
   - **Patterns**: project conventions (`stacks/python.md`), error handling, abstractions. Major.
   - **Performance**: unnecessary loops, N+1 queries, unbounded collections, blocking I/O. Major.
   - **Maintainability**: functions >50 lines, nesting >3 levels, missing type hints on public APIs. Minor-major.
   - **Naming**: unclear variables, inconsistent conventions, unexplained abbreviations. Minor.
   - **Tests**: changed code has test changes, edge cases covered, no behavior-hiding mocks. Major if missing.

3. **Prioritize** -- sort by severity, then remediation effort (quick wins first). Group findings sharing a root cause.

4. **Formulate feedback** -- each finding includes: file + line range, dimension, severity, description with WHY, concrete remediation.

5. **Score** -- zero blocker/critical and <3 major = PASS (>= 80).

**Example**: "Review this PR." -- 4 files, 120+/30-. Find `subprocess.call(user_input)` (security/critical), missing test for `validate_input()` (tests/major), unclear variable `x` (naming/minor). Score: 70/100 WARN, critical blocks merge.

### docs -- Documentation audit

Assess documentation health: coverage, cross-references, style, completeness.

1. **Inventory** -- list all `.md` files. Categorize: specs, standards, skills, agents, ADRs, README.

2. **Coverage** -- verify documentation exists for each public module/skill:
   - Every `skills/` entry has `SKILL.md`. Every `agents/` entry has `.md`. README at root covers setup/usage/contribution.

3. **Cross-references** -- scan for internal links, verify targets exist. Broken links = major. Bad anchors = minor.

4. **Style** -- frontmatter present where required, heading hierarchy (H1 title, H2 sections, no skips), imperative voice, no orphaned TODO/FIXME.

5. **Completeness** -- Purpose not placeholder, procedure not stub, examples for user-facing skills, references link to related docs.

6. **Score** -- fully documented project with no broken links scores >= 90.

**Example**: "Audit documentation health." -- 35 skills, 7 agents, 12 standards. Find stub SKILL.md (major), 3 broken cross-refs (major each), 2 skills missing examples (minor). Score: 72/100 WARN.

## Output Contract

Every mode produces this structure. Consumers (verify agent, CI, humans) rely on it.

```markdown
# Scan Report: quality/{mode}

## Score: N/100
## Verdict: PASS (>=80) | WARN (60-79) | FAIL (<60)

## Summary
One-paragraph assessment with key takeaway.

## Findings
| # | Severity | Dimension | Description | Location | Remediation |
|---|----------|-----------|-------------|----------|-------------|

## Metrics
| Metric | Value | Threshold | Status |
|--------|-------|-----------|--------|

## Recommendations
Ordered list of actions by impact, highest first.
```

- **PASS (>= 80)**: quality gate satisfied.
- **WARN (60-79)**: merge allowed with owner approval and logged rationale.
- **FAIL (< 60)**: merge blocked until resolved.
- Any single blocker forces FAIL regardless of score.

## Governance Notes

- This skill implements `standards/framework/quality/core.md`. The standard defines thresholds; this skill enforces them.
- Blocker/critical findings block merge. No exceptions without risk acceptance in `state/decision-store.json`.
- Remediation priority: security > reliability > correctness > performance > maintainability > testability > docs > style.
- Max 3 attempts to resolve ambiguous metrics or tool failures before escalating with evidence. Each retry must try a different approach.
- After producing a report, verify score is consistent with findings. If `.ai-engineering/` was modified, run integrity-check.

## References

- `standards/framework/quality/core.md` -- authoritative thresholds and gate structure.
- `standards/framework/stacks/python.md` -- stack-specific quality baseline.
- `standards/framework/core.md` -- governance enforcement rules.
- `.claude/agents/ai-verify.md` -- agent that invokes this skill.
- `.claude/skills/ai-security/SKILL.md` -- security scanning (separate concern).
- `.claude/skills/ai-test/SKILL.md` -- test execution (quality reports gaps, test fills them).
- `.claude/skills/ai-refactor/SKILL.md` -- code improvement (quality diagnoses, refactor treats).

Use context:fork for isolated execution when performing heavy analysis.

$ARGUMENTS
