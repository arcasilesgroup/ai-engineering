# Harness Gap Closure 2026-05-04 — Decomposition Manifest

## Source spec
User-supplied prompt 2026-05-04. Closes 11 audit findings, P0–P4.

## Branch
- Source: `feat/spec-120-observability-modernization` (HEAD a19053ad spec-121 close)
  Note: spec said "off main" but main lacks spec-118/119/120/121 infrastructure
  the spec depends on. Branched off the integration branch instead.
- Working: `feat/harness-gap-closure-2026-05-04-v2`

## Baseline (pre-work)
- memory.db: episodes=0, knowledge_objects=100, retrieval_log=2
- memory_vectors: errors via sqlite3 CLI (`no such module: vec0`); needs verification via Python
- framework-events.ndjson: 78,450 lines; 0 component=memory; 0 engine=codex
- Stashed: WIP parity-check + spec-120 tail (unrelated, deferred)

## Sub-specs (9 concerns)

| ID    | Title                                              | Priority | Files (primary)                                                   |
|-------|----------------------------------------------------|----------|-------------------------------------------------------------------|
| SS-01 | Memory persistence repair (P0.1)                   | P0       | hooks/memory-stop.py, scripts/memory/cli.py, tests/integration    |
| SS-02 | Integrity default = enforce (P0.2)                 | P0       | hooks/_lib/integrity.py + tests                                    |
| SS-03 | Ralph reinjection enabled-by-default (P0.3)        | P0       | hooks/runtime-stop.py + tests                                      |
| SS-04 | Codex injection guard matcher coverage (P1.1)      | P1       | .codex/hooks.json + tests/integration                              |
| SS-05 | Memory cross-IDE parity (P1.2)                     | P1       | .codex/hooks.json, .gemini/settings.json, .github/hooks/* + tests  |
| SS-06 | Eval-gate CI workflow (P2.1)                       | P2       | .github/workflows/eval-gate.yml                                    |
| SS-07 | Embedding async worker (P2.2)                      | P2       | scripts/memory/embed_worker.py, scripts/memory/cli.py + tests      |
| SS-08 | A2A artifact protocol + ACI severity (P3.1+P3.2)   | P3       | _lib/agent_protocol.py, _lib/observability.py, _lib/audit.py + tests |
| SS-09 | OTLP live-tail daemon (P4.1)                       | P4       | src/ai_engineering/cli_commands/audit_cmd.py + tests/integration    |

## DAG (file-overlap + import-chain analysis)

Computed after planning agents return Plans. Tentative file-overlap zones:
- `hooks/memory-stop.py` → SS-01 only
- `hooks/runtime-stop.py` → SS-03 only (P3 events go via observability)
- `_lib/integrity.py` → SS-02 only
- `.codex/hooks.json` → SS-04 + SS-05 (must serialize)
- `_lib/observability.py` → SS-08 only (SS-01 may read only)
- `_lib/audit.py` → SS-08 only (SS-09 may read only)
- `scripts/memory/cli.py` → SS-01 + SS-07 (must serialize)
- `audit_cmd.py` → SS-09 only

## Constraints (verbatim from spec)
- No CONSTITUTION.md / AGENTS.md edits
- Pre-commit < 1s, pre-push < 5s budget
- Hooks fail-open; only integrity flip is a new "block" (with env escape)
- schemaVersion 1.0 must still parse after 1.1 lands
- No new pyproject.toml deps (sqlite-vec, fastembed, hdbscan already pinned)
- PR must reference this spec block + link spec-122
- spec-121 status field updated post-merge
