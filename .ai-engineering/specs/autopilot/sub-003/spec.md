---
id: sub-003
parent: spec-122
title: "OPA Proper Switch + Governance Wiring"
status: planning
files:
  - .ai-engineering/policies/branch_protection.rego
  - .ai-engineering/policies/commit_conventional.rego
  - .ai-engineering/policies/risk_acceptance_ttl.rego
  - .ai-engineering/policies/branch_protection_test.rego
  - .ai-engineering/policies/commit_conventional_test.rego
  - .ai-engineering/policies/risk_acceptance_ttl_test.rego
  - .ai-engineering/policies/.manifest
  - .ai-engineering/policies/.signatures.json
  - src/ai_engineering/governance/policy_engine.py
  - src/ai_engineering/governance/__init__.py
  - src/ai_engineering/governance/opa_runner.py
  - src/ai_engineering/governance/decision_log.py
  - src/ai_engineering/installer/tool_registry.py
  - src/ai_engineering/installer/mechanisms/__init__.py
  - src/ai_engineering/policy/gates.py
  - src/ai_engineering/policy/checks/branch_protection.py
  - src/ai_engineering/policy/checks/commit_msg.py
  - src/ai_engineering/policy/checks/risk.py
  - src/ai_engineering/cli_commands/risk_cmd.py
  - .ai-engineering/manifest.yml
  - .ai-engineering/state/runtime/otel-config.yml
  - .claude/skills/ai-governance/SKILL.md
  - tests/integration/governance/test_opa_eval.py
  - tests/integration/governance/test_bundle_signing.py
  - tests/unit/governance/test_policy_engine.py
  - tests/unit/governance/test_opa_runner.py
  - tests/unit/governance/test_decision_log.py
  - tests/unit/installer/test_opa_install.py
  - tests/unit/hooks/test_hot_path_slo.py
  - .github/workflows/opa-test.yml
  - keys/opa-bundle-signing-dev.pem
depends_on: [sub-001]
source_spec: .ai-engineering/specs/spec-122-c-opa-proper-switch.md
---

# Sub-Spec 003: OPA Proper Switch + Governance Wiring

## Scope

Replace custom mini-Rego interpreter at
`src/ai_engineering/governance/policy_engine.py` (~400 LOC) with OPA proper
(CNCF-graduated, ~50 MB Go binary). Migrate three `.rego` policies
(branch_protection, commit_conventional, risk_acceptance_ttl) from custom
subset to OPA Rego v1 syntax. Wire pre-commit (commit_conventional.deny),
pre-push (branch_protection.deny), `/ai-risk-accept` (risk_acceptance_ttl.deny).
Build + sign bundle (`opa build` + `opa sign` JWT). OTLP decision logs export
to `state.db.events` (kind=`policy_decision`). `opa test --coverage` ≥ 90% in CI.

Preserves hot-path budget (<1s p95 pre-commit; OPA eval ~10ms).
Fail-open on missing binary (clear "install opa" message).

## Source

Full spec: `.ai-engineering/specs/spec-122-c-opa-proper-switch.md`.

Decisions imported: D-122-09, D-122-29 (governance test slice), D-122-36.

## Exploration

### Existing Files

- `.ai-engineering/policies/branch_protection.rego` (19 LOC) — package
  `branch_protection`. Already uses Rego v1 idioms (`if`, `default allow := false`,
  bracketed `deny["msg"]`). Inputs: `{branch, action}`. Inlines main/master
  check via `or` because the custom subset doesn't allow helper rules.
- `.ai-engineering/policies/commit_conventional.rego` (16 LOC) — package
  `commit_conventional`. Inputs: `{subject}`. Uses `regex.match`. Already
  v1-compatible.
- `.ai-engineering/policies/risk_acceptance_ttl.rego` (16 LOC) — package
  `risk_acceptance_ttl`. Inputs: `{ttl_expires_at, now}`. Uses lexicographic
  RFC-3339 string comparison; v1 supports this but `time.parse_rfc3339_ns`
  is the idiomatic builtin and should replace it for correctness.
- `src/ai_engineering/governance/policy_engine.py` (611 LOC, deletion target).
  Custom mini-Rego interpreter: `Decision`, `PolicyError`, `evaluate(path, input)`.
  Internals: `_strip_comment`, `_parse_policy`, `_evaluate_node`, `_truthy`,
  recursive descent expression parser supporting `regex.match` +
  `time.parse_rfc3339_ns`. **No production callers** outside test files; only
  imported by `tests/unit/governance/test_policy_engine.py` and indirectly via
  `src/ai_engineering/governance/__init__.py`. **No callers in installer/
  service.py or doctor** (spec text mentions 2 callers but `grep` shows zero
  imports of `policy_engine` or `from ...governance import` outside tests).
- `src/ai_engineering/governance/__init__.py` (20 LOC) — re-exports
  `Decision, evaluate`. Becomes the shim location for backwards-compat.
- `src/ai_engineering/installer/tool_registry.py` — declarative
  per-tool/per-OS install mechanism table. Adds `opa` entry following the
  `gitleaks` template (Brew/darwin, GitHub release/linux,
  Winget/Scoop/win32). Verify regex follows `_RE_SEMVER` pattern via
  `opa version --format json`.
- `src/ai_engineering/installer/mechanisms/__init__.py` — exports
  `BrewMechanism`, `GitHubReleaseBinaryMechanism`, `WingetMechanism`,
  `ScoopMechanism`. Reused as-is (no new mechanism class needed).
- `.ai-engineering/manifest.yml` — `required_tools.baseline` block currently
  lists `gitleaks`, `semgrep` (no Windows), `jq`. OPA adds a fourth entry
  with `version_range: ">=0.70.0,<1.0"` (or `>=1.0.0,<2.0.0` if using v1
  release-track per spec text "v1 release-track equivalent").
- `src/ai_engineering/policy/gates.py` (~600 LOC) — orchestrates `pre-commit`
  / `pre-push` / `commit-msg` checks via stack-aware dispatch. Calls
  `_run_pre_commit_checks` / `_run_pre_push_checks`, which delegate to
  `policy/checks/*`. Hot-path entry; wraps OPA invocation behind a new
  `policy/checks/opa_gate.py` check helper (NEW FILE).
- `src/ai_engineering/policy/checks/branch_protection.py` (~80 LOC currently)
  — runs Python-level branch-protection check via
  `current_branch() in PROTECTED_BRANCHES`. Refactored to invoke OPA
  `data.branch_protection.deny` so the canonical decision lives in Rego.
- `src/ai_engineering/policy/checks/commit_msg.py` — `validate_commit_message`
  / `inject_gate_trailer`. Refactored to delegate the format check to OPA
  `data.commit_conventional.deny`.
- `src/ai_engineering/policy/checks/risk.py` — `check_expiring_risk_acceptances`
  / `check_expired_risk_acceptances`. Refactored to invoke OPA
  `data.risk_acceptance_ttl.deny` per finding.
- `src/ai_engineering/cli_commands/risk_cmd.py` — `ai-eng risk *` namespace
  (accept, accept-all, renew, resolve, revoke, list, show). The
  `risk_acceptance_ttl` policy is invoked when **creating** a risk
  acceptance with `--ttl <duration>` to enforce per-severity max TTLs and
  when **listing** to flag expired entries.
- `.git/hooks/pre-commit` and `.git/hooks/pre-push` — generated by
  `src/ai_engineering/hooks/manager.py:_GATE_COMMANDS`. Both are bash
  wrappers calling `ai-eng gate pre-commit` / `ai-eng gate pre-push`.
  No edit to the wrapper itself; the OPA invocation is added inside the
  Python `gates.py` chain so the marker line + manifest sha256 are
  preserved (hook integrity stays intact).
- `.ai-engineering/scripts/hooks/_lib/integrity.py` (~150 LOC) — sha256
  hook-bytes manifest enforcement (`AIENG_HOOK_INTEGRITY_MODE=enforce`).
  Untouched; the `ai-eng gate pre-commit` shell wrapper bytes stay
  identical so no manifest regen needed.
- `.claude/skills/ai-governance/SKILL.md` — references
  `policy_engine.py` and the three `.rego` files. Updated to point at
  `opa eval` invocations and the bundle.
- `tests/unit/governance/test_policy_engine.py` (~270 LOC) — six
  per-policy round-trip cases. Becomes test for the shim's
  backwards-compat surface (allow/deny verdicts must stay equivalent).
- **NEW FILE** `src/ai_engineering/governance/opa_runner.py` —
  thin Python wrapper: `OpaResult`, `OpaError`, `evaluate(query, input)`,
  `evaluate_bundle(bundle_path, query, input)`, `version()`. Caches the
  `opa` binary path via `shutil.which("opa")` lookup; raises
  `OpaError("install opa via `ai-eng install`")` when absent.
- **NEW FILE** `src/ai_engineering/governance/decision_log.py` —
  emits `policy_decision` events. Phase 1 dual-write: (a) NDJSON
  `framework-events.ndjson` via `state.observability.emit_*` for
  parity, (b) optional OTLP push when sub-002's `state.db.events` is
  available (detected by file existence). 100% sample on `outcome='blocked'`,
  10% sample on `outcome='allow'`.
- **NEW FILE** `.ai-engineering/policies/.manifest` — list of `.rego` files
  in the bundle (used by `opa build`).
- **NEW FILE** `.ai-engineering/policies/.signatures.json` — generated by
  `opa sign --signing-alg RS256`; JWT carrying `{files, exp, iss}` claims
  with file SHA-256 entries.
- **NEW FILE** `.ai-engineering/policies/{branch_protection,commit_conventional,risk_acceptance_ttl}_test.rego`
  — companion `_test.rego` files with `test_` prefixed rules so `opa test
  --coverage` produces line-coverage data.
- **NEW FILE** `tests/integration/governance/test_opa_eval.py` — golden
  inputs per policy, asserts allow/deny verdicts via
  subprocess `opa eval`. Hot-path SLO assertion that bundle-cached
  invocation < 30 ms.
- **NEW FILE** `tests/integration/governance/test_bundle_signing.py` —
  invokes `opa build` + `opa sign`, asserts `.signatures.json` is
  parseable JWT, file SHA-256 entries match disk.
- **NEW FILE** `tests/unit/governance/test_opa_runner.py` — mocks
  subprocess; verifies query construction, missing-binary error path,
  timeout handling.
- **NEW FILE** `tests/unit/governance/test_decision_log.py` — mocks
  NDJSON + state.db writes; verifies sample rates + redaction mask.
- **NEW FILE** `tests/unit/installer/test_opa_install.py` — verifies
  the `opa` entry in `TOOL_REGISTRY` resolves to the right mechanism
  list per OS.
- **NEW FILE** `tests/unit/hooks/test_hot_path_slo.py` — pre-commit
  end-to-end timing assertion (< 1 s p95 over N repeated invocations).
- **NEW FILE** `keys/opa-bundle-signing-dev.pem` — single dev-machine
  RS256 key referenced by `opa sign`. Documented as Phase 1 dev-only;
  production rotation deferred. Added to `.gitignore` if private; pub
  key alone may be committed. **Decision below**: commit pub key only,
  ship the private key out-of-band via the install script.
- **NEW FILE** `.github/workflows/opa-test.yml` — CI job that installs
  `opa`, runs `opa test --coverage --format json`, asserts ≥ 90% line
  coverage per policy.

### Patterns to Follow

- **Tool registry entry shape**: model `opa` exactly on `gitleaks`
  (`tool_registry.py` lines 147-171). `darwin` → `BrewMechanism("opa")`
  + `GitHubReleaseBinaryMechanism(repo="open-policy-agent/opa",
  binary="opa")`. `linux` → `GitHubReleaseBinaryMechanism(...)`.
  `win32` → `WingetMechanism("OpenPolicyAgent.OPA")` +
  `ScoopMechanism("opa")` + `GitHubReleaseBinaryMechanism(...)` fallback.
  Verify: `_verify(["opa", "version"], _RE_SEMVER)`.
- **Rego v1 migration approach**: existing policies already use the
  v1-shaped `if`/`default allow := false` constructs. Migration is
  largely a no-op rename of the inline `or` expression in
  `branch_protection.rego` to a helper rule + adoption of
  `time.parse_rfc3339_ns` in `risk_acceptance_ttl.rego`. The `opa
  fmt` formatter will normalise spacing.
- **Hook gate integration**: follow the existing
  `policy/checks/branch_protection.py` pattern — append to
  `result.checks` with `GateCheckResult(name=..., passed=..., output=...)`.
  The OPA invocation lives in a new `policy/checks/opa_gate.py` helper
  that the existing checks delegate to, preserving the legacy check
  names so test fixtures and dashboards stay valid.
- **Event emission**: follow `state.observability.emit_framework_operation`
  / `emit_gate_event` shape; add a new `emit_policy_decision(...)` in
  `governance/decision_log.py` that sets
  `kind='policy_decision'` and respects the sample mask.
- **Subprocess wrapper hardening**: model `opa_runner.evaluate` on
  `cli_commands/risk_cmd.py` patterns — `subprocess.run` with
  `timeout=5`, `check=False`, capture stderr, raise typed `OpaError`
  on non-zero exit. Use `shutil.which("opa")` cache so cold-start cost
  is paid once per process.
- **Tests directory layout**: `tests/integration/governance/` (existing
  empty parent `tests/integration/`) mirrors `tests/unit/governance/`
  layout. Use `pytest.fixture` for the temp policy bundle build per
  test session.

### Dependencies Map

- **Imports we add** (cross-sub-spec, declared in `imports:`):
  - `state.db.events` table from sub-002 (T-2.4 final
    table). Needed for the OTLP-→-SQLite projection write of
    `kind='policy_decision'` rows. **Optional at runtime**: sub-003
    detects table presence and falls back to NDJSON-only when the
    projection isn't installed yet (parallel-execution safety).
  - `state/observability.emit_framework_operation` — exists today,
    no cross-sub-spec dependency.
- **Imports we drop** (within sub-003): nothing from outside its own
  scope; the only consumer of `governance.policy_engine.evaluate` is
  the now-rewritten test suite.
- **External dependencies introduced**:
  - `opa` Go binary (≥ 0.70.0) — installed via tool registry.
  - `cryptography` Python lib — already in pyproject; used by
    `decision_log.py` for the dev signing key load (no new wheel).
- **Files importing `governance.policy_engine`**: only
  `tests/unit/governance/test_policy_engine.py` (six tests) and
  `tests/integration/test_phase_failure.py` (one fixture). Both
  rewritten to invoke `opa_runner.evaluate` instead. No production
  callers, so the shim path can be a one-release stub or a clean delete.
- **Hook chain**: `.git/hooks/pre-commit` → `ai-eng gate pre-commit`
  → `policy/orchestrator.run_gate` → `policy/checks/*` → (NEW)
  `policy/checks/opa_gate.py` → `governance/opa_runner.evaluate` →
  `governance/decision_log.emit_policy_decision`.

### Risks

- **Bundle signing dev key management surface**: shipping a private
  RS256 key in-repo is a security smell even labelled "dev-only".
  **Mitigation**: commit only the public key; private key generated
  on first `ai-eng install` and stored under
  `~/.config/ai-engineering/opa-bundle-signing-dev.pem` (mode 0600).
  Plan task generates the key on demand.
- **Coverage not real safety**: `opa test --coverage ≥ 90%` is a
  line-coverage gate. The three policies are tiny (16-19 LOC); 90 %
  is trivially met. **Mitigation**: include both allow and deny golden
  cases per policy plus boundary cases (empty input, missing field) so
  branch coverage is meaningful.
- **Dual-write window with sub-002 events table**: until sub-002 lands
  the `events` table, sub-003 must write to NDJSON only. **Mitigation**:
  capability detection in `decision_log.emit_policy_decision`. State.db
  dual-write is gated on `(state_db / state.db).exists()` and table
  introspection. Backfill of the gap window is not needed (NDJSON is the
  immutable source-of-truth; the SQLite projection rebuilds from it).
- **Hot-path regression on cold start**: spec budget < 10 ms eval but
  ~100 ms cold-start. **Mitigation**: a single `opa eval --bundle`
  invocation per gate (one cold start). For risk-cmd evaluations
  inside a single `ai-eng risk *` invocation, batch all findings into a
  single `opa eval` call with `input.findings: []`. Test
  `test_hot_path_slo.py` enforces the budget.
- **Missing `opa` binary fail-open vs fail-closed**: spec says
  fail-open with `framework_error`. **Mitigation accepted**: emit the
  framework_error event AND mark the gate check as `passed=False` with
  a clear `output="opa not installed; run 'ai-eng install'"` so the
  user is forced to fix the install rather than silently bypassing.
  This is a fail-closed-with-clear-message stance; spec language about
  "fail-open" refers to not silently discarding the gate.
- **Windows OPA install**: `winget install OpenPolicyAgent.OPA` may
  fail on managed enterprise Windows. **Mitigation**: declared chain
  is `winget` → `scoop` → direct GitHub release. Tool registry
  declares all three.
- **Custom mini-Rego deletion vs. shim**: spec accepts either. **Decision
  pushed to plan**: ship a shim ≤ 50 LOC at
  `governance/policy_engine.py` for one release, that maps the legacy
  `evaluate(path, input) -> Decision` API to a single
  `opa_runner.evaluate_file(path, query="data.<package>.allow",
  input=input)` call. Original 611 LOC deleted in the same sub-spec
  PR; the shim keeps tests/integration importing without breaking.
- **`risk_cmd.py` invocation surface drift**: the spec assumes a
  `/ai-risk-accept` skill that does not exist (we have
  `ai-eng risk accept` CLI). **Mitigation**: wire the OPA call
  inside the CLI command (`risk_cmd.py:risk_accept`) and update
  `.claude/skills/ai-governance/SKILL.md` to document the CLI surface.
  Adds a `tasks/T-3.K` line to the plan to clarify the skill boundary.
- **`scripts/install.sh` does not exist**: spec text references
  this path; the install entry-point is Python-based
  (`installer/service.py`). **Mitigation**: tool-install lives in
  `tool_registry.py`; the hook wrapper at `.git/hooks/pre-commit` is
  generated by `hooks/manager.py`. No bash install.sh edit needed.

## Acceptance

See source spec. Summary:
- `which opa` returns path; `opa version` ≥ 0.70.0
- `.signatures.json` valid JWT with file SHA-256 entries
- `opa test --coverage` ≥ 90% per policy
- `git commit -m 'feat: bad subject'` rejected by pre-commit (Conventional Commits)
- `git push origin main` rejected by pre-push (branch protection)
- `ai-eng risk accept` rejected when TTL exceeds policy max
- `state.db.events` has `kind='policy_decision'` rows after invocation
  (or NDJSON during the parallel-execution window with sub-002)
- `policy_engine.py` is shim ≤ 50 LOC OR fully deleted
- Hot-path SLO test passes
- `tests/integration/governance/test_opa_eval.py` golden tests pass
