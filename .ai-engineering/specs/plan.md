# Plan: spec-107 MCP Sentinel Hardening + IDE Parity + Hash-Chained Audit Trail

**Spec ref**: `.ai-engineering/specs/spec.md` (status: approved, 2026-04-28)
**Effort**: large
**Pipeline**: full (build + verify; verify+review en Phase 6)
**Phases**: 6
**Tasks**: ~80 (build: ~67, verify: ~13)
**Branch**: `feat/spec-101-installer-robustness` (umbrella; renamed at PR creation)
**TDD pattern**: cada commit bundla GREEN code (current phase) + RED tests (next phase) marked `@pytest.mark.spec_107_red`. CI runs `pytest -m 'not spec_105_red and not spec_106_red and not spec_107_red'` → green throughout. Phase 6 verifica zero markers residuales.

---

### Phase 1: MCP binary allowlist + escape hatch + Phase 2 RED
**Gate**: `_ALLOWED_MCP_BINARIES` constant in `mcp-health.py`; risk-accept lookup wired; CI green.

- [x] T-1.1: Add `pytest.mark.spec_107_red` marker to `[tool.pytest.ini_options].markers` in `pyproject.toml` (agent: build)
- [x] T-1.2: Add `_ALLOWED_MCP_BINARIES = frozenset({"npx","node","python3","bunx","deno","cargo","go","dotnet"})` constant to `.ai-engineering/scripts/hooks/mcp-health.py` (agent: build)
- [x] T-1.3: Refactor `mcp-health.py` env-var resolution to validate `parts[0] in _ALLOWED_MCP_BINARIES`; on miss, lookup `find_active_risk_acceptance(finding_id=f"mcp-binary-{parts[0]}")` from decision-store (reuse spec-105 D-105-07) (agent: build)
- [x] T-1.4: Update template `src/ai_engineering/templates/.ai-engineering/scripts/hooks/mcp-health.py` byte-equivalent (agent: build)
- [x] T-1.5: Create `.ai-engineering/contexts/mcp-binary-policy.md` documenting canonical 8 binaries + extension via DEC (agent: build)
- [x] T-1.6: Write `tests/integration/test_mcp_binary_allowlist.py` (no marker, immediate GREEN) — 8 allowed PASS, 5 malicious DENIED (agent: build)
- [x] T-1.7: Write `tests/integration/test_mcp_binary_risk_accept.py` (no marker, GREEN) — DEC active concedes execution; expired DEC rejects (agent: build)
- [x] T-1.8: Run focused tests; confirm GREEN (agent: verify)
- [x] T-1.9: Write RED skeleton `tests/integration/test_settings_template_narrow.py` marked, covering Phase 2 G-3 (agent: build)
- [x] T-1.10: Write RED skeleton `tests/integration/test_doctor_permissions_advisory.py` marked, covering Phase 2 G-4 (agent: build)
- [x] T-1.11: Run `pytest -m 'not spec_105_red and not spec_106_red and not spec_107_red'` confirm PASS (agent: verify)
- [x] T-1.12: Stage and commit `feat(spec-107): Phase 1 GREEN MCP allowlist + Phase 2 RED tests` (agent: build)

---

### Phase 2: settings.json narrow template + doctor advisory + Phase 3 RED
**Gate**: template ships narrow; doctor advisory check `permissions-wildcard-detected`; cero existing file mutated; T-1.9/T-1.10 unmarked GREEN.

- [x] T-2.1: Update `src/ai_engineering/templates/.claude/settings.json` `allow:` from `["*"]` to explicit list (Read, Write, Edit, MultiEdit, Bash, Agent, Glob, Grep, Skill, TaskCreate, TaskUpdate, mcp__context7__*, mcp__notebooklm-mcp__*) (agent: build)
- [x] T-2.2: Verify other IDE settings templates (`.github/`, `.codex/`, `.gemini/`) remain consistent or N/A; update if Copilot equivalents exist (agent: build)
- [x] T-2.3: Add `permissions-wildcard-detected` check to `src/ai_engineering/doctor/` (find appropriate module) — reads `.claude/settings.json`, regex `["*"]` in allow → emit advisory WARN (agent: build)
- [x] T-2.4: Create `.ai-engineering/contexts/permissions-migration.md` con migration guide + canonical narrow list + extension example (agent: build)
- [x] T-2.5: Write `tests/unit/test_settings_template_narrow.py` body — assert template lacks `["*"]`, has explicit narrow list (agent: build)
- [x] T-2.6: Write `tests/integration/test_doctor_permissions_advisory.py` body — fixture project con `["*"]` in settings; assert doctor emits WARN advisory; another fixture con narrow list assert no advisory (agent: build)
- [x] T-2.7: Remove markers from these 2 test files; confirm GREEN (agent: build)
- [x] T-2.8: Write RED skeleton `tests/integration/test_copilot_explorer_rename.py` marked, covering Phase 3 G-5 (agent: build)
- [x] T-2.9: Write RED skeleton `tests/unit/test_gemini_md_placeholders.py` marked, covering Phase 3 G-6 (agent: build)
- [x] T-2.10: Write RED skeleton `tests/integration/test_platform_audit_new_checks.py` marked, covering Phase 3 G-7 (agent: build)
- [x] T-2.11: Run pytest filter; confirm PASS (agent: verify)
- [x] T-2.12: Stage and commit `feat(spec-107): Phase 2 GREEN narrow template + doctor advisory + Phase 3 RED tests` (agent: build)

---

### Phase 3: Explorer rename + GEMINI.md placeholders + platform-audit checks 6/7/8 + Phase 4 RED
**Gate**: `.github/agents/ai-explore.agent.md` exists with `name: ai-explore`; chatmode alias works; GEMINI.md placeholders rendered; 3 platform-audit checks operational; T-2.8/T-2.9/T-2.10 GREEN.

- [x] T-3.1: Rename `.github/agents/explore.agent.md` → `.github/agents/ai-explore.agent.md`; update front-matter `name: ai-explore` (agent: build)
- [x] T-3.2: Update `scripts/sync_command_mirrors.py` `AGENT_METADATA["explore"]["name"]` from "Explorer" to "ai-explore" (agent: build)
- [x] T-3.3: Create `.github/chatmodes/ai-explore.chatmode.md` con front-matter handler agent:ai-explore (agent: build)
- [x] T-3.4: Update `src/ai_engineering/templates/project/GEMINI.md` line 110: `## Skills (44)` → `## Skills (__SKILL_COUNT__)`; if agent count header exists similar treatment (agent: build)
- [x] T-3.5: Add `write_gemini_md(canonical_skills, canonical_agents)` function to `scripts/sync_command_mirrors.py`; wire into main sync flow (agent: build)
- [x] T-3.6: Update `.claude/skills/ai-platform-audit/SKILL.md` — add Check 6 (agent naming consistency cross-IDE), Check 7 (GEMINI.md skill count freshness), Check 8 (generic instruction-file count scan) (agent: build)
- [x] T-3.7: Run `uv run ai-eng sync` to regenerate mirrors with renamed agent + updated GEMINI.md + updated platform-audit (agent: build)
- [x] T-3.8: Run `uv run ai-eng sync --check` exit 0 (agent: verify)
- [x] T-3.9: Update CHANGELOG with `BREAKING-LIKELY: Copilot agent renamed Explorer → ai-explore` entry (agent: build)
- [x] T-3.10: Write `tests/integration/test_copilot_explorer_rename.py` body — assert `name: ai-explore` in agent file, chatmode exists, mirror parity preserved (agent: build)
- [x] T-3.11: Write `tests/unit/test_gemini_md_placeholders.py` body — load template, assert `__SKILL_COUNT__` and `__AGENT_COUNT__` placeholders present; load generated `.gemini/GEMINI.md`, assert canonical numeric counts substituted (agent: build)
- [x] T-3.12: Write `tests/integration/test_platform_audit_new_checks.py` body — fixture projects con drifts intentionales (renamed agent name mismatch slug, GEMINI.md count stale, CLAUDE.md count stale); assert each new check flags correctly (agent: build)
- [x] T-3.13: Remove markers from these 3 test files; confirm GREEN (agent: build)
- [x] T-3.14: Write RED skeleton `tests/integration/test_sentinel_runtime_iocs.py` marked, covering Phase 4 G-8 (agent: build)
- [x] T-3.15: Write RED skeleton `tests/integration/test_sentinel_risk_accept.py` marked, covering Phase 4 G-9 (agent: build)
- [x] T-3.16: Run pytest filter; confirm PASS (agent: verify)
- [x] T-3.17: Stage and commit `feat(spec-107): Phase 3 GREEN Explorer rename + GEMINI placeholders + platform-audit + Phase 4 RED tests` (agent: build)

---

### Phase 4: IOC catalog vendored + prompt-injection-guard extension + sentinel risk-accept + Phase 5 RED
**Gate**: `.ai-engineering/references/iocs.json` exists vendored; prompt-injection-guard.py loads + matches IOCs; risk-accept escape works; T-3.14/T-3.15 GREEN.

- [x] T-4.1: Vendor IOCs from `claude-mcp-sentinel/references/iocs.json` to `.ai-engineering/references/iocs.json`; preserve schema verbatim (agent: build)
- [x] T-4.2: Create `.ai-engineering/references/IOCS_ATTRIBUTION.md` with source URL, vendor commit hash, vendor date, license terms (agent: build)
- [x] T-4.3: Create `.ai-engineering/contexts/sentinel-iocs-update.md` documenting refresh cadence (quarterly manual PR) (agent: build)
- [x] T-4.4: Extend `.ai-engineering/scripts/hooks/prompt-injection-guard.py` con `load_iocs()` function (fallback empty if missing — fail-open) (agent: build)
- [x] T-4.5: Add IOC matching logic to `prompt-injection-guard.py` for 4 categories: sensitive_paths, sensitive_env_vars, malicious_domains, shell_patterns (agent: build)
- [x] T-4.6: Implement 3-valued decision: deny (no DEC), warn (DEC active), allow (no match) (agent: build)
- [x] T-4.7: Wire risk-accept lookup: compute canonical `finding_id = f"sentinel-{category}-{pattern_normalized}"`; query decision-store; warn if active (agent: build)
- [x] T-4.8: Update template `src/ai_engineering/templates/.ai-engineering/scripts/hooks/prompt-injection-guard.py` byte-equivalent (agent: build)
- [x] T-4.9: Update template `src/ai_engineering/templates/.ai-engineering/references/iocs.json` (copy from vendored) (agent: build)
- [x] T-4.10: Write `tests/integration/test_sentinel_runtime_iocs.py` body — 25+ fixtures: 8 sensitive paths blocked, 8 env vars blocked, 5 domains blocked, 4 shell patterns blocked (agent: build)
- [x] T-4.11: Write `tests/integration/test_sentinel_risk_accept.py` body — fixture: IOC match + DEC active for that finding-id → result is `warn` not `deny` (agent: build)
- [x] T-4.12: Remove markers from these 2 test files; confirm GREEN (agent: build)
- [x] T-4.13: Write RED skeleton `tests/integration/test_mcp_sentinel_skill_modes.py` marked, covering Phase 5 G-10 (3 modes: scan, audit-update, baseline) (agent: build)
- [x] T-4.14: Write RED skeleton `tests/integration/test_h1_rugpull_detection.py` marked, covering Phase 5 G-11 (agent: build)
- [x] T-4.15: Run pytest filter; confirm PASS (agent: verify)
- [x] T-4.16: Stage and commit `feat(spec-107): Phase 4 GREEN IOC catalog + sentinel runtime + Phase 5 RED tests` (agent: build)

---

### Phase 5: /ai-mcp-sentinel skill 3 modes + H1 tool-spec hash + Phase 6 RED
**Gate**: skill exists with 3 modes propagated to 4 IDEs; H1 hash mismatch detection works with risk-accept escape; T-4.13/T-4.14 GREEN.

- [ ] T-5.1: Create `.claude/skills/ai-mcp-sentinel/SKILL.md` con front-matter (name, description, effort: high) + 3 modes documented + triggering patterns (agent: build)
- [ ] T-5.2: Document Mode 1 `scan` — LLM coherence analysis pattern, output VERDE/ROJO verdicts (agent: build)
- [ ] T-5.3: Document Mode 2 `audit-update <skill>` — diff baseline vs current, rug-pull pattern detection (agent: build)
- [ ] T-5.4: Document Mode 3 `baseline set [--target <skill-or-all>]` — snapshot to `.ai-engineering/state/sentinel-baseline.json` (agent: build)
- [ ] T-5.5: Run `uv run ai-eng sync` to regenerate skill mirrors to `.github/`, `.codex/`, `.gemini/` (agent: build)
- [ ] T-5.6: Run `uv run ai-eng sync --check` exit 0 (agent: verify)
- [ ] T-5.7: Add `compute_tool_spec_hash(spec)` to `src/ai_engineering/state/manifest.py`; SHA256 of canonical-JSON spec entry (agent: build)
- [ ] T-5.8: Add `tool_spec_hashes: dict[str, str] = Field(default_factory=dict)` field to `InstallState` model (`state/models.py`) (agent: build)
- [ ] T-5.9: Wire H1 detection into `src/ai_engineering/installer/service.py`: compute current hash per tool; compare vs baseline; mismatch → CLI banner + DEC lookup (agent: build)
- [ ] T-5.10: Add CLI banner template (`Tool Spec Mismatch: ...; To accept: ai-eng risk accept ...`) to installer flow (agent: build)
- [ ] T-5.11: First-run handling: empty baseline → populate, no alert (agent: build)
- [ ] T-5.12: Write `tests/integration/test_mcp_sentinel_skill_modes.py` body — assert SKILL.md exists in all 4 IDE locations, frontmatter valid, all 3 modes documented (agent: build)
- [ ] T-5.13: Write `tests/integration/test_h1_rugpull_detection.py` body — fixture project: install, mutate manifest tool spec, re-install → assert mismatch detected; assert DEC active permits + updates baseline (agent: build)
- [ ] T-5.14: Remove markers from these 2 test files; confirm GREEN (agent: build)
- [ ] T-5.15: Write RED skeleton `tests/unit/test_audit_chain_verify.py` marked, covering Phase 6 G-12 (agent: build)
- [ ] T-5.16: Run pytest filter; confirm PASS (agent: verify)
- [ ] T-5.17: Stage and commit `feat(spec-107): Phase 5 GREEN /ai-mcp-sentinel + H1 + Phase 6 RED tests` (agent: build)

---

### Phase 6: H2 audit chain + verify+review convergence + history
**Gate**: `state/audit_chain.py` exists with `verify_audit_chain()`; `prev_event_hash` field added to events + decisions; doctor checks added; `ai-eng audit verify` CLI; T-5.15 GREEN; spec-107 declared COMPLETE.

- [ ] T-6.1: Create `src/ai_engineering/state/audit_chain.py` with `verify_audit_chain(file_path) → AuditChainVerdict` dataclass + walk logic (agent: build)
- [ ] T-6.2: Add `prev_event_hash: str | None = Field(default=None, alias="prevEventHash")` to event emission in `state/observability.py` (agent: build)
- [ ] T-6.3: Add `prev_event_hash: str | None` field to `Decision` model (`state/models.py`) — additive backward-compat (agent: build)
- [ ] T-6.4: Wire chain compute into `emit_control_outcome()` and `decision_logic.create_risk_acceptance()` (read prior entry, compute hash, set field) (agent: build)
- [ ] T-6.5: Add `audit-chain-events` and `audit-chain-decisions` checks to `ai-eng doctor` (WARN only, no FAIL) (agent: build)
- [ ] T-6.6: Add `ai-eng audit verify [--file events|decisions|all]` CLI subcommand (agent: build)
- [ ] T-6.7: Update `cli_factory.py` to register `audit` sub-Typer app (agent: build)
- [ ] T-6.8: Write `tests/unit/test_audit_chain_verify.py` body — 12+ fixtures: valid chain, mid-chain tampering (mismatch), truncation (shorter than expected), append injection (prev_hash points to wrong entry), legacy entries without field (agent: build)
- [ ] T-6.9: Remove marker from this test file; confirm GREEN (agent: build)
- [ ] T-6.10: Run `pytest -m 'spec_107_red' --collect-only` and confirm zero residual (agent: verify)
- [ ] T-6.11: Run `pytest -m 'not spec_105_red and not spec_106_red and not spec_107_red' --no-cov -q` full suite; confirm pre-existing failures only (agent: verify)
- [ ] T-6.12: Run `uv run ai-eng validate` confirm exit 0 (agent: verify)
- [ ] T-6.13: Run `uv run ai-eng sync --check` confirm exit 0 (agent: verify)
- [ ] T-6.14: Run `uv run gitleaks protect --staged --no-banner` + `uv run pip-audit` confirm no spec-107 findings introduced (agent: verify)
- [ ] T-6.15: Run `uv run ruff check` + `uv run ruff format --check` confirm clean (agent: verify)
- [ ] T-6.16: Update `.ai-engineering/specs/_history.md` with spec-107 phase summary (commit SHAs + metrics + lessons) (agent: build)
- [ ] T-6.17: Stage and commit `feat(spec-107): Phase 6 GREEN H2 audit chain + verify+review convergence + history` (agent: build)

---

## Dependencies (cross-phase)

- Phase 1 → Phase 2: MCP allowlist pattern established before settings.json narrow.
- Phase 2 → Phase 3: doctor advisory pattern in place before platform-audit checks (similar mechanism).
- Phase 3 → Phase 4: mirrors regenerated post-Explorer rename before IOCs vendored (avoid sync conflict).
- Phase 4 → Phase 5: prompt-injection-guard IOC layer in place before sentinel skill references its hot-path counterpart.
- Phase 5 → Phase 6: H1 tool-spec-hash baseline established before H2 chain (chain validator can include hash mutations).

## What this plan does NOT do

- No migración automática de existing `.claude/settings.json` (NG-1).
- No deprecation banners para `@Explorer` (NG-2).
- No graduated H1 escalation — solo warn + risk-accept (NG-3).
- No H2 chain en install-state.json (NG-4).
- No M1/M2/M3/M4 from NotebookLM — defer (NG-5/6/7/8).
- No IOC schema redesign (NG-9).
- No automated IOC update mechanism (NG-10).
- No platform-audit checks 6/7/8 enforcement como hard-gate (NG-11; advisory only).
- No PR creation in this spec (NG-12).
