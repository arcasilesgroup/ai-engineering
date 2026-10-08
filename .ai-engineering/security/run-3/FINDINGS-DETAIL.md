# Finding detail · worktree lifecycle awareness

## 1. Editable checkpoint state self-approves the workflow

**Severity:** HIGH
**Disposition:** Open
**Confidence:** High

### Data flow

1. `.github/hooks/ai-eng.json:8-17` registers
   `scripts/checkpoint-gate.py` on PreToolUse.
2. `scripts/checkpoint-gate.py:266-292` routes Write/Edit operations against
   `.ai-engineering/workflow/checkpoints/*.json` to `check_plan`.
3. `check_plan` in `scripts/checkpoint-gate.py:150-172` parses the resulting
   plan and checks that status/gates are internally consistent and prior
   checkpoints passed. It does not require evidence that tests ran or a human
   approved.
4. The Stop hook runs structural checks in
   `scripts/checkpoint-gate.py:195-231`; a fully self-asserted passed plan
   satisfies those checks without proving that a human approved it.
5. `skills/ai-orchestrator/SKILL.md:213-220` describes spoken app-review
   approval followed by local merge, but the merge path has no verified
   approval token tied to the checkpoint record.

### Reproduction

In a disposable clone, present repository instructions telling the agent to
skip the plan/app-review question, mark each checkpoint and gate passed in the
checkpoint JSON, then merge `feat/<slug>` into local `main`. The hook accepts
the consistent fields; the agent can then perform the local merge. An
independent validator exercised the hook transition functions and reproduced a
merge in a disposable clone. The user's primary tree and remote branches were
not modified.

### Impact and comparable

Unreviewed code enters local `main`, bypassing the workflow's explicit human
approval boundary. Git itself does not provide an application-level approval
record for a local branch merge; the control must be enforced by the workflow
hook or a trusted review service. No remote publication was demonstrated.

### Remediation

Keep approval provenance outside the repository-editable plan file. Require a
human-issued event/token for plan approval and app review, then have the
checkpoint hook verify it before it trusts passed states or allows the
merge/close path.
