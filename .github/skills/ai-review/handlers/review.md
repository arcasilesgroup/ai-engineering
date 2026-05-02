# Handler: Review

## Purpose

Single orchestration path for code review. Dispatches specialist agents via the
`Agent` tool for real context isolation and parallelism. Gathers context once,
runs the full specialist surface, adversarially validates every finding, and
reports by original specialist lens.

## Procedure

### Step 0 -- Read Manifest Stacks

Read `.ai-engineering/manifest.yml` field `providers.stacks` for the declared stacks.
Use that as the authoritative stack list for context loading and language-handler dispatch.

### Step 1 -- Gather Context

Before any specialist runs:

1. Read the full diff (`git diff --stat` and `git diff`)
2. Dispatch `review-context-explorer.md` via the **Agent** tool to gather architectural context
3. Load relevant language and framework contexts from `.ai-engineering/contexts/`
4. Read `.ai-engineering/state/decision-store.json` for applicable architectural decisions

The context explorer output is serialized and passed to every specialist in their Agent prompt. Do not re-run ad hoc exploration inside each specialist.

### Step 2 -- Choose Profile

- Default: `normal`
- Explicit expensive path: `--full`

`normal` still runs every specialist. It only changes the execution grouping.

### Step 3 -- Dispatch Specialists via Agent Tool

**Normal mode** -- Dispatch 3 macro-agents via the Agent tool:

```
Agent 1 prompt: "You are reviewing code with these specialist lenses:
correctness, testing, compatibility. [shared context] [diff]
Read and follow the instructions in these agent files:
.github/agents/internal/reviewer-correctness.md
.github/agents/internal/reviewer-testing.md
.github/agents/internal/reviewer-compatibility.md
Produce findings in YAML format attributed by original specialist."

Agent 2 prompt: "... security, backend, performance ..."
Agent 3 prompt: "... architecture, maintainability, frontend ..."
```

**Full mode** -- Dispatch 9 individual agents via the Agent tool:

```
For each specialist:
Agent prompt: "You are the [specialist] reviewer.
[shared context] [diff]
Read and follow .github/agents/internal/reviewer-[specialist].md
Produce findings in YAML format."
```

Each specialist must:
1. Read the shared context before asserting any finding
2. Inspect the full changed files, not only the diff hunk
3. Prefer concrete, user-visible or operationally meaningful defects
4. Emit `low_signal` or `not_applicable` when the surface is weak
5. Avoid style-only comments unless they hide a real defect

### Step 3b -- Language-Specific Review

For each detected language:
1. If a dedicated `handlers/lang-{language}.md` file exists, include it as context
2. Otherwise include `handlers/lang-generic.md`

Language findings are supplemental evidence. They do not replace the specialist roster.

### Step 4 -- Aggregate by Specialist

After all specialists report:

1. Merge duplicate findings that point to the same underlying issue
2. Keep the original specialist attribution even when execution came from a macro-agent
3. Preserve `low_signal` and `not_applicable` outcomes so coverage stays explicit

### Step 5 -- Adversarial Validation

Dispatch `review-finding-validator.md` via the **Agent** tool.

**Critical**: Pass ONLY the YAML finding blocks to the validator -- strip the
specialist's reasoning chain. The validator reads the code fresh and attempts
disproof without knowing why the specialist flagged it.

```
Agent prompt: "You are the finding validator.
Read and follow .github/agents/internal/review-finding-validator.md
Here are the findings to validate:
[YAML finding blocks only -- no reasoning chain]
For each finding, read the code at the cited location and
issue a CONFIRMED or DISMISSED verdict."
```

Validator outcomes:
- `CONFIRMED`: finding survives review
- `DISMISSED`: finding is dropped from the blocking report

If a finding is dismissed:
1. Remove it from blocking severity buckets
2. Record the dismissal reason under `Dismissed by Validator`
3. Keep original specialist attribution for auditability

### Step 6 -- Produce Review Report

```markdown
## Review Summary

**Profile**: normal | full
**Files reviewed**: N
**Specialists run**: security, backend, performance, correctness, testing,
  compatibility, architecture, maintainability, frontend

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
