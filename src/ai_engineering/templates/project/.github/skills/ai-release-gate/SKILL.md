---
name: ai-release-gate
description: "Use when checking release readiness: 'is this ready to ship?', 'can we release?', 'run the release checks', 'what's blocking the release?', 'pre-release checklist', 'GO/NO-GO'. Runs aggregated gate across 8 dimensions — coverage, security, tests, lint, dependencies, types, docs, packaging — against manifest thresholds and produces a structured GO / CONDITIONAL GO / NO-GO verdict."
effort: high
argument-hint: "[version]|--check-only"
mode: agent
tags: [quality, release, gate, go-no-go, delivery]
requires:
  bins:
  - gitleaks
mirror_family: copilot-skills
generated_by: ai-eng sync
canonical_source: .claude/skills/ai-release-gate/SKILL.md
edit_policy: generated-do-not-edit
---



# Release Gate

Aggregated GO/NO-GO release readiness gate. Checks every quality dimension against `manifest.yml` thresholds and produces a verdict with evidence. Run before version tagging or merge-to-main.

## When to Use

- Pre-release milestone, version tagging, merge-to-main decision.
- NOT for code quality only -- use `/ai-verify quality`.
- NOT for security only -- use `/ai-security`.

## Process

### Step 0 -- Detect stack

Read project root for build config files to determine the technology stack:
- `pyproject.toml` --> Python
- `package.json` --> JS/TS
- `Cargo.toml` --> Rust
- `go.mod` --> Go

Map each gate dimension to the stack-appropriate tool. If multiple configs are found, run gates for each detected stack. If no build config found, report and ask the user before proceeding.

### Phase 1: Gate Dimensions

1. **Coverage** -- verify test coverage meets threshold.
   - Run `pytest tests/ --cov --cov-report=term-missing`.
   - Gate: coverage >= threshold from `manifest.yml` (default 80%).

2. **Security** -- verify zero medium+ findings.
   - Run `gitleaks protect --staged`, `semgrep scan --config auto .`, `uv run python -m ai_engineering.verify.tls_pip_audit`.
   - Gate: zero critical/high findings. Medium findings documented.

3. **Tests** -- verify all tests pass.
   - Run `pytest tests/ -v`.
   - Gate: 100% pass rate. Zero skipped governance tests.

4. **Lint** -- verify clean lint and format.
   - Run `ruff check .`, `ruff format --check .`.
   - Gate: zero unfixable lint errors.

5. **Dependency vulnerabilities** -- verify clean dependency tree.
   - Run `uv run python -m ai_engineering.verify.tls_pip_audit --strict`.
   - Gate: zero known vulnerabilities. Accepted risks must be in `decision-store.json`.

6. **Type checking** -- verify type correctness.
   - Run `ty check src/`.
   - Gate: zero errors.

7. **Documentation coherence** -- verify docs are current.
   - CHANGELOG.md has `[Unreleased]` entries or versioned section.
   - README.md reflects current features.

8. **Packaging integrity** -- verify distribution builds.
   - Run `uv build` or equivalent.
   - Gate: wheel builds cleanly, no missing files.

### Phase 2: Aggregate Verdict

10. **Determine verdict**:
   - **GO**: all dimensions pass.
   - **CONDITIONAL GO**: all pass except non-critical items with risk acceptance in `decision-store.json`.
   - **NO-GO**: one or more blocking issues without risk acceptance.

11. **Produce closure path** (for NO-GO):
    - List specific blockers with fix suggestions.
    - Prioritize by blocking severity.
    - Estimate effort per fix.

## Output Contract

```markdown
## Release Readiness: [version]

### Verdict: GO | CONDITIONAL GO | NO-GO

| Dimension | Status | Detail |
|-----------|--------|--------|
| Coverage | PASS 87% (>= 80%) | -- |
| Security | PASS | 0 findings |
| Tests | PASS | 142/142 pass |
| Lint | PASS | 0 errors |
| Dependencies | PASS | 0 vulns |
| Types | PASS | 0 errors |
| Docs | PASS | CHANGELOG current |
| Packaging | PASS | wheel builds |

### Blockers (if NO-GO)
- [Issue, severity, fix suggestion]

### Residual Risk
- [Risk acceptances from decision-store.json]
```

## Quick Reference

```
/ai-release-gate              # full GO/NO-GO gate
/ai-release-gate v2.0.0       # gate for specific version
/ai-release-gate --check-only # report without blocking
```

## Common Mistakes

- Running release gate on a dirty working tree -- commit first.
- Ignoring CONDITIONAL GO risks -- each must have a `decision-store.json` entry.
- Skipping packaging integrity -- wheel build failures are release blockers.

## Integration

- Aggregates results from `/ai-security`, `/ai-verify quality`, `/ai-test`.
- Reads thresholds from `manifest.yml`.
- Risk acceptances from `state/decision-store.json`.

## References

- `.github/skills/ai-security/SKILL.md` -- security gate.
- `.github/skills/ai-governance/SKILL.md` -- compliance and risk.
- `.ai-engineering/manifest.yml` -- quality thresholds.
$ARGUMENTS
