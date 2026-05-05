---
total: 18
completed: 0
---

# Plan: sub-003 OPA Proper Switch

## Plan

exports:
  - ai_engineering.governance.opa_runner.OpaResult
  - ai_engineering.governance.opa_runner.OpaError
  - ai_engineering.governance.opa_runner.evaluate
  - ai_engineering.governance.opa_runner.evaluate_bundle
  - ai_engineering.governance.opa_runner.version
  - ai_engineering.governance.decision_log.emit_policy_decision
  - ai_engineering.governance.policy_engine.evaluate  # legacy shim ≤ 50 LOC
  - ai_engineering.governance.policy_engine.Decision  # legacy shim
  - tool_registry["opa"]  # installer entry
  - .ai-engineering/policies/ (signed bundle)
  - .ai-engineering/policies/.signatures.json (JWT)
  - .ai-engineering/policies/{branch_protection,commit_conventional,risk_acceptance_ttl}.rego (v1)
  - policy_decision events (kind='policy_decision') to NDJSON + state.db.events

imports:
  - sub-001: cleaned manifest.yml (required_tools.baseline block well-formed)
  - sub-001: spec-122-c-policy_engine deletion not blocked by other consumers
  - sub-002: state.db.events table (kind='policy_decision') -- OPTIONAL
    runtime dependency; sub-003 falls back to NDJSON-only when absent.

- [ ] T-3.1: Migrate three .rego files to OPA Rego v1 syntax
  - **Files**: .ai-engineering/policies/branch_protection.rego, .ai-engineering/policies/commit_conventional.rego, .ai-engineering/policies/risk_acceptance_ttl.rego
  - **Done**: `opa parse <file>` exits 0 for each policy; `opa fmt --diff` is clean; risk_acceptance_ttl.rego uses `time.parse_rfc3339_ns` instead of lexicographic string compare; branch_protection.rego replaces inline `or` with a helper rule `protected_branch[name]`.

- [ ] T-3.2: Author companion `_test.rego` files for opa test --coverage
  - **Files**: .ai-engineering/policies/branch_protection_test.rego, .ai-engineering/policies/commit_conventional_test.rego, .ai-engineering/policies/risk_acceptance_ttl_test.rego
  - **Done**: `opa test --coverage --format json .ai-engineering/policies/` reports `≥ 0.90` line coverage per policy; each policy has at least one allow case, one deny case, and one boundary case (empty/missing field).

- [ ] T-3.3: Add `opa` to tool registry + manifest.yml baseline
  - **Files**: src/ai_engineering/installer/tool_registry.py, .ai-engineering/manifest.yml
  - **Done**: `TOOL_REGISTRY["opa"]` declares `BrewMechanism("opa")` + `GitHubReleaseBinaryMechanism(repo="open-policy-agent/opa", binary="opa")` for darwin; `GitHubReleaseBinaryMechanism(...)` for linux; `WingetMechanism("OpenPolicyAgent.OPA") + ScoopMechanism("opa") + GitHubReleaseBinaryMechanism(...)` for win32. Verify: `_verify(["opa", "version"], _RE_SEMVER)`. `manifest.yml required_tools.baseline` adds `{name: opa, version_range: ">=0.70.0,<2.0"}`.

- [ ] T-3.4: Test opa install path per OS (RED then GREEN)
  - **Files**: tests/unit/installer/test_opa_install.py
  - **Done**: pytest verifies `TOOL_REGISTRY["opa"]["darwin"][0]` is `BrewMechanism`, fallback chain order matches spec, verify regex matches sample `opa version` output. Tests pass without invoking the network.

- [ ] T-3.5: Implement opa_runner subprocess wrapper with shutil.which cache
  - **Files**: src/ai_engineering/governance/opa_runner.py
  - **Done**: `evaluate(query, input_dict, *, bundle_path=None, timeout=5.0) -> OpaResult` runs `opa eval --bundle <path> --input <stdin>` returning `(allow: bool, deny_messages: list[str], raw: dict)`. Missing binary raises `OpaError("opa not installed; run 'ai-eng install'")`. `version()` parses `opa version --format json`. Path lookup memoised on first call.

- [ ] T-3.6: Test opa_runner with subprocess mocks (RED then GREEN)
  - **Files**: tests/unit/governance/test_opa_runner.py
  - **Done**: subprocess mocked with `monkeypatch`; tests cover (a) successful allow verdict, (b) deny with messages, (c) missing binary OpaError, (d) timeout escalation, (e) malformed JSON output, (f) bundle path forwarding. ≥ 95% line coverage on `opa_runner.py`.

- [ ] T-3.7: Implement decision_log with sample mask + dual-write fallback
  - **Files**: src/ai_engineering/governance/decision_log.py
  - **Done**: `emit_policy_decision(policy, input, decision, *, project_root)` writes a `kind='policy_decision'` event to `framework-events.ndjson` always. When `state.db` exists AND `events` table is present, also INSERTs a row. Sample mask: 100% on `outcome='blocked'`; 10% deterministic sampling (sha256 hash mod 10) on `outcome='allow'`. Sensitive fields (`input.subject`, `input.justification`) masked per `data.system.log.mask` policy.

- [ ] T-3.8: Test decision_log dual-write + sample mask (RED then GREEN)
  - **Files**: tests/unit/governance/test_decision_log.py
  - **Done**: tests cover (a) NDJSON-only path when state.db absent, (b) dual-write when state.db + events table present, (c) sample mask: 100/100 blocked recorded, ≈10/100 allow recorded, (d) field redaction for `subject` / `justification`. Uses `tmp_path` for both files.

- [ ] T-3.9: Build + sign bundle scaffold (.manifest + .signatures.json)
  - **Files**: .ai-engineering/policies/.manifest, scripts/build-policy-bundle.sh (or python helper inside ai_engineering.governance.bundle)
  - **Done**: `opa build -o bundle.tar.gz .ai-engineering/policies/` produces a versioned bundle. `opa sign --signing-alg RS256 --signing-key <pub-key-path> .ai-engineering/policies/` produces `.signatures.json` containing JWT-signed file hashes for each .rego. `opa run --bundle bundle.tar.gz --verification-key <key>` verifies clean.

- [ ] T-3.10: Test bundle signing round-trip (golden inputs)
  - **Files**: tests/integration/governance/test_bundle_signing.py
  - **Done**: pytest builds bundle in `tmp_path`, signs with throwaway key, parses `.signatures.json` JWT, asserts each `.rego` SHA-256 matches `hashlib.sha256(file.read_bytes()).hexdigest()`. Mutating a `.rego` file fails verification.

- [ ] T-3.11: Wire OPA into pre-commit gate (commit_conventional.deny)
  - **Files**: src/ai_engineering/policy/checks/commit_msg.py, src/ai_engineering/policy/checks/opa_gate.py (NEW)
  - **Done**: `validate_commit_message` delegates the format check to `opa_runner.evaluate("data.commit_conventional.deny", {"subject": ...})`. On deny, `GateCheckResult(name="commit-msg-format", passed=False, output=<deny message from OPA>)`. Existing `inject_gate_trailer` path preserved. Hot-path: opa eval cached bundle path; cold-start ≤ 100 ms once per process.

- [ ] T-3.12: Wire OPA into pre-push gate (branch_protection.deny)
  - **Files**: src/ai_engineering/policy/checks/branch_protection.py
  - **Done**: `check_branch_protection` invokes `opa_runner.evaluate("data.branch_protection.deny", {"branch": current_branch(), "action": "push"})`. Legacy `branch in PROTECTED_BRANCHES` Python fallback retained behind a `if not opa.available()` branch (fail-closed message guides install).

- [ ] T-3.13: Wire OPA into ai-eng risk accept (risk_acceptance_ttl.deny)
  - **Files**: src/ai_engineering/cli_commands/risk_cmd.py, src/ai_engineering/policy/checks/risk.py
  - **Done**: `risk_accept` calls `opa_runner.evaluate("data.risk_acceptance_ttl.deny", {"ttl_expires_at": expires.isoformat(), "now": datetime.now(UTC).isoformat(), "severity": severity})` before persisting the DEC entry. Deny verdict surfaces a typer.Exit(2) with the OPA reason. `check_expiring_risk_acceptances` (pre-commit warning) reuses the same query.

- [ ] T-3.14: Integration golden tests for all three policies via opa eval subprocess
  - **Files**: tests/integration/governance/test_opa_eval.py
  - **Done**: pytest invokes `opa eval --bundle .ai-engineering/policies/ --input <fixture> 'data.<package>.deny'` for each policy with at least 4 fixtures (allow, deny, edge, malformed). All asserts verify the returned JSON matches expected verdict. Skips with clear marker when `opa` not installed locally.

- [ ] T-3.15: Hot-path SLO test (pre-commit < 1 s p95)
  - **Files**: tests/unit/hooks/test_hot_path_slo.py
  - **Done**: test runs `policy.gates.run_gate(GateHook.PRE_COMMIT, ...)` 50 times against a fixture repo, asserts p95 wall-clock < 1000 ms with the OPA wiring active. Includes a separate assertion that `opa_runner.evaluate` cold-start < 250 ms and warm < 30 ms.

- [ ] T-3.16: Replace policy_engine.py with thin shim ≤ 50 LOC + delete legacy interpreter
  - **Files**: src/ai_engineering/governance/policy_engine.py, src/ai_engineering/governance/__init__.py, tests/unit/governance/test_policy_engine.py
  - **Done**: `policy_engine.py` reduced to ≤ 50 LOC. Public API preserved: `Decision` dataclass + `evaluate(path, input) -> Decision` that translates to `opa_runner.evaluate(query="data.<package>.allow", input)` and back-fills `Decision.reason` from any deny rule fired. Existing six tests in `test_policy_engine.py` pass against the shim, proving backwards compatibility.

- [ ] T-3.17: CI workflow for opa test --coverage gate
  - **Files**: .github/workflows/opa-test.yml
  - **Done**: workflow installs `opa` via `setup-opa@v3` (or direct release download), runs `opa test --coverage --format json .ai-engineering/policies/`, parses JSON, fails the job when any policy reports < 0.90 line coverage.

- [ ] T-3.18: Update ai-governance skill + manifest doctor wiring
  - **Files**: .claude/skills/ai-governance/SKILL.md, src/ai_engineering/templates/project/.claude/skills/ai-governance/SKILL.md, src/ai_engineering/templates/project/.gemini/skills/ai-governance/SKILL.md, src/ai_engineering/templates/project/.codex/skills/ai-governance/SKILL.md, src/ai_engineering/templates/project/.github/skills/ai-governance/SKILL.md
  - **Done**: SKILL.md no longer references `policy_engine.py` as the source-of-truth engine; references `opa eval --bundle .ai-engineering/policies/` and the bundle signature path. Lists the three policies + invocation surface (pre-commit, pre-push, `ai-eng risk accept`). Cross-IDE mirrors stay byte-identical (sync_command_mirrors check passes).

### Confidence

**Level**: high

**Justification**:
- Existing `.rego` files already use Rego v1 idioms (`if`, `default allow := false`, bracketed `deny[msg]`); migration is a small refinement, not a rewrite.
- `tool_registry.py` has a clear `gitleaks`-shaped template to copy for OPA install across darwin/linux/win32.
- The custom `policy_engine.py` has **zero** production callers (only test files import it); the shim path is an insurance policy, not a load-bearing requirement.
- The hot-path is already wrapped behind `policy/orchestrator.run_gate` + `policy/checks/*`; OPA insertion is additive without restructuring the orchestrator.
- OTLP / state.db dual-write is gated on capability detection so sub-003 can land without sub-002.
- Bundle signing has a documented Phase 1 dev-key path; production rotation is explicitly deferred.

**Residual risks** (medium-impact, do not lower confidence below high):
- Bundle signing key handling: committed pub key + locally-generated private key on first install. Plan task 3.9 owns the generation logic.
- `winget`-managed Windows enterprise installs may fall through; the GitHub-release fallback closes the gap.
- Cold-start ~100 ms for `opa eval`. Hot-path test (T-3.15) enforces the 1 s p95 budget; if regression detected, batch invocation per gate (single eval with all inputs) cuts cold-start cost to once per gate.

## Self-Report

[EMPTY — populated by Phase 4]
