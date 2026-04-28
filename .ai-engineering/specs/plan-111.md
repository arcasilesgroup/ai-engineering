# Plan: spec-111 AI Research Skill

## Pipeline: full
## Phases: 4
## Tasks: 46 (build: 40, verify: 5, guard: 1)

## Architecture

**Layered Architecture (with pipes-and-filters tendency in tier orchestration)**.

Justification: the skill structure (`.claude/skills/ai-research/SKILL.md` + `handlers/<topic>.md`) is a layered composition — SKILL.md is the entry point, handlers are sub-modules with single responsibilities (classify, tier0, tier1, tier2, tier3, synthesize, persist), and each handler reads/writes its own concern. Within the orchestration, tiers behave as pipes-and-filters (Tier 0 → Tier 1 → Tier 2 → Tier 3, each can short-circuit or escalate), but no formal pipes-and-filters infrastructure (queues, blocking handoffs) exists — orchestration is sequential function calls in a single agent context. Layered is the dominant pattern; pipes-and-filters is a local pattern for the tier escalation logic. No domain layer requires hexagonal isolation (no swappable infra for the skill); no event-sourcing because there is no temporal reconstruction need; no CQRS because read and write paths share the same shape. Layered matches existing skills (`/ai-brainstorm`, `/ai-plan`, etc.) and minimizes onboarding cost for downstream agents.

## Design

Skipped — `/ai-research` is a CLI/agent skill with no UI surface. No `/ai-design` invocation required.

---

### Phase 1 — Skill Scaffold + Tier 0 (Local)

**Gate**: `.claude/skills/ai-research/` exists with `SKILL.md` (frontmatter + Process section) and handlers `classify-query.md`, `tier0-local.md`, `tier1-free-mcps.md`, `tier2-web.md`, `tier3-notebooklm.md`, `synthesize-with-citations.md`, `persist-artifact.md` (placeholder content for Phase 1; filled in later phases). Mirrors regenerated for `.codex/skills/ai-research/`, `.gemini/skills/ai-research/`, `.github/skills/ai-research/`. Tier 0 (local) handler reads `.ai-engineering/research/*.md`, `LESSONS.md`, `framework-events.ndjson` and short-circuits when ≥3 relevant local hits found. Tests `test_ai_research_skill_present.py::test_skill_and_mirrors_exist` and `test_ai_research_tier0.py::test_local_match_short_circuits_when_sufficient` pass.

- [ ] T-1.1: Write failing test `tests/integration/test_ai_research_skill_present.py::test_skill_and_mirrors_exist` that asserts `.claude/skills/ai-research/SKILL.md` exists plus all 7 handlers, and that mirror skills exist in `.codex/skills/ai-research/`, `.gemini/skills/ai-research/`, `.github/skills/ai-research/` (agent: build)
- [ ] T-1.2: Create `.claude/skills/ai-research/SKILL.md` with frontmatter (`name: ai-research`, `effort: high`, `triggers: ['research', 'investigate', 'find sources', 'state of the art', 'compare options']`, `description: <oneliner>`) + Process section listing 7 steps (classify → tier0 → tier1 → tier2 → tier3 → synthesize → persist) (agent: build, blocked by T-1.1)
- [ ] T-1.3: Create handlers placeholder files: `.claude/skills/ai-research/handlers/{classify-query,tier0-local,tier1-free-mcps,tier2-web,tier3-notebooklm,synthesize-with-citations,persist-artifact}.md` with section headers but no logic yet (filled in later tasks) (agent: build, blocked by T-1.2)
- [ ] T-1.4: Run `ai-eng sync-mirrors` to regenerate `.codex/skills/ai-research/`, `.gemini/skills/ai-research/`, `.github/skills/ai-research/` from `.claude/skills/ai-research/` (agent: build, blocked by T-1.3)
- [ ] T-1.5: GREEN — verify `test_skill_and_mirrors_exist` passes (agent: build, blocked by T-1.4)
- [ ] T-1.6: Write failing tests `tests/integration/test_ai_research_tier0.py::test_local_match_short_circuits_when_sufficient` (≥3 hits → tiers 1-3 not invoked), `test_local_match_escalates_when_insufficient` (<3 hits → tier 1 invoked), `test_grep_research_artifacts_finds_topic_slug_match` (agent: build)
- [ ] T-1.7: Implement Tier 0 logic in `tier0-local.md` handler — algorithm: glob `.ai-engineering/research/*.md` and topic-slug similarity ≥0.7 via `difflib.SequenceMatcher`; grep `LESSONS.md` for keyword matches; parse `framework-events.ndjson` last 30 days filtering `kind: skill_invoked AND detail.skill = "ai-research"` for prior queries (agent: build, blocked by T-1.6)
- [ ] T-1.8: GREEN — verify all 3 tier0 tests pass (agent: build, blocked by T-1.7)

---

### Phase 2 — Tiers 1-2 (Free MCPs + Web)

**Gate**: Tier 1 invokes Context7 (`mcp__context7__resolve-library-id` + `query-docs`), Microsoft Learn MCP (`microsoft_docs_search` + `microsoft_code_sample_search`), and `gh search code/repos` IN PARALLEL when query mentions library/Azure/Microsoft/code patterns. Results deduped by URL/path. Tier 2 invokes WebSearch + WebFetch in parallel; supports `--allowed-domains` and `--blocked-domains` pass-through. Tests `test_ai_research_tier1.py::test_three_mcps_called_in_parallel` and `test_ai_research_tier2.py::test_websearch_invoked_with_filters` pass.

- [ ] T-2.1: Write failing test `tests/integration/test_ai_research_tier1.py::test_three_mcps_called_in_parallel` — mocks all 3 MCPs and validates concurrent invocation (timestamp delta < 100ms between starts) (agent: build)
- [ ] T-2.2: Write failing test `tests/integration/test_ai_research_tier1.py::test_dedup_by_url_or_path` (agent: build, blocked by T-2.1)
- [ ] T-2.3: Implement Tier 1 logic in `tier1-free-mcps.md` handler: classification heuristic to decide which MCP(s) apply (library mention → Context7; "Azure"/"Microsoft"/".NET" → MS Learn; "github"/code patterns → gh search); parallel invocation via `Promise.all`-equivalent in agent execution; dedup by URL stripped of query params for web sources, by `repo+path` for code (agent: build, blocked by T-2.2)
- [ ] T-2.4: GREEN — verify both tier1 tests pass (agent: build, blocked by T-2.3)
- [ ] T-2.5: Write failing test `tests/integration/test_ai_research_tier2.py::test_websearch_invoked_with_filters` — validates `--allowed-domains a.com,b.com` flag passes through to WebSearch tool call (agent: build)
- [ ] T-2.6: Write failing test `tests/integration/test_ai_research_tier2.py::test_tier2_skipped_when_tier1_yields_5_plus_hits` (agent: build, blocked by T-2.5)
- [ ] T-2.7: Implement Tier 2 logic in `tier2-web.md` handler — WebSearch with optional `allowed_domains`/`blocked_domains` pass-through; WebFetch when specific URL is referenced in query; parallel invocation; tier2 skip heuristic when tier1 returned ≥5 high-quality hits (agent: build, blocked by T-2.6)
- [ ] T-2.8: GREEN — verify both tier2 tests pass (agent: build, blocked by T-2.7)

---

### Phase 3 — Tier 3 (NotebookLM Persistent) + Persistence

**Gate**: Tier 3 creates new NotebookLM notebook with naming `ai-research/<topic-slug>-<YYYY-MM-DD>-<hash6>`, adds Tier 2 sources via `source_add` (max 20), queries with citation instruction, captures `notebook_id` and `conversation_id`. `--reuse-notebook=<id>` flag opt-in for follow-ups. Tier 3 triggered when `--depth=deep` or agent decides (heuristic: comparative/multi-source query). Persistence handler writes `.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md` with frontmatter + Question/Findings/Sources/Notebook Reference sections. Auto-persist when Tier 3 invoked; opt-in `--persist` for quick/standard. Tests `test_ai_research_tier3.py::test_notebooklm_creation_and_query_with_citations` and `test_persist.py::test_artifact_format_complete` pass.

- [ ] T-3.1: Write failing tests `tests/integration/test_ai_research_tier3.py::test_notebooklm_creation_and_query_with_citations` (mock MCP, validate `notebook_create` call with naming pattern, `source_add` calls per URL, `notebook_query` call with citation instruction, captures `notebook_id`+`conversation_id`), `test_max_20_sources` (agent: build)
- [ ] T-3.2: Write failing test `tests/integration/test_ai_research_tier3.py::test_reuse_notebook_flag_skips_creation` (when `--reuse-notebook=abc123`, `notebook_create` is NOT called; `source_add`+`notebook_query` use the provided ID) (agent: build, blocked by T-3.1)
- [ ] T-3.3: Implement topic-slug generator in `tier3-notebooklm.md` — algorithm: `re.sub(r'[^a-z0-9]+', '-', query.lower())[:40].strip('-')` (agent: build, blocked by T-3.2)
- [ ] T-3.4: Implement hash6 generator — `hashlib.sha256(f"{query}|{timestamp_iso}".encode()).hexdigest()[:6]` (agent: build, blocked by T-3.3)
- [ ] T-3.5: Implement Tier 3 main flow in `tier3-notebooklm.md` — create notebook (or reuse), add sources (cap 20), query with instruction "answer with citations to provided sources, use `[N]` notation", capture IDs, return synthesized response (agent: build, blocked by T-3.4)
- [ ] T-3.6: Implement Tier 3 trigger heuristic — invoke when (`--depth=deep` flag) OR (query is comparative: matches `\b(vs|versus|compare|difference between|alternatives?)\b`) OR (Tier 1+2 returned ≥10 sources, suggesting deep corpus available) (agent: build, blocked by T-3.5)
- [ ] T-3.7: GREEN — verify all 3 tier3 tests pass (agent: build, blocked by T-3.6)
- [ ] T-3.8: Write failing test `tests/unit/skills/ai_research/test_persist.py::test_artifact_format_complete` — validates frontmatter (query, depth, tiers_invoked, sources_used, notebook_id, created_at, slug), body sections (Question, Findings with citations inline, Sources numbered list, Notebook Reference URL if applicable) (agent: build)
- [ ] T-3.9: Write failing test `test_persist.py::test_auto_persist_when_tier3_invoked` and `test_opt_in_persist_for_quick_standard` (agent: build, blocked by T-3.8)
- [ ] T-3.10: Implement `persist-artifact.md` handler — write to `.ai-engineering/research/<topic-slug>-<YYYY-MM-DD>.md` with deterministic format (agent: build, blocked by T-3.9)
- [ ] T-3.11: GREEN — verify all persistence tests pass (agent: build, blocked by T-3.10)

---

### Phase 4 — Citation Validation + Brainstorm Integration + Resilience + Final Gates

**Gate**: synthesize-with-citations.md enforces citation hard-rule with `[unsourced]` literal for unsourced claims; validator regex `\[\d+\]|\[unsourced\]` matches at least once per claim paragraph. `/ai-brainstorm` interrogate.md handler invokes `/ai-research --depth=standard` when external evidence required; spec-schema.md permits `references: research:` entries. Resilience: graceful degradation when MCPs fail (Context7/MS Learn/NotebookLM). 4 CLI flags work (`--depth`, `--reuse-notebook`, `--persist`, `--allowed-domains`/`--blocked-domains`). 0 secrets, 0 vulns, 0 lint errors; coverage ≥80%; no NG violations.

- [ ] T-4.1: Write failing tests `tests/unit/skills/ai_research/test_citation_validator.py::test_output_with_citations_passes`, `test_output_without_citations_fails_validation`, `test_output_with_unsourced_marker_passes` (agent: build)
- [ ] T-4.2: Implement `synthesize-with-citations.md` handler — collect all sources from prior tiers into numbered list; generate output using LLM-as-synthesizer (agent context, no external API); apply citation validator regex; if validation fails, retry with stricter system message (max 2 retries); on retry exhaustion, output with warning "citations malformed" (agent: build, blocked by T-4.1)
- [ ] T-4.3: GREEN — verify citation validator tests pass (agent: build, blocked by T-4.2)
- [ ] T-4.4: Write failing test `tests/integration/test_brainstorm_research_integration.py::test_interrogation_invokes_research_when_evidence_required` (mocks brainstorm interrogation flow with question requiring external evidence; asserts `/ai-research` is invoked and artifact reference appears in spec) (agent: build)
- [ ] T-4.5: Modify `.claude/skills/ai-brainstorm/handlers/interrogate.md` — add explicit step "Si la pregunta requiere evidencia externa que el modelo no puede confirmar (e.g., 'qué patrones usa la industria', 'qué dice el state of the art'), invocar `/ai-research --depth=standard <subquery>` y consumir el artifact resultante; citarlo en spec en `## References` con prefix `research:`" (agent: build, blocked by T-4.4)
- [ ] T-4.6: Modify `.ai-engineering/contexts/spec-schema.md` — under Optional Sections, expand `## References` description to permit entries `- research: .ai-engineering/research/<artifact>.md` and document the prefix convention (agent: build, blocked by T-4.5)
- [ ] T-4.7: GREEN — verify brainstorm integration test passes (agent: build, blocked by T-4.6)
- [ ] T-4.8: Write failing tests `tests/integration/test_ai_research_resilience.py::test_context7_down_degrades_to_other_tier1`, `test_ms_learn_down_continues_with_other_mcps`, `test_notebooklm_auth_expired_degrades_to_tier2_only_with_warning`, `test_all_external_down_returns_local_only_with_warning` (agent: build)
- [ ] T-4.9: Implement degraded mode logic in `tier1-free-mcps.md` and `tier3-notebooklm.md` — try/except around MCP calls, on failure log warning visible to user, continue with remaining sources; for NotebookLM, probe `server_info` first and skip Tier 3 if auth expired (agent: build, blocked by T-4.8)
- [ ] T-4.10: GREEN — verify all 4 resilience tests pass (agent: build, blocked by T-4.9)
- [ ] T-4.11: Write failing tests `tests/unit/skills/ai_research/test_cli_args.py` for 8 flag scenarios (default depth=standard; --depth=quick; --depth=deep; --reuse-notebook=ID; --persist with quick; --allowed-domains a,b; --blocked-domains x,y; combination of multiple) (agent: build)
- [ ] T-4.12: Implement CLI flag handling in SKILL.md — document parameter parsing convention; ensure handlers receive parsed flags (agent: build, blocked by T-4.11)
- [ ] T-4.13: GREEN — verify all 8 CLI tests pass (agent: build, blocked by T-4.12)
- [ ] T-4.14: Markdown lint of new SKILL.md + 7 handlers + integration changes (agent: verify, blocked by T-4.13)
- [ ] T-4.15: Run `gitleaks protect --staged --no-banner` on all changed files — 0 findings (agent: verify, blocked by T-4.14)
- [ ] T-4.16: Run `pip-audit` — 0 high/critical vulns (agent: verify, blocked by T-4.15)
- [ ] T-4.17: Run `ruff format` + `ruff check` on changed Python tests — 0 errors (agent: verify, blocked by T-4.16)
- [ ] T-4.18: Run `pytest --cov=tests.integration.test_ai_research --cov=tests.unit.skills.ai_research` — verify ≥80% coverage on test scaffolding + handler logic invoked from tests (agent: verify, blocked by T-4.17)
- [ ] T-4.19: Pre-dispatch governance check — verify no NG violations: no Tier 4 academic (NG-1), no Tier 5 BYOK (NG-2), no survey mode (NG-3), no auto-detection in other skills (NG-4), no ML reranking (NG-5), no non-Markdown artifacts (NG-6), no auto-update of artifacts (NG-7), no internal enterprise search (NG-8), no autogenerated TL;DR (NG-9). (agent: guard, blocked by T-4.18)

---

## Risk Mitigation Notes

- **R-1 NotebookLM auth expiry**: T-4.8 + T-4.9 test and implement graceful degradation Tier 3 → Tier 2 with visible warning + suggestion to run `nlm login`.
- **R-2 gh search rate limits**: T-2.3 implementation note — caller's responsibility to add cache; if rate limit hit, captured by T-4.8 resilience tests as gh-down scenario.
- **R-3 Citation parsing failures**: T-4.2 implements 2-retry mechanism with stricter system message before output-with-warning.
- **R-4 NotebookLM Deep Research off-topic**: T-3.5 explicitly avoids invoking the autonomous Deep Research feature; only `source_add` with curated URLs from Tier 2.
- **R-5 Topic-slug collisions**: T-3.4 hash6 suffix guarantees uniqueness even with similar slugs.
- **R-6 Context window inflation**: implementation note in T-2.3 + T-2.7 — cap per tier (Tier 1: 5 results × 500 tokens; Tier 2: 10 results × 200 tokens); validate in T-4.18 coverage tests.
- **R-7 Domain filter zero results**: T-2.5 expects warning surface when filtered set is empty; visible in test fixture.

## Self-Review Notes

Reviewed once. No additional iteration needed:
- Each task is bite-sized and single-concern.
- TDD pairing applied: tests precede implementation in every domain (Phase 1: skill + tier0; Phase 2: tier1 + tier2; Phase 3: tier3 + persistence; Phase 4: citation validator + brainstorm integration + resilience + CLI flags).
- Phase gates are clearly verifiable.
- Dependencies explicit and acyclic.
- Architecture pattern (Layered) justified.
- No tasks attempt scope beyond spec (NG list checked in T-4.19).
- Resilience covered before final gate via dedicated tests (T-4.8 to T-4.10).
