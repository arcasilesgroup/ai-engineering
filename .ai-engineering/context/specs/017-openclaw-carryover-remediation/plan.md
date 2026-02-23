---
spec: "017"
approach: "serial-phases"
---

# Plan — OpenClaw Adoption + Carryover Remediation (014/015)

## Architecture

### New Files

| File | Purpose | Phase |
|------|---------|-------|
| `context/specs/017-openclaw-carryover-remediation/spec.md` | WHAT document | 0 |
| `context/specs/017-openclaw-carryover-remediation/plan.md` | HOW document | 0 |
| `context/specs/017-openclaw-carryover-remediation/tasks.md` | DO document | 0 |
| `context/specs/017-openclaw-carryover-remediation/done.md` | DONE document | 8 |

### Modified Files

| File | Change | Phase |
|------|--------|-------|
| `context/specs/_active.md` | Activate spec-017 | 0 |
| `context/product/product-contract.md` | Update Active Spec reference | 0 |
| `skills/govern/create-skill.md` | Extend frontmatter template (`anyBins/env/config/os`) | 1 |
| `skills/govern/integrity-check.md` | Validate expanded requirement metadata | 1 |
| `src/ai_engineering/skills/service.py` | Parse/evaluate expanded requirements model | 1 |
| `src/ai_engineering/cli_commands/skills.py` | Add richer skill status diagnostics | 2 |
| `.github/workflows/ci.yml` | Add security parity, workflow sanity, docs-only scope optimization, and Spec-015 carryover checks | 3-5 |
| `src/ai_engineering/policy/gates.py` | Wire coverage/duplication gates and bypass/hook integrity checks (Spec-015 5.7-5.9) | 4 |
| `src/ai_engineering/hooks/manager.py` | Hook hash support and verification integration | 4 |
| `tests/unit/test_gates.py` | New gate behavior tests | 4 |
| `tests/unit/test_hooks.py` | Hook integrity tests | 4 |
| `tests/integration/*` | Hook execution integration test (Spec-015 5.10) | 4 |
| `context/specs/014-dual-vcs-provider/spec.md` | Reconcile status/closure metadata | 6 |
| `context/specs/014-dual-vcs-provider/tasks.md` | Reconcile unchecked verification items | 6 |
| `context/specs/014-dual-vcs-provider/done.md` | Add closure reconciliation notes | 6 |

### Mirror Copies

Only required for files under framework-managed mirrored content (`.ai-engineering/skills/**`):

| Canonical | Mirror |
|-----------|--------|
| `.ai-engineering/skills/govern/create-skill.md` | `src/ai_engineering/templates/.ai-engineering/skills/govern/create-skill.md` |
| `.ai-engineering/skills/govern/integrity-check.md` | `src/ai_engineering/templates/.ai-engineering/skills/govern/integrity-check.md` |

## File Structure

```
.ai-engineering/
  context/specs/017-openclaw-carryover-remediation/
    spec.md
    plan.md
    tasks.md
    done.md
```

## Session Map

| Phase | Name | Size | Description |
|-------|------|------|-------------|
| 0 | Scaffold + Activate | S | Create spec files, activate `_active.md`, update product-contract Active Spec |
| 1 | Skill Requirements Model | M | Expand requirement metadata and integrity validation |
| 2 | Skills Status Diagnostics | M | Surface eligibility and missing requirement causes |
| 3 | CI Security Parity + Workflow Sanity | M | Add `gitleaks`, `semgrep`, and workflow sanity lane |
| 4 | Spec-015 Carryover Security/Tamper Tasks | L | Complete tasks 5.6-5.10 |
| 5 | CI Scope Optimization + Install Smoke | M | docs-only routing and install smoke flow |
| 6 | Spec-014 Closure Reconciliation | S | Align status/tasks/done consistency |
| 7 | Verification | S | Run tests, gates, and `ai-eng validate` |
| 8 | Close | S | `done.md`, final metadata, PR prep |

## Patterns

- Security-first ordering: complete blocking enforcement/tamper work before UX niceties.
- Backward-compatible schema evolution: new requirement fields optional, old skills remain valid.
- No policy weakening: no bypass flags or reduced gate severity to make CI green.
- Atomic phase commits: `spec-017: Phase N — <description>`.
- Mirror discipline: canonical and template mirror stay byte-identical for skill docs.
