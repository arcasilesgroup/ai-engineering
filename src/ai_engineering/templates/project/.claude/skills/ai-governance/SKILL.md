---
name: ai-governance
version: 2.0.0
description: "Unified governance validation: integrity, compliance, ownership, operational readiness, risk lifecycle, adaptive standards. Modes: integrity | compliance | ownership | operational | risk | standards."
argument-hint: "all|integrity|compliance|ownership|operational|risk|standards"
tags: [governance, integrity, compliance, ownership, validation, risk, standards]
---


# Governance

## Purpose

Unified governance validation covering cross-reference integrity, contract compliance, ownership boundaries, operational readiness, risk acceptance lifecycle, and adaptive standards evolution. Consolidates integrity, compliance, ownership, install, risk, and standards skills.

The CLI layer (`ai-eng validate`, `ai-eng doctor`) performs deterministic, repeatable checks. The LLM layer interprets those results in context -- connecting findings across modes, identifying root causes, and surfacing systemic patterns that no single check can detect alone.

## Trigger

- Command: `/ai-verify governance` or `/ai-governance [integrity|compliance|ownership|operational|risk|standards]`
- Context: governance audit, pre-release governance check, post-install verification.

> **Telemetry** (cross-IDE): run `ai-eng signals emit skill_invoked --actor=ai --detail='{"skill":"governance"}'` at skill start. Fail-open -- skip if ai-eng unavailable.

## Modes

### integrity -- Cross-reference validation

Validate that every countable claim in the manifest and governance files matches reality on disk.

**CLI**: `ai-eng validate --category integrity`

**Procedure**:

1. **Manifest counters** -- Compare `governance_surface.agents.total` and `governance_surface.skills.total` in `manifest.yml` against the actual count of files in `agents/` and `skills/*/SKILL.md`. A mismatch means a skill or agent was added or removed without updating the manifest.
2. **Agent-skill references** -- For each agent definition in `agents/*.md`, verify every path listed under `references.skills` resolves to an existing `SKILL.md`. Flag orphan references (agent points to deleted skill) and shadow skills (skill exists but no agent references it).
3. **Agent names list** -- Confirm `governance_surface.agents.names` in the manifest matches the actual filenames in `agents/` (minus the `.md` extension). Order does not matter; presence does.
4. **Command file existence** -- For every skill listed in `skills/`, verify the `SKILL.md` file is non-empty and contains valid YAML frontmatter with required fields (`name`, `description`, `metadata`).
5. **State file schemas** -- Confirm each file under `state/` is valid JSON (or NDJSON for `audit-log.ndjson`). Verify required keys exist: `decision-store.json` must have a `decisions` array, `install-manifest.json` must have `version`.

**Interpreting output**: Each check reports PASS or FAIL with the specific mismatch. A single FAIL in integrity is a blocker -- it means governance metadata is lying about the actual state, which poisons every downstream decision.

### compliance -- Contract validation

Validate that rules documented in `framework-contract.md` are actually enforced by hooks, agents, and configuration.

**CLI**: `ai-eng validate --category compliance`

**Procedure**:

1. **Hook enforcement** -- Verify `enforcement.hooks.required` hooks (`pre-commit`, `commit-msg`, `pre-push`) exist in `.git/hooks/` and are executable. Confirm `non_bypassable: true` is respected -- search hook scripts for `--no-verify` escape hatches.
2. **Check coverage** -- For each stack declared in `enforcement.checks`, confirm the corresponding tool is configured and callable. Example: if `python` requires `ruff-format`, verify `ruff` is installed and the pre-commit hook invokes it.
3. **Non-negotiables** -- Walk `standards.non_negotiables` in the manifest. For each directive (e.g., `mandatory_local_enforcement`), trace the enforcement chain: manifest declares it, hook script enforces it, CLAUDE.md prohibits bypassing it. Flag any broken link.
4. **CI workflows** -- Verify each workflow in `enforcement.ci.required_workflows` exists as a file under `.github/workflows/`. Confirm it blocks on the correct severity levels per `block_on_findings`.
5. **Security contract** -- Confirm gitleaks runs in pre-commit, semgrep runs in pre-push, and dependency audit runs per stack. Cross-reference against `tooling.required.security` in the manifest.

**Interpreting output**: Compliance failures are critical because they mean a documented safety net has a hole. A rule that exists only on paper is worse than no rule -- it creates false confidence.

### ownership -- Boundary validation

Validate that files live in the correct ownership zone and that no unauthorized modifications have crossed boundaries.

**CLI**: `ai-eng validate --category ownership`

**Procedure**:

1. **Zone mapping** -- Load `ownership.model` from the manifest. Build the four zones: framework-managed, team-managed, project-managed, system-managed. Add `ownership.external_framework_managed` as a fifth zone.
2. **File placement** -- Scan every file under `.ai-engineering/` and verify it falls into exactly one ownership zone. Flag files that match no zone (orphans) or match multiple zones (ambiguous ownership).
3. **Modification history** -- For framework-managed files, check `git log` to confirm only framework update commits modified them. For team-managed and project-managed files, confirm no framework update commit touched them. This detects silent overwrites.
4. **Update rule compliance** -- Verify the updater contract: team-managed and project-managed paths must never be overwritten by automated updates. Check `state/ownership-map.json` for recorded boundary crossings.
5. **External managed files** -- Verify each path in `external_framework_managed` either exists (expected) or is absent with a documented reason. Flag unexpected files in those paths that the framework does not manage.

**Interpreting output**: Ownership violations erode trust. If the framework silently overwrites team customizations, teams stop customizing. If team files leak into framework zones, updates become dangerous. Every violation needs a clear owner and resolution path.

### operational -- Install verification

Verify that the installed instance is ready to operate: tools present, hooks installed, state files initialized, permissions correct.

**CLI**: `ai-eng doctor`

**Procedure**:

1. **Required tools** -- For each tool in `tooling.required`, verify it is installed, on PATH, and at a compatible version. Group results by category (python, dotnet, nextjs, security, vcs_cli).
2. **Hook installation** -- Confirm hooks in `.git/hooks/` match the canonical versions in `scripts/hooks/`. Check file hashes to detect manual modifications. Verify executable permissions.
3. **State file initialization** -- Confirm all `system_managed` state files exist and contain valid initial data. A missing `decision-store.json` means decisions will be lost. A missing `audit-log.ndjson` means telemetry is blind.
4. **Configuration readiness** -- Per `tooling.readiness`, verify: tools are installed (`require_install`), configured (`require_configuration`), and authenticated where applicable (`require_auth_when_applicable`). Example: `gh` must be authenticated, `az` must have a default subscription.
5. **Optional tools** -- Report optional tooling status (dast, container, sbom, security) as informational. Missing optional tools do not block but reduce coverage.

**Interpreting output**: `ai-eng doctor` produces a checklist of PASS/WARN/FAIL per tool. FAIL means a required tool is missing or broken -- commits and pushes will be blocked until fixed. WARN means degraded but functional. Use `ai-eng doctor --fix-tools` for automated remediation, `ai-eng doctor --fix-hooks` for hook repair.

### risk -- Risk acceptance lifecycle

Manage the full risk acceptance lifecycle: accepting new risks with time-limited expiry, resolving them after remediation, and renewing when more time is needed. Ensures every risk is tracked, auditable, and subject to governance enforcement.

**CLI**: `ai-eng maintenance risk-status`

**Sub-modes**: `accept`, `resolve`, `renew` (specified as second argument, e.g., `/ai-governance risk accept`).

#### Accept procedure

Record a time-limited risk acceptance when immediate remediation is not feasible.

1. **Classify** -- identify the finding (source tool, description, affected scope).
2. **Determine severity** -- `critical` (exploitable, user-exposed), `high` (exploitable, limited mitigation), `medium` (conditional), `low` (informational).
3. **Assess remediation** -- if fixable now, fix it instead. If deferred, document why.
4. **Register** -- create decision in `decision-store.json`:
   - `risk_category`: `"risk-acceptance"`
   - `severity`: from step 2
   - `criticality`: derive from severity -- `critical` -> `critical`, `high` -> `high`, `medium` -> `medium`, `low` -> `low`
   - `follow_up_action`: **mandatory** concrete remediation plan
   - `accepted_by`: actor accepting the risk
   - `acknowledgedBy`: array of all stakeholders who reviewed
   - `expires_at`: ISO 8601 date, auto from severity (Critical 15d, High 30d, Medium 60d, Low 90d) or explicit override
5. **Log** -- append `risk-acceptance-created` to audit log.
6. **Verify** -- confirm in `ai-eng maintenance risk-status` as `active`.

#### Resolve procedure

Close a risk acceptance after the finding has been remediated.

1. **Locate** -- find decision by ID. Must be `active` or `expired`.
2. **Validate fix** -- confirm code change committed, security scan clean, no regression.
3. **Run checks** -- `ai-eng gate risk-check` passes, tool-specific scan no longer flags finding.
4. **Close** -- mark decision as `remediated` (remains in store for audit trail -- NOT deleted).
5. **Log** -- append `risk-acceptance-remediated` to audit log.
6. **Verify** -- decision shows `remediated` in status. Gates green.

#### Renew procedure

Extend a risk acceptance before expiry (maximum 2 renewals).

1. **Locate** -- find decision by ID. Check `renewal_count`.
2. **Check eligibility** -- if `renewal_count >= 2`: **deny**. Remediation is mandatory.
3. **Justify** -- require concrete justification (not generic). Update `follow_up_action` if plan changed.
4. **Extend** -- create new decision: `renewed_from` = original ID, `renewal_count` + 1, recalculated expiry. Original marked `superseded`.
5. **Log** -- append `risk-acceptance-renewed` with renewal count and justification.
6. **Warn on final** -- if renewal count = 2: "Final renewal. No further extensions."
7. **Verify** -- new decision `active`, original `superseded`, gates pass.

**Governance notes**: Risk acceptances are **time-limited** -- expire by severity. Expired acceptances **block pre-push** and **warn in pre-commit**. Maximum **2 renewals** per chain -- non-negotiable. `follow_up_action` is **mandatory** -- no acceptance without a remediation plan. After 2 renewals: remediate or start a new acceptance chain with fresh justification. Partial fixes: do not resolve -- complete the fix or renew.

**Interpreting output**: Each sub-mode produces a decision record. Accept creates a new tracked risk. Resolve marks it closed with audit trail preserved. Renew extends with strict limits. Any expired, unresolved acceptance is a blocker in pre-push gates.

### standards -- Adaptive standards from evidence

Define a controlled loop for proposing and applying standards updates from measurable evidence (gate failures, audits, incident patterns). Use when recurring workflow friction, new risks, or platform changes require policy updates.

**Procedure**:

1. **Collect evidence** -- gather data from gate failures, audit findings, and incident patterns. Quantify: how often, how severe, what impact.
2. **Draft standards delta** -- propose specific changes with rationale, expected gain, and impact assessment. Each change must cite evidence.
3. **Validate non-negotiables** -- confirm proposed changes do not weaken non-negotiable standards. Verify ownership boundaries are respected.
4. **Apply updates** -- implement changes with mirror synchronization across IDE configurations. Run integrity-check after application.

**Post-action validation**:

- Run integrity-check to verify 7/7 categories pass.
- Run contract-compliance against `framework-contract.md` to verify no regression.
- If validation fails, fix issues and re-validate (max 3 attempts per iteration limits).

**Governance notes**: Never weaken non-negotiables without explicit risk acceptance (use the `risk` mode to record it). Standards changes must be evidence-driven -- no speculative policy updates.

**Interpreting output**: Standards mode produces a change proposal with evidence citations and impact analysis. After application, integrity and compliance checks confirm the change did not introduce regressions. Failed post-action validation means the standards change must be revised or reverted.

## Systemic Pattern Analysis

The LLM adds value beyond CLI checks by connecting findings across modes. After collecting results from all requested modes, perform this analysis:

1. **Root cause correlation** -- A single root cause often manifests across multiple modes. Example: a missing tool appears as an operational FAIL, causes a compliance gap (check not enforced), and may cascade into an integrity mismatch (state file not updated). Trace findings back to the fewest root causes.
2. **Drift detection** -- Compare the intended state (manifest + contracts) against the actual state (disk + git history). Identify when drift started and what triggered it. Gradual drift is harder to detect than acute breaks.
3. **Coverage gaps** -- Identify what is NOT checked. If a new stack was added but `enforcement.checks` was not updated, no mode will flag the missing checks. The LLM should reason about what validations should exist but do not.
4. **Priority ranking** -- Not all findings are equal. Rank by blast radius: a broken pre-commit hook affects every developer on every commit. A missing optional tool affects one scan mode. Present findings in priority order.
5. **Remediation sequencing** -- Some fixes must happen before others. Hook repair must precede compliance validation. Tool installation must precede operational checks. Propose a fix order, not just a fix list.

## Common Findings

| Finding | Mode | Typical cause | Remediation |
|---------|------|---------------|-------------|
| Manifest says 35 skills, disk has 34 | integrity | Skill deleted without manifest update | Update `governance_surface.skills.total` in manifest.yml |
| Agent references nonexistent skill | integrity | Skill renamed or moved | Update agent's `references.skills` path |
| pre-push hook missing semgrep call | compliance | Hook script modified manually | Run `ai-eng doctor --fix-hooks` to restore canonical hooks |
| Team file modified by framework commit | ownership | Updater bug or manual error | Restore from git, file issue against updater |
| `gh` not authenticated | operational | Fresh clone, no `gh auth login` | Run `gh auth login` then `ai-eng doctor` |
| State file contains invalid JSON | integrity | Interrupted write, merge conflict | Regenerate from defaults: `ai-eng state reset <file>` |
| Risk acceptance expired, blocking push | risk | Expiry passed without remediation or renewal | Resolve the finding or renew (max 2) via `/ai-governance risk` |
| Renewal denied (count >= 2) | risk | Maximum renewals exhausted | Remediate the finding -- no further extensions allowed |
| Risk accepted without follow_up_action | risk | Missing mandatory field | Add concrete remediation plan to decision |
| Standards change weakened non-negotiable | standards | Proposed delta relaxes a core rule | Revert change, use risk acceptance if deferral needed |
| Post-action integrity-check failed | standards | Standards update broke cross-references | Fix mismatches, re-run integrity-check (max 3 attempts) |

## When NOT to Use

- **Code quality issues** -- Use `/ai-verify quality` instead. Governance does not assess code metrics.
- **Security vulnerabilities** -- Use `/ai-verify security`. Governance checks that security tools are configured, not what they find.
- **Performance problems** -- Use `/ai-verify performance`. Governance does not profile runtime behavior.
- **Single-file questions** -- Governance operates at the framework level. For "does this file follow standards," use `/ai-quality review`.
- **During active spec implementation** -- Governance checks are most valuable between phases, before releases, or after structural changes. Running mid-implementation generates noise from intentionally incomplete states.

## Output Contract

Every governance scan produces this format:

```markdown
# Governance Report: [mode]

## Score: N/100
## Verdict: PASS | WARN | FAIL

## Findings
| # | Severity | Category | Description | Location | Remediation |

## Signals
{ "mode": "governance", "sub_mode": "<mode>", "score": N, "findings": { "blocker": 0, "critical": N, "major": N }, "timestamp": "..." }

## Gate Check
- Blocker findings: N (threshold: 0)
- Critical findings: N (threshold: 0)
- Verdict justification: ...
```

**Risk mode output** additionally includes: decision ID, severity, expiry date, renewal count, and sub-mode action taken (accepted/resolved/renewed).

**Standards mode output** additionally includes: evidence citations, proposed delta, post-action validation results (integrity-check 7/7, contract-compliance status).

**Scoring**: Start at 100. Deduct per finding: blocker -25, critical -15, major -5, minor -1. Floor at 0. Verdict: PASS >= 90, WARN >= 70, FAIL < 70.

## Procedure

1. **Emit telemetry** -- Signal skill invocation. Fail-open.
2. **Run CLI** -- `ai-eng validate --category <mode>` (or `ai-eng doctor` for operational). Collect deterministic results.
3. **Interpret** -- Apply the mode-specific procedure above. Check each item methodically.
4. **Analyze patterns** -- If multiple modes were requested, run systemic pattern analysis to connect findings.
5. **Score and report** -- Produce the output contract. Rank findings by severity, then by blast radius.
6. **Emit completion signal** -- `ai-eng signals emit scan_complete --actor=scan --detail='{"mode":"governance","sub_mode":"<mode>","score":<N>,...}'`

Use context:fork for isolated execution when performing heavy analysis.

$ARGUMENTS
