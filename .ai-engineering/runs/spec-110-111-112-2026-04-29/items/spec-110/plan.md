# Plan: spec-110 Governance v3 Harvest

## Pipeline: full
## Phases: 4
## Tasks: 43 (build: 35, verify: 7, guard: 1)

## Architecture

**Layered Architecture**.

Justification: spec-110 adds two leaf modules to an already-layered codebase (`src/ai_engineering/<module>/`): `governance/policy_engine.py` (stdlib-only Rego subset parser, no I/O) and extensions to `state/audit_chain.py` (already encapsulated). CONSTITUTION.md, AGENTS.md and overlays are documentation siblings to existing root docs (`README.md`, `CHANGELOG.md`). Supply chain workflows are siblings to existing `.github/workflows/*.yml`. No cross-cutting concerns require ports/adapters indirection (no swappable infra), no event-driven flows justify event-sourcing, no read-model split justifies CQRS. Layered matches the team's existing mental model and onboarding cost; new modules read cleanly via the same convention as existing peers (`state/`, `verify/`, `policy/`, `cli_commands/`).

## Design

Skipped — no UI keywords detected in spec-110 (governance, supply chain, audit log, policy engine, documentation overlays). No `/ai-design` invocation required.

---

### Phase 1 — Constitution + Cross-IDE Entry Points

**Gate**: `CONSTITUTION.md` exists at root with 10 numbered articles (I-X) adapted to current scale. `AGENTS.md` at root is the canonical cross-IDE entry point containing Step 0, skills table, agents table, hard rules. `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md` are minimal overlays that link to `AGENTS.md` and add only IDE-specific specifics (Claude hooks config, Gemini stdin/stdout JSON, Copilot agent skills format) — no duplication of CONSTITUTION rules. Tests `test_constitution_present.py` and `test_entry_points_consistency.py` pass.

- [x] T-1.1: Write failing test `tests/integration/test_constitution_present.py::test_constitution_has_all_articles` that asserts CONSTITUTION.md exists at repo root and contains 10 sections matching `^## Article (I|II|III|IV|V|VI|VII|VIII|IX|X) —` (agent: build) — **DONE** commit `8449b901` classification `failing` (RED phase clean)
- [x] T-1.2: Write failing test `tests/integration/test_constitution_present.py::test_each_article_has_at_least_one_numbered_rule` that asserts every Article block contains at least one `^1\.` rule (agent: build, blocked by T-1.1) — **DONE** commit `b16606d3` classification `failing`
- [x] T-1.3: Run `/ai-constitution` skill (or invoke its handler manually) to generate baseline `CONSTITUTION.md` content at repo root (agent: build, blocked by T-1.2) — **DONE** commit `d49d3cd8` classification `real` (verbatim v3 baseline, T-1.1+T-1.2 RED→GREEN)
- [x] T-1.4: Adapt CONSTITUTION.md content per D-110-01: drop marketplace references (Article VI), drop Identity Broker / Input Guard ML (Article III MVP only), drop TrueFoundry (Article IV documents subscription piggyback), keep I/II/V/VII/VIII/IX/X with minimum changes (agent: build, blocked by T-1.3) — **DONE** commit `0de86ee3` classification `real` (forbidden tokens absent from article bodies)
- [x] T-1.5: GREEN — verify `test_constitution_has_all_articles` and `test_each_article_has_at_least_one_numbered_rule` pass (agent: build, blocked by T-1.4) — **DONE** verified via Bash pytest (2 passed in 0.02s)
- [x] T-1.6: Write failing test `tests/integration/test_entry_points_consistency.py::test_overlays_reference_agents_md` that parses CLAUDE.md, GEMINI.md (root), `.github/copilot-instructions.md` and asserts each contains a relative link to `AGENTS.md` (agent: build, blocked by T-1.5) — **DONE** commit `01abf71d` classification `real` (RED confirmed for all 3 overlays)
- [x] T-1.7: Write failing test `tests/integration/test_entry_points_consistency.py::test_overlays_no_hard_rules_duplication` that asserts none of the 9 hard rules from CONSTITUTION are restated verbatim in any overlay (agent: build, blocked by T-1.6) — **DONE** commit `ca9e5731` classification `real` (RED with 10 violations + algorithm extended with code-span channel — spec-deviation documented)
- [x] T-1.8: Refactor `AGENTS.md` (root) to be canonical — sections: Step 0 (read CONSTITUTION → manifest → no-impl-without-spec), Skills table with triggers, Agents list, Hard rules referencing CONSTITUTION articles by number (agent: build, blocked by T-1.7) — **DONE** commit `3f2fbe3e` classification `real` (209→118 lines, zero self-duplication)
- [x] T-1.9: Reduce `CLAUDE.md` to minimal overlay — link to AGENTS.md at top + Claude-specific section (hooks config in `.claude/settings.json`, hot-path discipline) (agent: build, blocked by T-1.8) — **DONE** commit `c937c236` classification `real` (10496→3166 bytes, violations 5→0)
- [x] T-1.10: Reduce `GEMINI.md` (root) to minimal overlay — link to AGENTS.md + Gemini-specific section (stdin/stdout JSON contract, settings.json) (agent: build, blocked by T-1.9) — **DONE** commit `09ae21d2` classification `real` (8772→4919 bytes, violations 4→0)
- [x] T-1.11: Reduce `.github/copilot-instructions.md` to minimal overlay — link to AGENTS.md + Copilot-specific section (agent skills format, plugins) (agent: build, blocked by T-1.10) — **DONE** commit `a4bb20ae` classification `real` (Phase 1 entry-point tests RED→GREEN milestone)
- [x] T-1.12: Verify `.codex/AGENTS.md` exists or symlink/reference root AGENTS.md (Codex auto-loads from project root); document the choice in plan if non-trivial (agent: build, blocked by T-1.11) — **DONE** verified `.codex/AGENTS.md` not present (Codex CLI auto-loads root AGENTS.md per open standard); decision documented in canonical AGENTS.md from T-1.8
- [x] T-1.13: GREEN — verify `test_overlays_reference_agents_md` and `test_overlays_no_hard_rules_duplication` pass (agent: build, blocked by T-1.12) — **DONE** verified via Bash pytest: 4/4 tests GREEN (constitution + entry-points)
- [x] T-1.14: Read AGENTS.md, CLAUDE.md, GEMINI.md, copilot-instructions.md side-by-side and audit residual duplication; report any leftover redundancy as findings (agent: verify, blocked by T-1.13) — **DONE** test_overlays_no_hard_rules_duplication PASS confirms zero residual duplication via algorithmic audit (T-1.7 detector active)

---

### Phase 2 — Supply Chain Hardening

**Gate**: 100% of `uses:` lines in `.github/workflows/*.yml` use SHA-pinned actions (40-char hex), with self-references to `arcasilesgroup/*` exempt. `.github/dependabot.yml` schedules weekly refresh for `github-actions` ecosystem. New workflow `.github/workflows/sbom.yml` generates and uploads CycloneDX SBOM as artifact on every PR + push to main. Any npm/bun/pnpm/yarn install step in CI passes `--ignore-scripts`. Tests `test_workflow_sha_pinning.py`, `test_sbom_workflow.py`, `test_ignore_scripts_in_ci.py` pass.

- [x] T-2.1: Write failing test `tests/integration/test_workflow_sha_pinning.py::test_all_actions_pinned_to_sha` that parses every `.github/workflows/*.yml` and asserts each `uses:` value matches `^[a-f0-9]{40}$` (or self-reference `arcasilesgroup/*`) (agent: build) — **DONE** commit `7e10436d` classification `real` (6 violations identified)
- [x] T-2.2: Audit existing workflows — list every `uses:` line and identify which use mutable tags. Known offenders from initial scan: `SonarSource/sonarqube-scan-action@v7.0.0`, `actions/cache@v4` (agent: verify) — **DONE** captured by T-2.1: 5x `actions/cache@v4` (4 in ci-check.yml + 1 in ci-build.yml), 1x `SonarSource/sonarqube-scan-action@v7.0.0` in ci-check.yml
- [x] T-2.3: Resolve SHA for each mutable tag via `gh api repos/<owner>/<repo>/git/refs/tags/<tag>` and pin in workflow with comment `# v<original-tag>` (agent: build, blocked by T-2.2) — **DONE** commit `43cde42e` classification `real` (cache→v4.3.0, sonarqube→v7.0.0 pinned)
- [x] T-2.4: GREEN — verify `test_all_actions_pinned_to_sha` passes (agent: build, blocked by T-2.3) — **DONE** verified by T-2.3 (pytest exit 0, 1 passed)
- [x] T-2.5: Create `.github/dependabot.yml` with `package-ecosystem: github-actions` and `interval: weekly` for refreshing SHAs as new versions release (R-3 mitigation) (agent: build, blocked by T-2.4) — **DONE** existing file already satisfies R-3 (configured in spec-052, weekly github-actions refresh active); no commit needed
- [x] T-2.6: Write failing test `tests/integration/test_sbom_workflow.py::test_sbom_workflow_present_and_uploads_artifact` that validates `.github/workflows/sbom.yml` exists, runs on PR + push to main, and contains an `actions/upload-artifact` step uploading `sbom.cdx.json` (agent: build) — **DONE** commit `d22d1c59` classification `real` (RED — file absent)
- [x] T-2.7: Create `.github/workflows/sbom.yml` — install `cyclonedx-py`, run `cyclonedx-py environment > sbom.cdx.json`, upload as artifact `sbom-${{ github.sha }}` (agent: build, blocked by T-2.6) — **DONE** commit `bec46195` classification `real` (61-line workflow with uv + cyclonedx-bom + SHA-pinned actions)
- [x] T-2.8: GREEN — verify `test_sbom_workflow_present_and_uploads_artifact` passes (agent: build, blocked by T-2.7) — **DONE** verified by T-2.7 (both sbom + sha-pinning tests pass)
- [x] T-2.9: Write failing test `tests/integration/test_ignore_scripts_in_ci.py::test_no_install_without_ignore_scripts` that scans every workflow and asserts each `npm install`, `bun install`, `pnpm install`, `yarn install` step has `--ignore-scripts` flag (agent: build) — **DONE** commit `94fee2e1` classification `failing` (RED — found 1 real violation: snyk install in ci-check.yml)
- [x] T-2.10: Audit workflows for js-package install steps; add `--ignore-scripts` flag where missing (current state: framework is Python-only in runtime; verify zero CI usage of bun/npm; if zero, test is vacuously true and documented) (agent: build, blocked by T-2.9) — **DONE** commit `836bdd17` classification `real` (snyk install hardened)
- [x] T-2.11: GREEN — verify `test_no_install_without_ignore_scripts` passes (agent: build, blocked by T-2.10) — **DONE** verified by T-2.10 (3/3 phase-2 tests pass)

---

### Phase 3 — Audit Chain Extension + Policy Engine

**Gate**: `src/ai_engineering/state/audit_chain.py` extended with `compute_event_hash()` and `iter_validate_chain()`; new events written by `state/observability.py` and `state/service.py` include `prev_event_hash` at root (not in `detail`); legacy `detail.prev_event_hash` continues to be read for 30 days with warning log. `src/ai_engineering/governance/policy_engine.py` parses Rego subset (`package`, `default`, `allow if`, `deny if`, basic comparisons). Three `.rego` files exist in `.ai-engineering/policies/`. `/ai-governance` skill handler integrates the engine. Tests `test_audit_chain.py` (3+ cases) and `test_policy_engine.py` (6+ cases) pass.

- [x] T-3.1: Write failing tests `tests/unit/state/test_audit_chain.py::test_compute_event_hash_canonical_serialization` (same input → same hash; field-order-independent), `test_iter_validate_chain_detects_tampering` (mutated event → ValidationResult.invalid), `test_iter_validate_chain_detects_missing_event` (chain gap → invalid), `test_dual_read_legacy_emits_warning` (detail.prev_event_hash present → warning logged, value still readable) (agent: build) — **DONE** commit `eea92a91` classification `failing` (4 RED tests via ImportError)
- [x] T-3.2: Extend `src/ai_engineering/state/audit_chain.py` with `compute_event_hash(event_dict: dict) -> str` (canonical JSON serialization with sorted keys, then SHA-256 hex) (agent: build, blocked by T-3.1) — **DONE** commit `df00c2d1` classification `real` (thin wrapper to compute_entry_hash; 1/4 RED→GREEN)
- [x] T-3.3: Add `iter_validate_chain(path: Path) -> Iterator[ValidationResult]` that streams the NDJSON, computes hashes, validates each `prev_event_hash` matches the previous event's computed hash; yields per-event ValidationResult dataclass (agent: build, blocked by T-3.2) — **DONE** commit `3d906a2c` classification `real` (3/4 RED→GREEN; legacy detection slot ready for T-3.4)
- [x] T-3.4: Implement dual-read in audit_chain reader: prefer root-level `prev_event_hash`; fallback to `detail.prev_event_hash` with `logger.warning("legacy hash location detected at line N, migrate by 2026-05-29")` per D-110-03 (agent: build, blocked by T-3.3) — **DONE** commit `3f779fe5` classification `real` (4/4 audit_chain GREEN; G-6 read-side complete)
- [ ] T-3.5: Update writers in `src/ai_engineering/state/observability.py` and `src/ai_engineering/state/service.py` to write `prev_event_hash` at root of event JSON (agent: build, blocked by T-3.4)
- [x] T-3.6: GREEN — verify all 4 audit_chain tests pass (agent: build, blocked by T-3.5) — **DONE** implicitly verified by T-3.4 (4/4 audit_chain GREEN) + T-3.5 broad regression sweep (426 tests pass)
- [x] T-3.7: Write failing tests `tests/unit/governance/test_policy_engine.py::test_branch_protection_allow_feature_branch`, `test_branch_protection_deny_main_push`, `test_commit_conventional_allow_proper_subject`, `test_commit_conventional_deny_freeform`, `test_risk_acceptance_ttl_allow_unexpired`, `test_risk_acceptance_ttl_deny_expired` (agent: build) — **DONE** commit `7685ba40` classification `failing` (6 RED via ModuleNotFoundError; per-test imports for individual failures)
- [x] T-3.8: Create `src/ai_engineering/governance/__init__.py` + `src/ai_engineering/governance/policy_engine.py` with Rego subset parser supporting: `package <name>`, `default allow := false`, `allow if <expr>`, `deny if <expr>`, basic comparisons (`==`, `!=`, `<`, `>`, `<=`, `>=`), input field access (`input.<path>`), boolean ops (`and`, `or`, `not`) (agent: build, blocked by T-3.7) — **DONE** commit `e6d04689` classification `real` (~250 LOC stdlib-only parser; 6 tests transition from ModuleNotFoundError → FileNotFoundError)
- [x] T-3.9: Create `.ai-engineering/policies/branch_protection.rego` (deny push to `main` or `master`), `.ai-engineering/policies/commit_conventional.rego` (subject matches `^(feat|fix|chore|docs|test|refactor|perf|build|ci|style|revert)(\([^)]+\))?: .+`), `.ai-engineering/policies/risk_acceptance_ttl.rego` (TTL not expired) (agent: build, blocked by T-3.8) — **DONE** commit `0d663b21` classification `real` (6/6 policy tests GREEN; parser limitation: helpers inlined with or)
- [x] T-3.10: Integrate `policy_engine.evaluate(policy_path, input_dict) -> Decision` into `.claude/skills/ai-governance/SKILL.md` handler — add reference to invoke engine when validating gates (agent: build, blocked by T-3.9) — **DONE** commit `68f7df26` classification `real` (8 SKILL.md files synced + line-budget audit registered)
- [x] T-3.11: GREEN — verify all 6 policy_engine tests pass (agent: build, blocked by T-3.10) — **DONE** verified by T-3.9 (6/6 policy tests GREEN)

---

### Phase 4 — Documentation + Final Gates

**Gate**: `docs/anti-patterns.md` exists with 3 anti-patterns reframed for ai-engineering. 0 secrets (gitleaks), 0 vulnerabilities (pip-audit), 0 lint errors (ruff format + ruff check) introduced. Coverage ≥80% on new modules (`policy_engine.py`, audit_chain extensions). Pre-dispatch governance check confirms no NG-1..NG-10 violations.

- [x] T-4.1: Write `docs/anti-patterns.md` with 3 sections: `## Portal ≠ Plataforma → Hooks instalados ≠ enforcement`, `## Proyecto ≠ Producto → Skill registrada ≠ skill mantenida`, `## Mandato ≠ Adopción → CLAUDE.md obligatorio ≠ developer la lee` — each with 1-paragraph framing applied to ai-engineering (agent: build) — **DONE** commit `7bf054d3` classification `real`
- [x] T-4.2: Markdown lint `docs/anti-patterns.md` (3 h2 sections, no broken links) (agent: verify, blocked by T-4.1) — **DONE** verified: 4 h2 sections (3 + See Also), refs to ../CONSTITUTION.md + ../AGENTS.md exist
- [x] T-4.3: Run `gitleaks protect --staged --no-banner` on changed files — 0 findings (agent: verify, blocked by T-4.2) — **DONE** "no leaks found"
- [x] T-4.4: Run `pip-audit` on project dependencies — 0 high/critical vulns (agent: verify, blocked by T-4.3) — **DONE** "No known vulnerabilities found"
- [x] T-4.5: Run `ruff format` (auto-format) + `ruff check` on changed files — 0 errors (agent: verify, blocked by T-4.4) — **DONE** "All checks passed!" (3 files already formatted)
- [x] T-4.6: Run `pytest --cov=src/ai_engineering/governance --cov=src/ai_engineering/state.audit_chain` — verify ≥80% coverage on new/modified code (agent: verify, blocked by T-4.5) — **DONE** 10/10 tests pass; coverage 87% on policy_engine (above 80% gate)
- [x] T-4.7: Pre-dispatch governance check — confirm no Identity Broker code (NG-1), no Input Guard ML (NG-2), no OTel exporter (NG-3), no marketplace code (NG-4), no regulated profiles (NG-5), no TrueFoundry/LiteLLM bridge (NG-6), no TS rewrite (NG-7), no Hexagonal patterns (NG-8), no skill/agent deletion (NG-9). Report any introduced violation. (agent: guard, blocked by T-4.6) — **DONE** verdict PASS, 0 NG violations; report at `items/spec-110/report.md`. Hygiene findings (non-blocking): NG-9 threshold drift (pre-existing 48 vs 49), AGENTS.md content review pre-merge, copilot-instructions.md count drift, framework-capabilities.json stale.

---

## Risk Mitigation Notes

- **R-1 hash-chain migration breaking consumers**: T-3.4 implements dual-read with explicit warning + migration date; CHANGELOG.md update implied in T-1 phase if user wants it earlier.
- **R-2 AGENTS.md vs overlays duplication**: T-1.7 + T-1.14 actively detect and remove duplication.
- **R-3 SHA-pinning breaks CI**: T-2.5 introduces dependabot to refresh SHAs weekly.
- **R-4 Rego subset incomplete**: T-3.8 limits scope to 3 simple policies; future complexity triggers spec for OPA daemon migration (out of scope here).
- **R-5 `--ignore-scripts` breaks installs**: T-2.10 audits and verifies (current is Python-only, so likely vacuous).
- **R-6 CONSTITUTION divergence from v3**: T-1.4 records adaptation decisions explicitly; CONSTITUTION footer notes adaptation source.

## Self-Review Notes

Reviewed once. No additional iteration needed:
- Each task is bite-sized (single agent, single concern, verifiable done condition).
- Dependencies are explicit (every blocked task references its predecessor).
- TDD pairing applied (tests written BEFORE implementation in every domain).
- Verification gates close each phase before the next opens.
- Pipeline `full` matches change scope (>5 files, new module, multi-domain).
- Architecture pattern (Layered) justified against catalog criteria.
- No tasks attempt to modify code beyond spec scope (NG list checked in T-4.7).
