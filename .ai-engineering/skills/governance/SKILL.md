---
name: governance
description: "Unified governance validation: integrity, compliance, ownership, operational readiness. Modes: integrity | compliance | ownership | operational."
metadata:
  version: 2.0.0
  tags: [governance, integrity, compliance, ownership, validation]
  ai-engineering:
    scope: read-write
    token_estimate: 1000
---

# Governance

## Purpose

Unified governance validation covering cross-reference integrity, contract compliance, ownership boundaries, and operational readiness. Consolidates integrity, compliance, ownership, and install skills.

The CLI layer (`ai-eng validate`, `ai-eng doctor`) performs deterministic, repeatable checks. The LLM layer interprets those results in context -- connecting findings across modes, identifying root causes, and surfacing systemic patterns that no single check can detect alone.

## Trigger

- Command: `/ai:verify governance` or `/ai:governance [integrity|compliance|ownership|operational]`
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
5. **State file schemas** -- Confirm each file under `state/` is valid JSON (or NDJSON for `audit-log.ndjson`). Verify required keys exist: `decision-store.json` must have a `decisions` array, `session-checkpoint.json` must have `last_session`, `install-manifest.json` must have `version`.

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

## When NOT to Use

- **Code quality issues** -- Use `/ai:verify quality` instead. Governance does not assess code metrics.
- **Security vulnerabilities** -- Use `/ai:verify security`. Governance checks that security tools are configured, not what they find.
- **Performance problems** -- Use `/ai:verify performance`. Governance does not profile runtime behavior.
- **Single-file questions** -- Governance operates at the framework level. For "does this file follow standards," use `/ai:quality review`.
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

**Scoring**: Start at 100. Deduct per finding: blocker -25, critical -15, major -5, minor -1. Floor at 0. Verdict: PASS >= 90, WARN >= 70, FAIL < 70.

## Procedure

1. **Emit telemetry** -- Signal skill invocation. Fail-open.
2. **Run CLI** -- `ai-eng validate --category <mode>` (or `ai-eng doctor` for operational). Collect deterministic results.
3. **Interpret** -- Apply the mode-specific procedure above. Check each item methodically.
4. **Analyze patterns** -- If multiple modes were requested, run systemic pattern analysis to connect findings.
5. **Score and report** -- Produce the output contract. Rank findings by severity, then by blast radius.
6. **Emit completion signal** -- `ai-eng signals emit scan_complete --actor=scan --detail='{"mode":"governance","sub_mode":"<mode>","score":<N>,...}'`
