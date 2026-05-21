# OPA Policy Engine Integration

Use OPA `.rego` policies under `.ai-engineering/policies/` over ad-hoc procedural checks. Spec-122 Phase C swapped the in-tree mini-Rego interpreter for upstream OPA; spec-123 wired it into pre-commit, pre-push, and `risk accept`.

- Prefer existing policy files over re-implementing the same gate.
- The evaluator (`src/ai_engineering/governance/opa_runner.py`) is owned by governance code, not by this skill.
- If a rule exceeds OPA's grammar, STOP and escalate to spec/implementation work.

Every OPA evaluation is recorded in `framework-events.ndjson`. Inspect via:

```bash
ai-eng audit replay   # span tree over framework-events.ndjson (filter kind=policy_decision)
```

`ai-eng doctor` runs four advisory OPA probes (binary, version, bundle-load, bundle-signature). Failures surface as WARN (non-blocking).

## Key files

- `.ai-engineering/policies/branch_protection.rego` — branch-push policy.
- `.ai-engineering/policies/commit_conventional.rego` — conventional-commits policy.
- `.ai-engineering/policies/risk_acceptance_ttl.rego` — risk-acceptance TTL policy.
- `src/ai_engineering/governance/opa_runner.py` — OPA subprocess wrapper.
- `src/ai_engineering/governance/decision_log.py` — emits `kind='policy_decision'` events.
- `src/ai_engineering/policy/checks/opa_gate.py` — shared deny-rule adapter.
- `src/ai_engineering/doctor/runtime/opa_health.py` — advisory health probes.
