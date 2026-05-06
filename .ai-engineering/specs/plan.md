# Plan: spec-124 Post-Install UX + Doctor Provisioning + Security Visibility

## Pipeline: full
## Phases: 6
## Tasks: 38 (build: 27, verify: 8, guard: 3)

## Architecture

Modular Monolith + CQRS+Outbox + Sidecar (same as spec-123). Targeted polish across existing modules; no new architectural pattern.

## Design

No UI work beyond CLI rendering polish (D-124-03/04/05/06). `.ai-engineering/contexts/cli-ux.md` color semantics.

---

### Phase 1 — Wave 1: IDE rename + install UX bugs (D-124-01,02,04,05,06)

**Gate**: pytest installer tests green; ai-eng install on test project shows: NO "What's new" banner, NO truncated header, NO duplicated [N/M], hooks count > 0, blank line before Install Complete; manifest read shim translates old keys.

- [x] T-1.1: Pre-rename grep — inventory `claude_code`, `"gemini"`, `github_copilot`, `"copilot"` references repo-wide (agent: verify)
- [x] T-1.2: Update `IdeName` Literal type + `detect_ide()` returns in `installer/engram.py` (agent: build)
- [x] T-1.3: Mass rename Python literals: `claude_code → claude-code`, `gemini → gemini-cli`, `github_copilot → github-copilot`, `"copilot" → "github-copilot"` (agent: build)
- [x] T-1.4: Update manifest schema enum + add backwards-compat read shim with WARN log (agent: build)
- [x] T-1.5: Update CLI flags + help text (Click/Typer in cli_commands/) (agent: build)
- [x] T-1.6: Update `.ai-engineering/manifest.yml` + template manifest values (agent: build)
- [x] T-1.7: Update tests (mass rename in tests/) (agent: build)
- [x] T-1.8: Update README + CLAUDE.md + AGENTS.md + GEMINI.md + CHANGELOG one-line (agent: build)
- [x] T-1.9: Remove "What's new" banner (D-124-02) — delete `_BREAKING_BANNER` + function + call site (agent: build)
- [x] T-1.10: Drop `breaking_banner_seen` field from `InstallState` (agent: build)
- [x] T-1.11: Fix tool header truncation (D-124-04) — shorten helper text (agent: build)
- [x] T-1.12: Fix `[N/M] [N/M]` duplication — trace `core.py:604` phase callback (agent: build)
- [x] T-1.13: Fix hooks count always 0 (D-124-05) — populate `result.hooks.installed` (agent: build)
- [x] T-1.14: Add spacing before Install Complete panel (D-124-06) (agent: build)
- [x] T-1.15: Phase 1 verification — pytest installer + manual ai-eng install dry-run (agent: verify)

---

### Phase 2 — Wave 2: Per-tool progress UX (D-124-03)

**Gate**: tool installer phase + git-hooks phase emit per-tool events visible in CLI; throttled to 100ms.

- [x] T-2.1: TDD-RED — failing test for per-tool progress callbacks in installer phase (agent: build)
- [x] T-2.2: TDD-GREEN — implement `tool_started/tool_finished` event emission in tool installer phase (agent: build)
- [x] T-2.3: Same for git-hooks phase (agent: build)
- [x] T-2.4: UI layer renders Rich Status spinner with current tool name; 100ms throttle (agent: build)
- [x] T-2.5: Phase 2 verification — manual ai-eng install on test project; visual confirm progress visible (agent: verify)

---

### Phase 3 — Wave 3: Doctor provisioning + OPA per-install + keys cleanup (D-124-07,08,11)

**Gate**: fresh `ai-eng install` followed by `ai-eng doctor` returns 0 warnings for ownership-coverage + opa-bundle-load + opa-bundle-signature. Bundle + signature + private key all present at expected paths.

- [x] T-3.1: Seed default ownership map at install time (D-124-07) — invoke `default_ownership_map()` in state install phase (agent: build)
- [x] T-3.2: New `src/ai_engineering/installer/opa.py` — keygen + build + sign helpers (agent: build)
- [x] T-3.3: Add `.rego` policies + `.manifest` to install template `src/ai_engineering/templates/.ai-engineering/policies/` (agent: build)
- [x] T-3.4: Wire OPA bundle generation into governance install phase (D-124-08) (agent: build)
- [ ] T-3.5: Add `--rotate-opa-keys` flag to `ai-eng install` for keypair regeneration (agent: build)
- [ ] T-3.6: Trace + identify origin of `keys/opa-bundle-signing-dev.pub.pem` (D-124-11) (agent: verify)
- [x] T-3.7: Clean up source repo keys/ artifact (delete or document install-output-only path) (agent: build)
- [ ] T-3.8: Tests for opa.py (mock subprocess) (agent: build)
- [x] T-3.9: Phase 3 verification — fresh install + doctor 0 warnings (agent: verify)

---

### Phase 4 — Wave 4: Secrets-gate visibility + docs (D-124-09,10,13)

**Gate**: ai-eng doctor surfaces secrets-gate probe; CONSTITUTION + README documents gate; semgrep-update-model.md present.

- [ ] T-4.1: New `src/ai_engineering/doctor/runtime/secrets_gate.py` probe (D-124-09) — 7 checks (agent: build)
- [ ] T-4.2: Register secrets_gate in doctor runtime modules list (agent: build)
- [ ] T-4.3: Tests for secrets_gate probe (agent: build)
- [ ] T-4.4: CONSTITUTION.md documentation block on secrets-gate (D-124-10) (agent: build)
- [ ] T-4.5: README.md install section secrets-gate paragraph (agent: build)
- [ ] T-4.6: New `.ai-engineering/contexts/semgrep-update-model.md` (D-124-13) (agent: build)
- [ ] T-4.7: Phase 4 verification — doctor shows secrets-gate; CONSTITUTION links to context doc (agent: verify)

---

### Phase 5 — Wave 5: state/ JSON cleanup + canonical guard (D-124-12)

**Gate**: state/ contains only canonical entries; CI guard test passes; consumers read from state.db.

- [ ] T-5.1: Pre-deletion grep — find all consumers of the 5 JSON files (agent: verify)
- [ ] T-5.2: Migrate any laggard consumers to state.db.read_* helpers (agent: build)
- [ ] T-5.3: Delete 5 JSON files (agent: build)
- [ ] T-5.4: Add startup migration assertion (warn if file present + suggest ai-eng audit migrate-fallback) (agent: build)
- [ ] T-5.5: New `tests/unit/specs/test_state_canonical.py` CI guard (agent: build)
- [ ] T-5.6: Phase 5 verification — state/ correct, CI guard passes (agent: verify)

---

### Phase 6 — Wave 6: Quality convergence + PR

**Gate**: all green; ready for PR update.

- [ ] T-6.1: Full unit test suite (agent: verify)
- [ ] T-6.2: Integration tests (agent: verify)
- [ ] T-6.3: ruff format + lint baseline preserved (agent: verify)
- [ ] T-6.4: gitleaks (agent: verify)
- [ ] T-6.5: Hot-path SLO (agent: verify)
- [ ] T-6.6: ai-eng spec verify --all + ai-eng doctor (agent: verify)
- [ ] T-6.7: governance pre-pr review (agent: guard)
- [ ] T-6.8: spec compliance pre-pr (agent: guard)
- [ ] T-6.9: Update PR #505 with spec-124 commits OR open new PR (agent: guard)

---

## Counts breakdown

| Phase | Tasks | build | verify | guard |
|-------|-------|-------|--------|-------|
| 1 IDE rename + UX bugs | 15 | 13 | 2 | 0 |
| 2 Per-tool progress | 5 | 4 | 1 | 0 |
| 3 Doctor + OPA per-install | 9 | 6 | 3 | 0 |
| 4 Secrets-gate + docs | 7 | 6 | 1 | 0 |
| 5 state/ cleanup | 6 | 4 | 2 | 0 |
| 6 Quality convergence | 9 | 0 | 6 | 3 |
| **Total** | **51** | **33** | **15** | **3** |

(Updated: 51 tasks vs initial 38 estimate — Phase 1 expanded with explicit IDE rename steps.)

## Critical path

```
Phase 1 (IDE rename + UX bugs)
        |
   Phase 2 (per-tool progress)
        |
Phase 3 (doctor provisioning + OPA per-install)
        |
   Phase 4 (secrets-gate visibility + docs)
        |
   Phase 5 (state/ JSON cleanup)
        |
   Phase 6 (quality + PR)
```

Phase 1 + 2 chain because both touch installer UX surface. Phase 3..5 could parallelize but small enough to serialize for clean review.

## Recommended execution path

Same as spec-123: `/ai-autopilot` with per-task verification gates in agent prompts. Smaller waves than spec-122/123. Phase 6 = PR delivery (update PR #505 since same branch, or new PR if branch policy demands).

## STOP — Hard gate

`/ai-plan` is planning-only. Implementation runs via `/ai-autopilot` or `/ai-dispatch`.
