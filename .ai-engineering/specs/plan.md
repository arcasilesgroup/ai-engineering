# Plan: codex-compliance-p0-p1

## Pipeline: standard
## Phases: 4
## Tasks: 10 (build: 7, verify: 3, guard: 0)

### Phase 1: Plan And Canonical Scope
**Gate**: Canonical source-of-truth, target files, and verification scope are fixed before edits begin.
- [x] T-1.1: Load ai-plan, ai-code, ai-test, and ai-debug procedures plus applicable `contexts/**` guidance. (agent: build)
- [x] T-1.2: Audit the current Codex/Copilot/agents drift to confirm P0 and P1 scope. (agent: build)
- [x] T-1.3: Persist the execution plan in this file before implementation starts. (agent: build)

### Phase 2: P0 Canonical Repairs
**Gate**: Canonical `.claude` sources and generated top-level instruction files no longer contain stale counts or broken public skill references.
- [x] T-2.1: Fix stale skill counts and public surface documentation in canonical docs/templates. (agent: build)
- [x] T-2.2: Repair `guard`/`explore` taxonomy drift so canonical agents and skills stop referencing nonexistent public skills. (agent: build)
- [x] T-2.3: Update mirror generation so `AGENTS.md` preserves provider-correct paths and derives counts from source data instead of stale literals. (agent: build)

### Phase 3: P1 Runtime And Readiness Repairs
**Gate**: Runtime detection and health checks reflect the installed Codex/Copilot surfaces, and skill scanning ignores non-skill markdown resources.
- [x] T-3.1: Extend provider autodetection to recognize the shared Codex/Gemini surface from `AGENTS.md` and `.agents`. (agent: build)
- [x] T-3.2: Fix live Copilot instruction generation/expectations so doctor and install surfaces agree. (agent: build)
- [x] T-3.3: Harden skill discovery/status logic to ignore helper markdown files that are not runnable skills. (agent: build)

### Phase 4: Verification And Regeneration
**Gate**: Mirrors regenerate cleanly, targeted tests pass, and repo validation/doctor output improves with evidence.
- [x] T-4.1: Add or update regression tests covering the generator, autodetect, taxonomy, and skill scanning changes. (agent: build)
- [x] T-4.2: Regenerate mirrors from canonical sources and inspect resulting diffs for unintended drift. (agent: build)
- [x] T-4.3: Run targeted test suites plus `ai-eng validate .` and `ai-eng doctor .`, then record outcomes against the original P0/P1 findings. (agent: build)
