---
total: 38
completed: 0
---

# Plan: sub-008 M7 — Adapter library for /ai-build (7 stacks)

## Pipeline: full
## Phases: 11
## Tasks: 38 (build: 31, verify: 7)

## Architecture

**Pattern**: Hexagonal.
- `tools/skill_app/deterministic_router.py` — app layer. Pure function,
  <50ms, stdlib only — no domain or infra deps.
- Adapters as PROSE markdown under `.ai-engineering/adapters/<stack>/`. Read
  by `ai-build` agent at runtime, never imported by Python. Router returns
  filesystem Path; agent loads markdown into context.
- Source-revision header per T-8.9 / D-127-06: every `conventions.md` opens
  with `<!-- source: contexts/languages/<stack>.md @ <git-sha> -->` for
  drift detection.
- Hand-authored per D-127-06: each adapter author reads cited `contexts/`
  files and writes prose. No template auto-generation.

## Design

Skipped — prose authoring + pure-function router.

## Phase classification: full

46 file deliverables (35 adapter prose + 7 fixture tests + 1 scaffolding
test + 1 router test + 1 router module + 1 SKILL.md edit). 38 tasks. Two
RED→GREEN pairs. Per-stack fixture gating.

### Phase structure (sequential gating per stack)

```
P0: scaffold test RED                        (T-8.1)
P1: typescript adapter + fixture             (T-8.2.x, T-8.10.ts)
P2: python adapter + fixture                 (T-8.3.x, T-8.10.py)
P3: go adapter + fixture                     (T-8.4.x, T-8.10.go)
P4: rust adapter + fixture                   (T-8.5.x, T-8.10.rs)
P5: swift adapter + fixture                  (T-8.6.x, T-8.10.sw)
P6: csharp adapter + fixture                 (T-8.7.x, T-8.10.cs)
P7: kotlin adapter + fixture                 (T-8.8.x, T-8.10.kt)
P8: router test RED                          (T-8.11)
P9: router GREEN + skill wire                (T-8.12, T-8.13)
P10: scaffold + fixture verify               (T-8.14)
```

Per-stack gate: each adapter ships with paired fixture green BEFORE next stack
begins. Parallelism viable across stacks but per-stack atomic.

### Phase 0 — Scaffold test RED

**Gate**: `tests/adapters/test_adapter_scaffolding.py` exists, FAILS (no
adapters yet).

- [ ] T-8.1: Failing test asserting per-stack: `conventions.md` exists +
  opens with `<!-- source: contexts/languages/<stack>.md @ <sha> -->`,
  `tdd_harness.md` ≥30 lines, `security_floor.md` ≥30 lines,
  `len(glob('examples/*.md')) >= 2` (agent: build)

### Phase 1 — TypeScript

**Gate**: `tests/adapters/test_typescript_fixture.py` green; scaffolding
asserts pass for `typescript`.

- [ ] T-8.2.a: `adapters/typescript/conventions.md` ref `contexts/languages/
  typescript.md` + `frameworks/{nextjs,react,nodejs,bun}.md`. Source-revision
  header. **DO NOT modify test_adapter_scaffolding.py from T-8.1.** (agent: build)
- [ ] T-8.2.b: `adapters/typescript/tdd_harness.md` — vitest RED→GREEN, watch
  flag, failure conventions (agent: build)
- [ ] T-8.2.c: `adapters/typescript/security_floor.md` — input validation,
  secrets (process.env), OWASP top-3, eslint+npm audit (agent: build)
- [ ] T-8.2.d: `adapters/typescript/examples/{nextjs-page,node-service}.md`
  — ≥2 patterns (agent: build)
- [ ] T-8.10.ts: `tests/adapters/test_typescript_fixture.py` — minimal vitest
  task (agent: verify)

### Phase 2 — Python

- [ ] T-8.3.a: `adapters/python/conventions.md` ref `python.md` +
  `frameworks/{django,api-design,backend-patterns}.md`; header (agent: build)
- [ ] T-8.3.b: `adapters/python/tdd_harness.md` — pytest, `-x`, parametrize
  (agent: build)
- [ ] T-8.3.c: `adapters/python/security_floor.md` — pydantic, secrets, OWASP,
  ruff+bandit (agent: build)
- [ ] T-8.3.d: `adapters/python/examples/{django-view,fastapi-endpoint}.md`
  (agent: build)
- [ ] T-8.10.py: `tests/adapters/test_python_fixture.py` — minimal pytest
  (agent: verify)

### Phase 3 — Go

- [ ] T-8.4.a: `adapters/go/conventions.md` ref `go.md`; header (agent: build)
- [ ] T-8.4.b: `adapters/go/tdd_harness.md` — `go test`, table-driven, `-run`,
  `-race` (agent: build)
- [ ] T-8.4.c: `adapters/go/security_floor.md` — `staticcheck`+`govulncheck`
  (agent: build)
- [ ] T-8.4.d: `adapters/go/examples/{http-handler,table-test}.md` (agent: build)
- [ ] T-8.10.go: `tests/adapters/test_go_fixture.py` — minimal `go test`
  (agent: verify)

### Phase 4 — Rust

- [ ] T-8.5.a: `adapters/rust/conventions.md` ref `rust.md`; header (agent: build)
- [ ] T-8.5.b: `adapters/rust/tdd_harness.md` — `cargo test`, `#[cfg(test)]`,
  `cargo nextest` opt (agent: build)
- [ ] T-8.5.c: `adapters/rust/security_floor.md` — `cargo clippy`+`cargo audit`
  (agent: build)
- [ ] T-8.5.d: `adapters/rust/examples/{result-fn,trait-impl}.md` (agent: build)
- [ ] T-8.10.rs: `tests/adapters/test_rust_fixture.py` — minimal `cargo test`
  (agent: verify)

### Phase 5 — Swift

- [ ] T-8.6.a: `adapters/swift/conventions.md` ref `swift.md` + `ios.md`;
  header (agent: build)
- [ ] T-8.6.b: `adapters/swift/tdd_harness.md` — XCTest, `swift test`
  (agent: build)
- [ ] T-8.6.c: `adapters/swift/security_floor.md` — Keychain, ATS, `swift-lint`
  (agent: build)
- [ ] T-8.6.d: `adapters/swift/examples/{value-type-xctest,swiftui-view}.md`
  (agent: build)
- [ ] T-8.10.sw: `tests/adapters/test_swift_fixture.py` — XCTest task (skipped
  on non-macOS) (agent: verify)

### Phase 6 — C#

- [ ] T-8.7.a: `adapters/csharp/conventions.md` ref `csharp.md` +
  `aspnetcore.md`; header (agent: build)
- [ ] T-8.7.b: `adapters/csharp/tdd_harness.md` — xUnit, `dotnet test`,
  theory/inlinedata (agent: build)
- [ ] T-8.7.c: `adapters/csharp/security_floor.md` — IConfiguration, OWASP,
  `dotnet format`+`list package --vulnerable` (agent: build)
- [ ] T-8.7.d: `adapters/csharp/examples/{minimal-api,record-test}.md`
  (agent: build)
- [ ] T-8.10.cs: `tests/adapters/test_csharp_fixture.py` — `dotnet test`
  (agent: verify)

### Phase 7 — Kotlin

- [ ] T-8.8.a: `adapters/kotlin/conventions.md` ref `kotlin.md` + `android.md`;
  header (agent: build)
- [ ] T-8.8.b: `adapters/kotlin/tdd_harness.md` — JUnit5, gradle `test`,
  kotest opt (agent: build)
- [ ] T-8.8.c: `adapters/kotlin/security_floor.md` — Android Keystore, OWASP
  MASVS, ktlint+detekt (agent: build)
- [ ] T-8.8.d: `adapters/kotlin/examples/{sealed-class,compose-vm}.md`
  (agent: build)
- [ ] T-8.10.kt: `tests/adapters/test_kotlin_fixture.py` — gradle test
  (agent: verify)

### Phase 8 — Router test RED

**Gate**: `tests/unit/router/test_deterministic_router.py` written, FAILS.

- [ ] T-8.11: RED — covers all 7 stacks via `spec_stack` hit, all 8 extension
  fallbacks, `UnknownStackError`, p95<50ms perf assertion (agent: build)

### Phase 9 — Router GREEN + skill wire

**Gate**: T-8.11 green; `/ai-build` Workflow references router.

- [ ] T-8.12: Implement `tools/skill_app/deterministic_router.py` — pure
  function `resolve_adapter(task_path: str, spec_stack: str | None) -> Path`;
  stdlib-only; <50 ms. **DO NOT modify test_deterministic_router.py from
  T-8.11.** (agent: build)
- [ ] T-8.13: Wire router into `.claude/skills/ai-build/SKILL.md` Workflow
  before `ai-build` agent invocation (gated on M4 rename complete; if not,
  no-op until M4 lands) (agent: build)

### Phase 10 — Final verify

- [ ] T-8.14: `pytest tests/adapters/ tests/unit/router/ -v` — all 7 fixture
  tests + scaffolding + router green; record router perf (agent: verify)

## Phase Dependency Graph

```
P0 (RED) ──→ P1..P7 (per-stack adapter+fixture, sequential per-stack atomic) ──→ P8 (router RED) ──→ P9 (router GREEN + wire) ──→ P10 (final verify)
```

P1..P7 may parallelize across stacks if M1+M4 prereqs land first.

## TDD Pairing

- **T-8.1 (RED) → T-8.2.a..T-8.8.d (GREEN)**: scaffolding test fails until 7
  adapter dirs ship 5 required files. Constraint: **DO NOT modify
  `tests/adapters/test_adapter_scaffolding.py`.**
- **T-8.11 (RED) → T-8.12 (GREEN)**: router test fails until
  `deterministic_router.py` resolves all 7 stacks + extension map + perf.
  Constraint: **DO NOT modify `tests/unit/router/test_deterministic_router.py`.**

## Cross-sub gating

- sub-002 (M1) before T-8.12 (`tools/skill_app/` package must exist).
- sub-005 (M4) before T-8.13 (`/ai-build` skill must exist post-rename).

## Hot-path budget

Router <50ms p95 (asserted in T-8.11 perf test).

## Done Conditions

- [ ] 7 adapter dirs each ship `conventions.md` + `tdd_harness.md` +
  `security_floor.md` + `examples/<≥2>.md`
- [ ] Each `conventions.md` opens with source-revision header
- [ ] 7 per-stack fixture tests green
- [ ] `tests/adapters/test_adapter_scaffolding.py` green
- [ ] `tools/skill_app/deterministic_router.py` resolves all 7 stacks +
  extension fallbacks; `UnknownStackError` for neither; p95 <50ms
- [ ] `/ai-build` Workflow references router (post-M4)

## Self-Report
[EMPTY -- populated by Phase 4]
