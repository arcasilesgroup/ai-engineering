---
name: ai-debug
description: "Diagnoses broken behavior systematically with a 4-phase root-cause loop: test failures, runtime errors, crashes, regressions. Never patches symptoms. Trigger for 'it is not working', 'something broke', 'this used to work', 'I am getting an error', 'CI is failing', 'why is X happening'. Not for adding tests; use /ai-test instead. Not for security findings; use /ai-security instead."
effort: mid
argument-hint: "[error description or file:line]"
---

# Debug

Systematic 4-phase debugging, always in order, that finds and fixes the root cause instead of patching symptoms. After 2 failed fix attempts, escalate to the user.

## Workflow

Principles applied: §10.5 TDD (a regression test that fails without the fix and passes with it); §10.1 KISS (the smallest change that addresses the root cause).

Step 0 — load contexts: read `.ai-engineering/manifest.yml` `providers.stacks`; load `.ai-engineering/overrides/<stack>/conventions.md` per stack + `.ai-engineering/overrides/_shared/conventions.md`; load `.ai-engineering/team/*.md`.

### Phase 1 — Symptom Analysis (facts before hypotheses)

1. **WHAT** — exact error message, stack trace, log output.
2. **WHEN** — always? intermittent? after a specific change? under load?
3. **WHERE** — which file, function, line, test, environment?
4. **SINCE WHEN** — `git log --oneline -20`: what changed recently?

Output: a symptom report with every fact tagged KNOWN or SUSPECTED.

### Phase 2 — Reproduction (minimal repro)

1. Run the failing test or reproduce the error.
2. If not reproducible: document exact conditions and STOP (cannot debug what cannot be reproduced).
3. Strip to a minimal repro: remove unrelated code, simplify inputs, isolate the component.
4. Confirm the minimal repro fails consistently.

Output: the exact command to reproduce the failure.

### Phase 3 — Root Cause (5 Whys)

1. Ask **Why** repeatedly (immediate cause -> deeper cause -> root cause) until you reach a cause you can fix directly.
2. **Techniques** — binary search (comment out code, add assertions); `git bisect start HEAD <known-good>`; targeted print/log tracing at decision points; `git diff <known-good>..HEAD -- <file>`; assumption check (list every assumption, verify each).
3. **Classify** the root cause: logic error / state corruption / contract violation / environment / data.

Output: a root-cause statement (1-2 sentences, specific and testable).

### Phase 4 — Solution Design (fix + regression test)

1. Design the fix: minimal change addressing the root cause; one logical change. If the fix is large, Phase 3 may be wrong — revisit.
2. Write a regression test that fails without the fix and passes with it.
3. Apply the fix.
4. Verify: the regression test passes AND all existing tests pass.
5. Check for siblings: does the same bug pattern exist elsewhere? (`grep` for similar code.)

## Escalation Protocol

| Attempt | Action |
|---------|--------|
| 1st fix fails | Try a different approach (not the same thing again) |
| 2nd fix fails | STOP. Escalate with: symptom, repro, root-cause analysis, 2 approaches tried |

Never retry the same approach. Never loop silently.

## 5 Whys Example

```
Symptom: test_parse_config_handles_empty fails with KeyError
Why 1: config["database"] raises KeyError
Why 2: parse_config returns empty dict when file is empty
Why 3: the YAML parser returns None for empty files, not empty dict
Root cause: missing None -> {} coercion after yaml.safe_load()
Fix: config = yaml.safe_load(f) or {}
```

## Stack-specific guidance

When a stack is active, apply `.ai-engineering/overrides/<stack>/conventions.md` while isolating the fault. Greenfield mode (stacks=[]): follow the generic procedure and run `ai-eng doctor --fix` to seed stack detection.

## Common Mistakes

- Fixing the symptom (e.g., add a try/except) instead of the root cause.
- Changing multiple things at once (change one thing, verify, repeat).

## Examples

### Example — CI failure on a fresh branch

User: "CI is failing only on this branch — what changed?"

```
/ai-debug "CI failing on feat/new-auth"
```

Walks the diff vs `main`, isolates the suspect change, reproduces locally, identifies the root cause without symptom-patching, then adds a regression test before applying the fix.

## Integration

Called by: `/ai-build`, `/ai-build` (test fail), user directly. Calls: test runners (reproduction), `/ai-test` (regression test). Transitions to: `/ai-build` (fix), `/ai-commit` (verified). See also: `/ai-test`, `/ai-postmortem`, `/ai-resolve-conflicts`.

$ARGUMENTS
