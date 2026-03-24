# Handler: Verify Sub-Spec (Anti-Hallucination Gate)

## Purpose

Verify that a sub-spec implementation is real and functional -- not hallucinated, incomplete, or disconnected. This is the quality gate between sub-specs.

## Why This Exists

AI agents can:
- Create files that exist but are never imported or called (dead code)
- Write functions with correct signatures but wrong behavior
- Reference modules that do not exist (phantom imports)
- Mark tasks DONE without the code actually working

This gate catches those failures BEFORE moving to the next sub-spec.

## Procedure

### Step 1 -- Read Verify Pattern

Read `.claude/skills/ai-verify/SKILL.md`. Use the IRRV protocol (Identify, Run, Read, Verify) as the foundation for every check below. No claim without evidence.

### Step 2 -- Collect Evidence

Get the list of files changed in this sub-spec:

```bash
git diff HEAD~1 --name-only
```

Load the sub-spec from `.ai-engineering/specs/autopilot/sub-NNN.md` and extract its `files:` list and acceptance criteria.

### Step 3 -- Dispatch Verify Agent

Dispatch Agent(Verify) with the changed files and this five-level checklist.

**Level 1: Existence**
- [ ] Every file listed in sub-spec `files:` exists on disk
- [ ] No file is empty (>10 lines of actual content, not just headers)
- [ ] File extensions match expected types

**Level 2: Syntax**
- [ ] `ruff check .` passes with zero errors
- [ ] `ruff format --check .` reports no changes needed
- [ ] For YAML files: valid YAML (`python -c "import yaml; yaml.safe_load(open(f))"`)
- [ ] For JSON files: valid JSON (`python -c "import json; json.load(open(f))"`)

**Level 3: Integration**
- [ ] No phantom imports: for each `import X` or `from X import Y` in new code, verify X exists
- [ ] No dead code: every new function/class is referenced from at least one other file
- [ ] For skills: routing table references match handler files on disk
- [ ] For handlers: cross-references to other handlers/skills resolve
- [ ] `sync_command_mirrors.py --check` reports zero drift (if applicable)

**Level 4: Functional**
- [ ] `pytest tests/unit/ -q` passes
- [ ] If new test files were created: they run and pass
- [ ] Sub-spec acceptance criteria from `sub-NNN.md` are met

**Level 5: Consistency**
- [ ] `scripts/check_test_mapping.py` passes (new tests mapped)
- [ ] Manifest counts match disk reality
- [ ] No CLAUDE.md/AGENTS.md counter drift

### Step 4 -- Evaluate Results

**ALL PASS**: Mark sub-spec as VERIFIED in `specs/autopilot/manifest.md`, continue to next.

**Level 1-2 failures** (auto-fixable):
1. Run `ruff check . --fix` and `ruff format .`
2. Re-check once
3. If still failing: treat as Level 3-5 failure

**Level 3-5 failures** (structural):
1. Report findings with evidence: which check failed, file path, line number, error message
2. If first failure for this sub-spec: retry the execute phase with the failure report embedded in the build prompt
3. If second failure: STOP the autopilot pipeline. Report to user with:
   - Sub-spec identifier
   - Both verify reports (attempt 1 and attempt 2)
   - Specific checks that failed and why
   - Rollback command: `git reset --soft HEAD~N`

## Output

```
--- Verify: sub-NNN ---
Level 1 (Existence):  PASS | FAIL (details)
Level 2 (Syntax):     PASS | FAIL (details)
Level 3 (Integration): PASS | FAIL (details)
Level 4 (Functional): PASS | FAIL (details)
Level 5 (Consistency): PASS | FAIL (details)
Verdict: VERIFIED | RETRY (attempt 1/2) | FAILED (pipeline halted)
---
```

## Behavioral Negatives (Must NOT)

- Weaken or skip any check level to force a pass
- Modify test assertions to make tests pass
- Claim VERIFIED without running every applicable check
- Use forbidden words: "should work", "looks good", "probably fine"
- Proceed to the next sub-spec on a FAILED verdict
- Retry more than once (2 total attempts max, then escalate)
