# Plan: spec-081 ai-eng update Interactive UX and Diagnostics

## Pipeline: full
## Phases: 3
## Tasks: 9 (build: 6, verify: 2, guard: 1)

### Phase 1: Lock Contracts
**Gate**: The updater service returns explicit outcome metadata, and failing tests describe the intended behavior before CLI implementation starts.
- [x] T-1.1: Write failing service-level tests for update outcome classification and reason codes in the updater result model. (agent: build)
- [x] T-1.2: Implement updater result-model changes so each file change carries outcome, reason code, explanation, and recommended action without changing ownership semantics. (agent: build)
- [x] T-1.3: Write failing CLI tests for interactive TTY preview/confirm flow, including the rule that human apply intent still previews before writing. (agent: build)

### Phase 2: Deliver User Experience
**Gate**: Human CLI output matches the approved update UX, and non-interactive or JSON flows remain prompt-free and explicit.
- [x] T-2.1: Implement human TTY flow in `update_cmd`: preview first, group outcomes, prompt for confirmation, and apply only after confirmation. (agent: build)
- [x] T-2.2: Implement human-facing messaging that replaces raw labels such as `skip-denied` with ownership-aware explanations and no-action-needed guidance where appropriate. (agent: build)
- [x] T-2.3: Implement JSON output contract changes so automation receives structured outcome, reason code, explanation, and recommended action per file. (agent: build)
- [x] T-2.4: Add or update CLI tests for JSON mode, non-TTY compatibility, grouped summaries, and separation of protected items from real failures. (agent: build)

### Phase 3: Verify And Harden
**Gate**: Focused tests pass, automation compatibility is confirmed, and governance review finds no drift from install-style behavior.
- [x] T-3.1: Run the focused updater and CLI test suites, fix any regressions introduced by the redesign, and keep behavior within approved scope. (agent: build)
- [x] T-3.2: Verify that the final behavior matches spec-081 acceptance criteria for TTY, non-TTY, JSON, and ownership-protection messaging. (agent: verify)
- [x] T-3.3: Review the final flow for governance and compatibility drift against `ai-eng install`, especially prompt suppression and operator guidance in automation scenarios. (agent: guard)

## Notes

- TDD applies to the service-model and CLI behavior changes: tests first, then implementation.
- Tasks in Phase 2 depend on the result-model work from Phase 1.
- T-2.4 depends on T-2.1 through T-2.3 being implemented.
- T-3.2 and T-3.3 run only after the build tasks are complete.
