# Handler: Review

## Purpose

Single orchestration path for code review. It gathers context once, runs the full
specialist surface in either `normal` or `--full`, adversarially validates every
finding, and reports by original specialist lens.

## Procedure

### Step 0 -- Read Manifest Stacks

Read `.ai-engineering/manifest.yml` field `providers.stacks` for the declared stacks.
Use that as the authoritative stack list for context loading and language-handler dispatch.

### Step 1 -- Gather Context

Before any specialist runs:

1. Read the full diff (`git diff --stat` and `git diff`)
2. Dispatch `context-explorer.md` to gather architectural context beyond the diff
3. Load relevant language and framework contexts
4. Read `.ai-engineering/state/decision-store.json` for applicable architectural decisions

The context explorer output is shared across every specialist. Do not re-run ad hoc exploration inside each specialist unless a finding truly requires it.

### Step 2 -- Choose Profile

- Default: `normal`
- Explicit expensive path: `--full`

`normal` still runs every specialist. It only changes the execution grouping:

1. `correctness`, `testing`, `compatibility`
2. `security`, `backend`, `performance`
3. `architecture`, `maintainability`, `frontend`

`--full` runs one specialist prompt per specialist.

### Step 3 -- Dispatch Specialists

Each specialist reviews the same diff with the shared context and returns:

```yaml
specialist: security|backend|performance|correctness|testing|compatibility|architecture|maintainability|frontend
status: active|low_signal|not_applicable
findings:
  - id: security-1
    severity: blocker|critical|major|minor|info
    file: path/to/file
    line: 42
    finding: "What is wrong"
    evidence: "Why it is a real issue"
    remediation: "How to fix"
```

Use these specialist resources:

- `reviewer-security.md`
- `reviewer-backend.md`
- `reviewer-performance.md`
- `reviewer-correctness.md`
- `reviewer-testing.md`
- `reviewer-compatibility.md`
- `reviewer-architecture.md`
- `reviewer-maintainability.md`
- `reviewer-frontend.md`

Each specialist must:

1. read the shared context before asserting any finding
2. inspect the full changed files, not only the diff hunk
3. prefer concrete, user-visible or operationally meaningful defects
4. emit `low_signal` or `not_applicable` when the surface is weak instead of stretching for noise
5. avoid style-only comments unless they hide a correctness, maintainability, or compatibility defect

### Step 3b -- Language-Specific Review

For each detected language:

1. If a dedicated `handlers/lang-{language}.md` file exists, dispatch it
2. Otherwise dispatch `handlers/lang-generic.md`

Language findings are supplemental evidence. They do not replace the specialist roster.

### Step 4 -- Aggregate by Specialist

After all specialists and language supplements report:

1. Merge duplicate findings that point to the same underlying issue
2. Keep the original specialist attribution even when execution came from a macro-agent
3. Preserve `low_signal` and `not_applicable` specialist outcomes in the report so coverage stays explicit

### Step 5 -- Adversarial Validation

Run `finding-validator.md` against every emitted finding in both `normal` and `--full`.

Validator outcomes:

- `CONFIRMED`: finding survives review
- `DISMISSED`: finding is dropped from the final blocking report

Every final finding must have survived this stage.

If a finding is dismissed:

1. remove it from the blocking severity buckets
2. record the dismissal reason under `Dismissed by Validator`
3. keep the original specialist attribution for auditability

### Step 6 -- Produce Review Report

```markdown
## Review Summary

**Profile**: normal | full
**Files reviewed**: N
**Specialists run**: security, backend, performance, correctness, testing, compatibility, architecture, maintainability, frontend

### Blockers
[grouped by specialist]

### Critical
[grouped by specialist]

### Major
[grouped by specialist]

### Minor
[grouped by specialist]

### Informational
[grouped by specialist]

### Dismissed by Validator
[finding ids with concise reasons]

### Low Signal / Not Applicable
[specialists that had little or no relevant surface]
```

The final report must remain organized by original specialist lens even when
multiple specialists were executed by the same macro-agent in `normal`.
