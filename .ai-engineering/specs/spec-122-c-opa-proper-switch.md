---
spec: spec-122-c
title: Framework Cleanup Phase 1-C — OPA Proper Switch + Governance Wiring
status: approved
effort: medium
---

# Spec 122-c — OPA Proper Switch + Governance Wiring

> Sub-spec of [spec-122 master](./spec-122-framework-cleanup-phase-1.md).
> Implements decisions D-122-09, D-122-29 (governance test slice),
> D-122-36. **Depends on spec-122-a** (cleaned config surfaces) and
> **spec-122-b** (state.db.events table needed for `policy_decision`
> event logging via OTLP collector). May proceed in parallel with
> spec-122-b after spec-122-a merges.

## Summary

Replaces the custom mini-Rego interpreter in
`src/ai_engineering/governance/policy_engine.py` (~400 LOC) with **OPA
proper** — the CNCF-graduated, ~50 MB Go binary used by Netflix, Capital
One, and Atlassian. The three existing `.rego` policies
(`branch_protection.rego`, `commit_conventional.rego`,
`risk_acceptance_ttl.rego`) are migrated from the custom subset syntax
to OPA Rego v1 (full builtins, including crypto). Three hooks become
real teeth: `pre-commit` invokes `data.commit_conventional.deny`,
`pre-push` invokes `data.branch_protection.deny`, `/ai-risk-accept`
invokes `data.risk_acceptance_ttl.deny`. Decisions are logged via OTLP
to the existing `state.db.events` projection (kind=`policy_decision`).
The policy bundle is built and signed via `opa build` + `opa sign`
producing `.signatures.json` (JWT, RSA-256). `opa test --coverage` runs
in CI with ≥ 90% line coverage gate. The `.git/hooks/pre-commit` shell
wrapper installed by `scripts/install.sh` is updated to invoke the OPA
chain after the existing `ruff` + `gitleaks` + format-check sequence.

This sub-spec carries the second-highest blast radius of Phase 1
because it touches the governance hot path. Failure modes are
fail-open (missing `opa` binary surfaces a `framework_error` event
with a clear "install opa" message; never silently bypass the gate).

## Goals

- `opa` binary added to `manifest.yml required_tools.baseline` with
  version pin (`>= 0.70.0,< 1.0.0` or v1 release-track equivalent).
- `ai-eng install` detects the platform and installs `opa`:
  - macOS / Linux: `brew install opa` (preferred).
  - Linux fallback: direct binary download from
    https://github.com/open-policy-agent/opa/releases.
  - Windows: `winget install OpenPolicyAgent.OPA` (preferred); fallback
    to direct binary download.
- Three `.rego` files migrated from custom mini-Rego subset to OPA
  Rego v1 syntax (full crypto builtins available).
- `opa test --coverage` runs in CI; merge gate requires ≥ 90% line
  coverage per policy.
- Bundle build: `opa build -o bundle.tar.gz .ai-engineering/policies/`
  produces a versioned bundle artifact.
- Bundle signing: `opa sign --signing-key <dev-key.pem> --signing-alg
  RS256 .ai-engineering/policies/` produces `.signatures.json`
  containing JWT-signed file hashes.
- `.git/hooks/pre-commit` shell wrapper updated by `scripts/install.sh`
  to invoke `opa eval --bundle .ai-engineering/policies/ --input <input>
  'data.commit_conventional.deny'` after existing checks.
- `pre-push` hook invokes `branch_protection.deny`.
- `/ai-risk-accept` skill invokes `risk_acceptance_ttl.deny`.
- Decision logs export to OTLP collector configured at
  `state/runtime/otel-config.yml`; events land in `state.db.events`
  with `kind='policy_decision'`.
- `src/ai_engineering/governance/policy_engine.py` deprecated
  (replaced by a thin shim that shells out to `opa eval`); the custom
  mini-Rego interpreter is deleted in the same sub-spec.
- `tests/integration/governance/test_opa_eval.py` invokes `opa eval`
  for each policy with golden inputs and asserts allow / deny
  verdicts.
- Hot-path budget preserved: `opa eval` typical < 10 ms for structured
  inputs; pre-commit total budget remains < 1 s p95.

## Non-Goals

- Migrating to Regorus (Rust mini-OPA, 1.9-6.3 MB binary). Documented
  as a future-spec option for confidential-computing or edge builds;
  Phase 1 default is full OPA for OTLP-native decision logging,
  bundle signing, and CNCF ecosystem alignment.
- Migrating to OPA-WASM (compiled `.wasm` modules embedded in Python).
  1317% Go-to-WASM execution penalty (per benchmark research) makes
  this a future option, not Phase 1.
- Authoring new policies beyond the existing three.
- Production key management for bundle signing. Phase 1 uses a single
  documented dev-machine signing key; production rotation strategy
  deferred to a follow-up governance / key-management spec.
- Wiring policies to runtime hooks beyond pre-commit / pre-push /
  risk-accept (a future spec may extend to `/ai-pr` review or
  `/ai-release-gate` evaluation).

## Decisions

This sub-spec **imports** the following master decisions verbatim:

| ID | Decision title |
|---|---|
| D-122-09 | OPA proper switched in; custom mini-Rego deprecated |
| D-122-29 (governance slice) | Phase 1 test coverage — OPA wiring tests + bundle integrity tests |
| D-122-36 | Pre-commit gate updated for OPA wiring |

## Acceptance Criteria

- `which opa` returns a path; `opa version` returns ≥ `0.70.0`.
- `cat .ai-engineering/policies/.signatures.json` shows a valid JWT
  with file SHA-256 entries for each `.rego` file.
- `opa test --coverage .ai-engineering/policies/` reports ≥ 90% line
  coverage per policy.
- `git commit -m 'feat: bad subject'` is rejected by pre-commit with
  the OPA-emitted reason (Conventional Commits violation).
- `git push origin main` is rejected by pre-push (branch protection).
- `ai-eng risk-accept --finding <hash> --ttl 30d` is rejected when
  TTL exceeds the policy maximum.
- `sqlite3 state.db "SELECT count(*) FROM events WHERE
  kind='policy_decision'"` returns ≥ 1 after a single OPA invocation.
- `find src/ai_engineering/governance -name 'policy_engine.py'`
  returns either empty (full delete) or a thin shim file ≤ 50 LOC.
- Hot-path SLO test
  (`tests/unit/hooks/test_hot_path_slo.py::test_pre_commit_under_1s_p95`)
  passes with the OPA wiring in place.
- `tests/integration/governance/test_opa_eval.py::test_branch_protection`,
  `::test_commit_conventional`, `::test_risk_acceptance_ttl` all pass
  on golden inputs.

## Risks

- **OPA binary footprint on container CI**: 50 MB binary inflates
  Docker layers and CI cold-start time. **Mitigation**: `opa` is
  baked into the CI image at build time (Dockerfile RUN step); no
  per-job download.
- **Rego v1 syntax migration drift**: the custom mini-Rego files may
  use idioms not supported in v1. **Mitigation**: `opa test` runs
  after each migration; coverage flag asserts ≥ 90% line coverage;
  hand-review each `.rego` against
  https://www.openpolicyagent.org/docs/v1.2/policy-language/ before
  merge.
- **Bundle signing key management surface area**: introducing
  JWT-signed bundles introduces a key-rotation concern.
  **Mitigation**: Phase 1 uses a single dev-machine signing key
  documented in the spec-122-c plan; production rotation strategy
  deferred.
- **Pre-commit budget regression with OPA**: hot-path is < 1 s p95;
  OPA evaluation adds ~10 ms but binary cold-start could be ~100 ms.
  **Mitigation**: `tests/unit/hooks/test_hot_path_slo.py` enforces
  the budget; if regression detected, switch to `opa eval --watch`
  daemon mode for repeated invocations within a single shell session.
- **Custom mini-Rego deletion stranding callers**: the custom
  interpreter has 2 known callers (doctor, installer). **Mitigation**:
  shim layer at `policy_engine.py` translates legacy `evaluate()`
  calls to `opa eval`; both interfaces preserved for one release
  before full delete.
- **Windows OPA install path**: `winget install OpenPolicyAgent.OPA`
  may fail on managed enterprise Windows. **Mitigation**: direct
  binary download fallback documented in CLAUDE.md install section;
  `ai-eng install --opa-path <path>` accepts pre-installed binaries.
- **Decision log volume**: OPA fires on every commit + push +
  risk-accept; log volume could pollute `state.db.events`.
  **Mitigation**: OPA decision log mask filters sensitive fields
  (per `data.system.log.mask` policy); OTLP exporter samples at
  100% only for `outcome='blocked'`; `outcome='allow'` sampled at
  10%.

## References

- doc: spec-122-framework-cleanup-phase-1.md (master)
- doc: spec-122-a-hygiene-and-evals-removal.md (dependency)
- doc: spec-122-b-engram-and-state-unify.md (dependency — events table)
- doc: .ai-engineering/policies/branch_protection.rego
- doc: .ai-engineering/policies/commit_conventional.rego
- doc: .ai-engineering/policies/risk_acceptance_ttl.rego
- doc: src/ai_engineering/governance/policy_engine.py
- doc: scripts/install.sh
- doc: .ai-engineering/scripts/hooks/_lib/integrity.py
- ext: https://www.openpolicyagent.org/docs/
- ext: https://www.openpolicyagent.org/docs/v1.2/policy-language/
- ext: https://github.com/open-policy-agent/opa
- ext: https://github.com/open-policy-agent/opa/releases
- ext: https://github.com/open-policy-agent/setup-opa
- ext: https://github.com/microsoft/regorus
- ext: https://www.cncf.io/projects/open-policy-agent-opa/
