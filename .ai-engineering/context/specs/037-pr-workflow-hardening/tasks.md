---
spec: "037"
total: 13
completed: 0
last_session: "2026-03-05"
next_session: "Phase 0 — Scaffold and Activate"
---

# Tasks — PR Workflow Hardening

## Phase 0: Scaffold and Activate [S]
- [ ] 0.1 Create spec lifecycle files (spec.md, plan.md, tasks.md)
- [ ] 0.2 Update `_active.md` to this spec and verify quick resume links

## Phase 1: Contract Parity Baseline [M]
- [ ] 1.1 Build parity matrix for `skills/pr`, manifest command contract, and workflow implementation
- [ ] 1.2 Document drift points and define target PR behavior contract
- [ ] 1.3 Confirm prompt surface consolidation scope (`ai-pr` vs `pr`)

## Phase 2: Deterministic PR Upsert Path [L]
- [ ] 2.1 Implement existing-PR detection by head branch in workflow path
- [ ] 2.2 Implement append-only update behavior for existing PR descriptions
- [ ] 2.3 Preserve create behavior for new PRs with structured description contract

## Phase 3: Body Reliability Hardening [M]
- [ ] 3.1 Replace fragile inline multiline body handling with file-backed payload path
- [ ] 3.2 Ensure PR update path keeps previous body and appends Additional Changes block

## Phase 4: Validation and Governance Closure [L]
- [ ] 4.1 Add integration tests for PR create vs existing-PR update flow
- [ ] 4.2 Add/adjust provider unit tests for upsert behavior consistency
- [ ] 4.3 Run lint/type/test/governance validations and capture evidence
- [ ] 4.4 Prepare closure artifacts (`done.md`) once acceptance criteria pass
