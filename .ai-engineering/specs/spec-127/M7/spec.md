---
id: sub-008
parent: spec-127
milestone: M7
title: "Adapter library for /ai-build (7 stacks)"
status: planning
files:
  - .ai-engineering/adapters/typescript/
  - .ai-engineering/adapters/python/
  - .ai-engineering/adapters/go/
  - .ai-engineering/adapters/rust/
  - .ai-engineering/adapters/swift/
  - .ai-engineering/adapters/csharp/
  - .ai-engineering/adapters/kotlin/
  - tests/adapters/test_adapter_scaffolding.py
  - tests/adapters/test_typescript_fixture.py
  - tests/adapters/test_python_fixture.py
  - tests/adapters/test_go_fixture.py
  - tests/adapters/test_rust_fixture.py
  - tests/adapters/test_swift_fixture.py
  - tests/adapters/test_csharp_fixture.py
  - tests/adapters/test_kotlin_fixture.py
  - tests/unit/router/test_deterministic_router.py
  - tools/skill_app/deterministic_router.py
  - .claude/skills/ai-build/SKILL.md
depends_on:
  - sub-001
  - sub-002
---

# Sub-Spec 008: M7 — Adapter library for /ai-build (7 stacks)

## Scope

Per D-127-06 (hand-authored adapters using `contexts/languages/` +
`contexts/frameworks/` as reference, no projection script). Author 28-file
adapter library: 7 stacks × 4 files each.

Stacks: TypeScript (refs `contexts/languages/typescript.md` +
`frameworks/{nextjs,react,nodejs,bun}.md`), Python (refs
`languages/python.md` + `frameworks/{django,api-design,backend-patterns}.md`),
Go (refs `languages/go.md`), Rust (refs `languages/rust.md`), Swift (refs
`languages/swift.md` + `frameworks/ios.md`), C# (refs `languages/csharp.md` +
`frameworks/aspnetcore.md`), Kotlin (refs `languages/kotlin.md` +
`frameworks/android.md`).

Per stack ship 4 files: `conventions.md`, `tdd_harness.md`,
`security_floor.md`, `examples/<≥2>.md`. Each `conventions.md` opens with a
header pinning source-revision: `<!-- source: contexts/languages/<stack>.md
@ <git-sha> -->`. Per-stack fixture `tests/adapters/test_<stack>_fixture.py`
exercises a minimal task (lint + test runner invocation) using the adapter
prose to prove translation works.

Implement `tools/skill_app/deterministic_router.py` (task path + spec stack
→ adapter; <50 ms). Wire router into `/ai-build` skill body before
`ai-build` agent invocation. Verify
`tests/unit/router/test_deterministic_router.py` covers all 7 stacks.

## Exploration

### Pre-flight findings

- All 7 language refs present: `typescript.md, python.md, go.md, rust.md,
  swift.md, csharp.md, kotlin.md`. ✅ no blocker.
- All required framework refs present: `nextjs.md, react.md, nodejs.md,
  bun.md, django.md, api-design.md, backend-patterns.md, ios.md,
  aspnetcore.md, android.md`. ✅ no blocker.
- `.ai-engineering/adapters/` does NOT exist — created in T-8.2.
- `.claude/skills/ai-build/` does NOT exist yet — current skill is
  `.claude/skills/ai-dispatch/`. Rename owned by M4 (sub-005). T-8.13 gated
  on M4 completion.
- `tools/skill_app/` does NOT exist yet — created in M1 (sub-002 hex
  scaffold). T-8.12 gated on M1.
- `tests/adapters/` does NOT exist — created by T-8.1.
- `tests/unit/router/` does NOT exist — created by T-8.11.

### Reference inventory (contexts/ → adapter)

| Stack | language ref | framework refs |
| typescript | contexts/languages/typescript.md | frameworks/{nextjs,react,nodejs,bun}.md |
| python | contexts/languages/python.md | frameworks/{django,api-design,backend-patterns}.md |
| go | contexts/languages/go.md | (none) |
| rust | contexts/languages/rust.md | (none) |
| swift | contexts/languages/swift.md | frameworks/ios.md |
| csharp | contexts/languages/csharp.md | frameworks/aspnetcore.md |
| kotlin | contexts/languages/kotlin.md | frameworks/android.md |

### Deliverable matrix (≥35 files, 7 stacks × 5 files min)

Per stack under `.ai-engineering/adapters/<stack>/`:
1. `conventions.md` — opens with `<!-- source: contexts/languages/<stack>.md
   @ <git-sha> -->` (T-8.9). Sections: Naming, File layout, Imports, Error
   handling, Idiomatic shape.
2. `tdd_harness.md` — failing-test-first flow on native runner (`vitest`,
   `pytest`, `go test`, `cargo test`, `XCTest`, `xUnit`, `JUnit5`); RED→GREEN
   command, watch flag, failure-message conventions.
3. `security_floor.md` — input validation, secrets, OWASP top-3, lint/scan
   hooks.
4. `examples/<example-1>.md` + `examples/<example-2>.md` — ≥2 minimal
   patterns referencing framework refs.

Adapter file totals: 35 (5 × 7) + 7 fixture tests + 1 scaffolding test +
1 router test + 1 router module + 1 SKILL.md edit = **46 deliverables**.

### Router path table

| Input                                              | Resolution    | Output                         |
| spec_stack ∈ KNOWN_STACKS                          | direct match  | `adapters/<spec_stack>/`       |
| spec_stack missing, *.ts/.tsx/.mts/.cts/.js/.jsx/.mjs/.cjs | extension map | `adapters/typescript/`     |
| spec_stack missing, *.py/.pyi                     | extension map | `adapters/python/`             |
| spec_stack missing, *.go                          | extension map | `adapters/go/`                 |
| spec_stack missing, *.rs                          | extension map | `adapters/rust/`               |
| spec_stack missing, *.swift                       | extension map | `adapters/swift/`              |
| spec_stack missing, *.cs/.csx                     | extension map | `adapters/csharp/`             |
| spec_stack missing, *.kt/.kts                     | extension map | `adapters/kotlin/`             |
| neither resolves                                   | error         | `UnknownStackError`            |

Budget: <50 ms p95 (pure function, stdlib only). Verified by perf assertion
in `tests/unit/router/test_deterministic_router.py::test_router_p95_under_50ms`.

### Hexagonal placement

- `tools/skill_app/deterministic_router.py` — **app layer**. Pure function.
  Imports: `pathlib`, `typing` only. No domain or infra dependency.
  No import of `.ai-engineering/adapters/*` (those are prose, not Python).
- Adapters are **PROSE markdown** under `.ai-engineering/adapters/<stack>/`.
  Read by `ai-build` agent at runtime, not imported by Python.
- Skill wire: `.claude/skills/ai-build/SKILL.md` Workflow section cites
  `tools.skill_app.deterministic_router:resolve_adapter()` as DET step before
  agent invocation.

### Cross-sub gating

- Depends on sub-001 (M0) + sub-002 (M1 hex scaffold).
- Coordinates with sub-005 (M4 `/ai-dispatch` → `/ai-build` rename). T-8.13
  gated on M4; if M4 lags, T-8.13 stays open while rest of M7 completes.
- Hand-authored per D-127-06 — no projection script.
