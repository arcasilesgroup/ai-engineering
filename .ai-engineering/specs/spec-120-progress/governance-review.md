# Spec-120 Governance Review

**Generated** 2026 May 04 (UTC, post-Phase-E governance pass) 2026-05-04T03:05:00Z
**Branch**: feat/spec-120-observability-modernization
**Reviewer**: governance-guard agent
**Plan task**: T-E5
**Predecessor evidence**: [acceptance-evidence.md](acceptance-evidence.md)

---

## 1. Constitution Article V - Single Source of Truth

**Article V scope** (CONSTITUTION.md lines 67-75): Skills live ONCE under .claude/skills/ai-NAME/SKILL.md; IDE mirrors are generated, never hand-edited; ai-eng sync-mirrors is the only authorized writer.

**Spec-120 footprint**: new modules under src/ai_engineering/state/, five new Typer subcommands under src/ai_engineering/cli_commands/audit_cmd.py, additive root-field support in event_schema/observability/models, stdlib mirror under .ai-engineering/scripts/hooks/_lib/, runtime-stop session_token_rollup emit, additive optional fields in audit-event.schema.json, regenerated hooks-manifest.json, appended audit observability section in AGENTS.md and CLAUDE.md, plus tests.

**Verdict**: **No conflict.** Spec-120 touches zero files under .claude/skills/. The _lib/observability.py and _lib/trace_context.py mirrors are the existing stdlib-only hook variants (the parity contract codified in T-A4); _lib mirroring is the explicit pattern for hook scripts that must run pre-pip-install - distinct from the IDE-mirror SSOT contract Article V governs.

---

## 2. Audit chain integrity

**Hash algebra** (src/ai_engineering/state/audit_chain.py lines 78-104):

The _strip_chain_field helper returns a copy of entry with ONLY prev_event_hash and its camelCase alias prevEventHash removed (the _CHAIN_FIELD and _CHAIN_FIELD_ALIAS constants). The compute_entry_hash function then takes that stripped dict, json.dumps with sort_keys=True and compact separators, and SHA-256 hashes the UTF-8 encoded canonical bytes.

Because the strip-set is closed (only the chain pointer fields), new root fields traceId / spanId / parentSpanId and the new detail.genai.* block are absorbed into the canonical SHA-256 input naturally. There is no allow-list of fields the hasher knows about - the algebra is open by design.

**Forward-compatibility consequence**:

- Events written **before** spec-120 hash with no trace fields - unchanged.
- Events written **after** spec-120 hash including the new fields - those bytes contribute to the next event prev_event_hash.
- The chain re-anchors naturally at the spec-120 boundary because each event prev_event_hash is computed at write time over the **prior** event actual canonical bytes - there is no retroactive rehash.

This was the explicit risk mitigation in plan-120 Risk hotspots row for compute_entry_hash, and it is verified empirically by the 27 audit-chain tests in tests/unit/test_audit_chain_verify.py and the 4 in tests/unit/state/test_audit_chain.py running green after Phase A schema additions land.

**Verdict**: **Intentional and additive.** Hash chain integrity preserved. Cited code: src/ai_engineering/state/audit_chain.py lines 78-104.

---

## 3. Hook integrity

Verification commands and results:

- python3 .ai-engineering/scripts/regenerate-hooks-manifest.py --check returned: hooks-manifest OK (60 hooks)
- git diff --stat .ai-engineering/state/hooks-manifest.json showed: 1 file changed, 5 insertions, 4 deletions
- pytest tests/unit/hooks/test_hook_integrity.py -v returned: 6 passed in 0.04s

Manifest is regenerated, --check clean, integrity tests green. Manifest mod is staged for commit alongside the hook edits per the discipline laid out in CLAUDE.md Integrity verification section.

**Verdict**: **Confirmed.**

---

## 4. Ownership boundaries

Modified tracked files (13): audit-event.schema.json, _lib/observability.py, runtime-stop.py, hooks-manifest.json, .gitignore, AGENTS.md, CLAUDE.md, audit_cmd.py, cli_factory.py, event_schema.py, models.py, observability.py, test_lib_observability.py.

New untracked files (relevant subset): _lib/trace_context.py, plan-120 + spec-120 docs, spec-120-progress/ (coverage-evidence.md + acceptance-evidence.md + governance-review.md), state/audit_index.py, state/audit_otel_export.py, state/audit_replay.py, state/trace_context.py, plus tests under tests/unit/state/, tests/unit/cli/, tests/unit/hooks/, and tests/integration/test_spec_120_e2e.py.

Every file lives in one of the boundaries the prompt named:

| Boundary | Status |
|----------|--------|
| src/ai_engineering/state/ | OK |
| src/ai_engineering/cli_commands/ | OK |
| .ai-engineering/scripts/hooks/_lib/ | OK |
| .ai-engineering/scripts/hooks/runtime-stop.py | OK |
| tests/ | OK |
| Plus declared adjacent: schema, gitignore, AGENTS/CLAUDE docs, spec/plan/progress | OK (declared in spec section 4 and plan T-A2 / T-D2 / T-E3) |

Notably **untouched** (in keeping with the spec-120 hard constraints):

- src/ai_engineering/state/audit_chain.py
- src/ai_engineering/state/decisions.py
- Any .claude/skills/** file
- Any .github/** or .agents/** IDE-mirror file
- pyproject.toml dependencies (uses stdlib sqlite3 only - no new dep added)

**Verdict**: **Boundaries respected.**

---

## 5. CONSTITUTION.md non-negotiables

Brief sweep of CONSTITUTION articles relevant to spec-120:

| Article | Subject | Spec-120 stance |
|---------|---------|------------------|
| V | Skill SSOT | Untouched (no skill files modified). |
| VI | Supply chain integrity | No new third-party dependencies added; all new modules use stdlib (sqlite3, hashlib, json, pathlib, datetime, uuid). |
| VII | No suppression | No noqa, no skip flags, no skipped audit-chain tests. |
| VIII | Conventional commits | Will be honoured at commit time. |

Other articles (I-IV, IX-XII) cover plane separation, ownership routes, telemetry obligations, and decision lifecycle - none of which spec-120 modifies. Spec-120 adds capacity to the telemetry plane.

**Verdict**: **No conflict.**

---

## 6. Risk acceptance - deferred items vs spec text

| Deferred item | Listed in spec section 3 / section 8? | Status |
|---------------|---------------------------------------|--------|
| HTML / web UI viewer | section 3 (non-goal) and section 8 (deferred) | OK |
| Real-time streaming export | section 3 (non-goal) and section 8 (deferred) | OK |
| Token attribution from IDE - currently no-op | section 2 + section 3 + section 7 (best-effort, IDE-cooperation) | OK Surface plumbed; population deferred to T-E2. |
| Backfill of traceId/spanId into existing NDJSON | section 3 + section 8 | OK Forward-only enrichment. |
| Self-hosted Langfuse / Phoenix / Logfire | section 3 (non-goal) | OK We emit OTLP JSON, deployment is operator choice. |
| Cross-session analytics | section 8 (deferred) | OK Future spec. |
| Cost-optimization recommender | section 8 (deferred) | OK Future spec. |
| Automatic OTel collector deployment | section 8 (deferred) | OK Future spec. |

Every gap surfaced during acceptance verification is pre-declared in spec section 3 (non-goals) or section 8 (deferred). The token columns NULL on production data and the OTel exporter exercised against a synthetic trace are both natural consequences of the forward-only enrichment design choice.

**Verdict**: **All deferred items have explicit spec coverage.**

---

## Final sign-off

* Constitution Article V - **CLEAR**
* Audit-chain integrity - **CLEAR** (src/ai_engineering/state/audit_chain.py lines 78-104)
* Hook integrity - **CLEAR** (hooks-manifest OK 60 hooks)
* Ownership boundaries - **CLEAR** (every modified/added file inside the spec-120 perimeter)
* CONSTITUTION non-negotiables - **CLEAR**
* Risk acceptance - **CLEAR** (every gap pre-declared in section 3 / section 8)

All eight acceptance criteria reported GREEN in acceptance-evidence.md, with two pre-declared caveats (token rollup NULL on legacy data; OTel exporter validated end-to-end via synthetic trace + smoke-validated against real single-event trace). The 44 pre-existing test failures were verified to be unrelated to spec-120 (reproduced on baseline with spec-120 stashed).

**Sign-off: GO**
