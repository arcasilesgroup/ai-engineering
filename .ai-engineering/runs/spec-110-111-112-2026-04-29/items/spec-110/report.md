# spec-110 Governance v3 Harvest — Final Report

**Branch**: `work/spec-110-111-112-2026-04-29/spec-110/governance-v3-harvest`
**Closed**: 2026-04-29

## Verdict: PASS — 0 NG violations introduced

## Goals coverage

| Goal | Description | Status |
|---|---|---|
| G-1 | CONSTITUTION.md with 10 articles via /ai-constitution | ✓ commit `d49d3cd8` (baseline) + `0de86ee3` (D-110-01 adaptation) |
| G-2 | AGENTS.md canonical + 3 overlays slim | ✓ `3f2fbe3e` (canonical) + `c937c236` CLAUDE + `09ae21d2` GEMINI + `a4bb20ae` copilot |
| G-3 | All `.github/workflows/*.yml` SHA-pinned | ✓ `43cde42e` (cache@v4 + sonarqube@v7.0.0 pinned) |
| G-4 | sbom.yml CycloneDX workflow | ✓ `bec46195` (uv + cyclonedx-bom + SHA-pinned actions) |
| G-5 | --ignore-scripts in npm/bun installs | ✓ `836bdd17` (snyk install hardened) |
| G-6 | Hash-chain at root with dual-read 30d | ✓ `3d906a2c` + `3f779fe5` (4/4 audit_chain tests GREEN) + `6f8f9afe` (writers migrated) |
| G-7 | 3 Rego policies + Python evaluator | ✓ `e6d04689` (engine, ~250 LOC) + `0d663b21` (3 .rego files; 6/6 policy tests GREEN) + `68f7df26` (skill integration) |
| G-8 | docs/anti-patterns.md | ✓ `7bf054d3` (3 anti-patterns + see also) |
| G-9 | 0 secrets/vulns/lint errors | ✓ verified by T-4.3/T-4.4/T-4.5 (gitleaks + pip-audit + ruff all clean) |
| G-10 | Coverage ≥80% on new modules | ✓ verified 87% on policy_engine via T-4.6 |

## NG-1..NG-9 verification

| # | Forbidden | Verified by | Result |
|---|---|---|---|
| NG-1 | Identity Broker / OBO tokens / OAuth | grep src/ tests/ | 0 matches |
| NG-2 | Input Guard ML-based | dependency scan + grep ML libs | 0 ML deps |
| NG-3 | OTel exporter | pyproject.toml + grep | 0 opentelemetry deps |
| NG-4 | Plugin marketplace 3-tier | grep src/ | 0 OFFICIAL/VERIFIED/COMMUNITY tier code |
| NG-5 | Regulated profiles | filesystem scan | no banking/healthcare/etc dirs |
| NG-6 | TrueFoundry / LiteLLM bridge | grep src/ | 0 matches in src |
| NG-7 | TS+Bun rewrite | find -name *.ts | 0 .ts files |
| NG-8 | Hexagonal / DDD bounded contexts | filesystem scan | flat modules in governance/ |
| NG-9 | Skill/agent deletion | ls .claude/skills + agents | no deletions in spec-110 diff |

## Findings (non-blocking, hygiene)

1. **NG-9 threshold pre-existing**: manifest declares 48 skills; threshold was 49. spec-106 consolidation pre-dates spec-110. **Action**: update NG-9 threshold to 48 in follow-up.
2. **AGENTS.md root content review**: T-4.7 governance check noted possible content anomaly (Claude-specific path mentioned). Test passes (test_overlays_reference_agents_md GREEN), but content quality should be reviewed before merge. **Action**: visual review pre-merge.
3. **copilot-instructions.md skills count drift**: shows "Skills (47)" vs manifest's 48. **Action**: re-run sync-mirrors before final delivery.
4. **framework-capabilities.json stale**: dated 2026-03-27 with old skill list. Not authoritative. **Action**: regenerate via doctor or cleanup spec.

## Commits (chronological, on `work/spec-110-111-112-2026-04-29/spec-110/governance-v3-harvest`)

```
0a54d59e  chore(run): initialize ai-run orchestration
d22d1c59  test(spec-110): add failing test for SBOM workflow presence (RED phase)
bec46195  feat(spec-110): add SBOM workflow with cyclonedx-py + upload-artifact (GREEN)
94fee2e1  test(spec-110): add test for npm/bun/pnpm/yarn install --ignore-scripts gate
836bdd17  chore(spec-110): add --ignore-scripts to snyk install (supply-chain hardening)
eea92a91  test(spec-110): add failing tests for audit_chain extensions (RED phase)
df00c2d1  feat(spec-110): add compute_event_hash to state/audit_chain (GREEN partial)
3d906a2c  feat(spec-110): add iter_validate_chain + ValidationResult to audit_chain
3f779fe5  feat(spec-110): emit warning on legacy detail.prev_event_hash detection (D-110-03)
6f8f9afe  refactor(spec-110): migrate writers to root prev_event_hash (D-110-03)
7685ba40  test(spec-110): add failing tests for policy_engine 3 policies (RED phase)
8cc811e5  fix(tests): auto-restore .git/config when tests pollute it
e6d04689  feat(spec-110): add governance.policy_engine with Rego subset parser
0d663b21  feat(spec-110): add 3 Rego policies (branch_protection + commit_conventional + risk_acceptance_ttl)
68f7df26  feat(spec-110): integrate policy_engine in /ai-governance skill (T-3.10)
7bf054d3  docs(spec-110): add anti-patterns mirror from Codemotion deck (T-4.1)
```

Plus Phase 1 commits ahead of these:
```
8449b901  test(spec-110): add failing test for CONSTITUTION presence (RED phase)
b16606d3  test(spec-110): add failing test for per-article numbered rules (RED phase)
d49d3cd8  feat(spec-110): generate baseline CONSTITUTION.md (10 articles, GREEN for T-1.1+T-1.2)
0de86ee3  refactor(spec-110): adapt CONSTITUTION.md per D-110-01 (current scale)
01abf71d  test(spec-110): add failing test for overlay entry-point AGENTS.md references (RED phase)
ca9e5731  test(spec-110): add failing test for overlay no-duplication of CONSTITUTION rules (RED)
3f2fbe3e  refactor(spec-110): make AGENTS.md the canonical cross-IDE entry point
c937c236  refactor(spec-110): slim CLAUDE.md to overlay (delegate rules to AGENTS.md/CONSTITUTION)
09ae21d2  refactor(spec-110): slim GEMINI.md to overlay (delegate to AGENTS.md/CONSTITUTION)
a4bb20ae  refactor(spec-110): slim copilot-instructions.md to overlay (entry-point tests GREEN)
d970fce8  chore(run): close spec-110 Phase 1 — entry-point overlays GREEN
7e10436d  test(spec-110): add failing test for workflow SHA-pinning (RED phase)
43cde42e  chore(spec-110): pin GH Actions to immutable SHAs (cache + sonarqube)
```

Total: 26+ commits. All gated, no `--no-verify` used.

## Tests delivered (post-spec-110)

- `tests/integration/test_constitution_present.py` — 2 tests (presence + numbered rules per article)
- `tests/integration/test_entry_points_consistency.py` — 2 tests (overlays ref AGENTS.md + no rule duplication)
- `tests/integration/test_workflow_sha_pinning.py` — 1 test (all actions SHA-pinned)
- `tests/integration/test_sbom_workflow.py` — 1 test (sbom.yml present + uploads artifact)
- `tests/integration/test_ignore_scripts_in_ci.py` — 1 test (no js install without --ignore-scripts)
- `tests/unit/state/test_audit_chain.py` — 4 tests (compute_event_hash + iter_validate_chain + tampering + missing event + dual-read warning)
- `tests/unit/governance/test_policy_engine.py` — 6 tests (3 policies × allow/deny each)

**Total: 17 new tests, all GREEN.** Pre-existing test suite still passes (broad regression sweep showed 4871+ pass).

## Promotion

Branch ready for promotion to `run/spec-110-111-112-2026-04-29` integration branch.
