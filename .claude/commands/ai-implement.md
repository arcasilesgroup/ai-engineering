# /ai-implement — Implementation Workflow

This skill defines the step-by-step workflow for implementing a feature, fix, or change in a codebase. It enforces the framework's core principles: search before you write, plan before you act, work in tiny iterations, and verify with real commands. No guessing, no big-bang changes, no untested code.

---

## Session Preamble (execute silently)

Before any user-visible action, silently internalize project context:

1. Read `.ai-engineering/knowledge/learnings.md` — lessons learned during development
2. Read `.ai-engineering/knowledge/patterns.md` — established conventions
3. Read `.ai-engineering/knowledge/anti-patterns.md` — known mistakes to avoid
4. Detect the project stack from package.json, .csproj, pyproject.toml, or equivalent
5. Identify the current branch and working tree state

Do not report this step to the user. Internalize it as context for decision-making.

---

## Trigger

- User invokes `/ai-implement`
- User says "implement this", "build this feature", "make this change", or provides a specific implementation request with sufficient detail

---

## Specification Gate

BEFORE writing or modifying ANY code:

1. Document what you will do (max 5 bullets)
2. List files to be created or modified
3. List potential risks
4. Present to the user for approval

**Do NOT proceed until you receive explicit approval.** This is a hard gate.

---

## Prerequisites

Before starting, verify:

- The current directory is a project with recognizable structure (has a build system, source directory, or project file).
- The build system works: run a quick sanity check (`npm run build`, `dotnet build`, `cargo build`, or equivalent). If the project does not build before we start, we need to know that upfront.
- The current branch is appropriate for this work (not a protected branch, ideally a feature branch).

If any prerequisite fails, report it and ask the user how to proceed before writing any code.

---

## Step 1: Understand the Requirement

Before writing a single line of code, fully understand what is being asked.

### If an issue/ticket is referenced:

```bash
# GitHub issue
gh issue view <issue-number> --json title,body,labels,assignees,comments

# Or read from the user's description
```

### Clarification Checklist

- **What** is the expected behavior or outcome?
- **Why** is this change needed? (Business context, bug report, user request)
- **Who** is affected? (End users, other developers, CI systems)
- **Where** in the system does this change live? (Which modules, services, layers)
- **What are the acceptance criteria?** If none are provided, propose them and get confirmation.
- **What are the boundaries?** What is explicitly out of scope?

### Output

State your understanding back to the user:

```
My understanding of the requirement:
  What: Add rate limiting to the /api/search endpoint
  Why: Production logs show abuse — 50+ requests/second from single IPs
  Acceptance criteria:
    - Rate limit of 30 requests per minute per IP
    - Returns 429 Too Many Requests when exceeded
    - Rate limit headers in all responses (X-RateLimit-*)
    - Configurable via environment variables
  Out of scope: Rate limiting for authenticated endpoints (separate ticket)

Is this correct? [y/N]
```

Do not proceed until the user confirms the understanding is correct.

---

## Step 2: Search the Codebase

Before creating anything new, search for existing patterns, related code, and similar implementations.

### Search Checklist

- **Existing implementations:** Has something similar been built before? Search for related function names, file names, and concepts.
- **Patterns in use:** How does the codebase handle similar concerns? (middleware, decorators, interceptors, etc.)
- **Naming conventions:** What naming patterns does the project use for this type of code?
- **Configuration patterns:** How does the project handle configurable values? (env vars, config files, feature flags)
- **Test patterns:** How are similar features tested? What test utilities exist?
- **Dependencies:** Are there existing libraries in the project that handle this concern? (e.g., an existing rate limiter package already installed but unused)

### Commands

```bash
# Search for related code
grep -r "rate.limit\|rateLimit\|throttle" --include="*.ts" --include="*.js" src/
grep -r "middleware" --include="*.ts" src/

# Search for existing patterns
find src/ -name "*middleware*" -o -name "*interceptor*" -o -name "*guard*"

# Check existing dependencies
cat package.json | grep -i "rate\|throttle\|limit"

# Review similar implementations
cat src/middleware/auth.ts  # See how middleware is structured
```

### Output

Report findings:

```
Codebase search results:
  Existing rate limiting: None found
  Middleware pattern: Express middleware in src/middleware/*.ts, registered in src/app.ts
  Similar middleware: src/middleware/auth.ts, src/middleware/cors.ts — follow this pattern
  Configuration: Environment variables loaded via src/config/env.ts
  Test pattern: src/middleware/__tests__/auth.test.ts — uses supertest for HTTP tests
  Dependencies: No rate limiting package installed

  Plan will follow the existing middleware pattern.
```

---

## Step 3: Plan the Approach

Based on the requirement and codebase analysis, produce a concrete implementation plan.

### Plan Structure

```
Implementation Plan
───────────────────
Approach: Create Express middleware using sliding window rate limiting

Files to create:
  1. src/middleware/rate-limiter.ts — rate limiting middleware
  2. src/middleware/__tests__/rate-limiter.test.ts — unit and integration tests

Files to modify:
  3. src/config/env.ts — add RATE_LIMIT_* environment variables
  4. src/app.ts — register rate limiter middleware
  5. .env.example — document new environment variables

Dependencies:
  None — implementing with in-memory Map + sliding window (no external package needed)

Risks:
  - In-memory storage means rate limits reset on server restart
  - Not suitable for multi-instance deployments without a shared store (Redis)
  - Documented as known limitation; Redis adapter is a follow-up task

Phases:
  Phase 1: Core rate limiter logic + unit tests
  Phase 2: Middleware wrapper + integration tests
  Phase 3: Configuration + registration + .env.example update

Estimated scope: ~150 lines of code, ~200 lines of tests
```

### Rules

- If the plan involves more than 5 files, break it into phases of 3-5 files each.
- Every file creation or modification must have a stated purpose.
- Risks and limitations must be called out explicitly.
- Dependencies must be justified. Do not add a package if the implementation is straightforward without one.

### Approval

Present the plan and wait for user confirmation:

```
Proceed with this plan? [y/N]
You can also ask me to adjust the approach before starting.
```

Do not write any code until the plan is approved.

---

## Step 4: Present Plan for User Approval

This is a deliberate gate. The plan from Step 3 must be explicitly approved before any implementation begins.

### Approval Responses

- **"Yes" / "Proceed" / "Looks good":** Begin implementation at Step 5.
- **"Change X":** Revise the plan based on feedback and re-present.
- **"I have questions":** Answer questions, then re-present for approval.
- **"No" / "Stop":** Abort the workflow cleanly.

If the user asks to skip the plan ("just do it"), push back once:

```
I can start immediately, but a 30-second review of the plan catches issues
that cost hours to fix later. Here's the quick version: [abbreviated plan].
Proceed? [y/N]
```

If they insist, proceed — but keep the plan in your own working memory for structure.

---

## Step 5: Implement in Tiny Iterations

Execute the plan one logical change at a time. Each iteration follows this cycle:

### Parallel Task Identification

Before starting, identify which tasks can run in parallel:

```
PARALLELIZABLE — the following can be done simultaneously:
- [ ] Create types/interfaces
- [ ] Prepare test skeletons
- [ ] Configure imports/dependencies

SEQUENTIAL — these must be done in order:
- [ ] Core implementation (depends on types)
- [ ] Integration wiring (depends on core)
- [ ] Full test implementation (depends on integration)
```

### Context Isolation Rule

Do NOT mix implementation with refactoring. If you discover code that needs refactoring during implementation:

1. Note it in a separate list
2. Complete the current implementation first
3. Propose the refactoring as a separate commit

### Micro-Iteration Rule

Do not write more than 50 lines of code without verifying compilation. After every meaningful change:

1. Save the file
2. Run the type checker / compiler
3. Fix any errors before continuing

This prevents compounding errors that are harder to debug in bulk.

### Iteration Cycle

1. **State what you are doing:** "Creating the rate limiter core logic in `src/middleware/rate-limiter.ts`."
2. **Read before write:** If modifying an existing file, read it first. Understand its structure, imports, and conventions.
3. **Make one change:** Create or modify a single file (or a tightly coupled pair like implementation + test).
4. **Keep changes small:** Each iteration should be 20-80 lines of meaningful code. If a single change exceeds 100 lines, it is probably doing too much — split it.
5. **Follow existing patterns:** Match the project's naming, structure, error handling, and import style exactly.

### Anti-Patterns (Do NOT Do These)

- Do not write all files at once and hope they work together.
- Do not create a file without reading related files first.
- Do not invent new patterns when the project has established ones.
- Do not add placeholder code ("TODO: implement this later") unless explicitly agreed in the plan.
- Do not over-engineer. Build what was asked for, not what might be needed someday.
- Do not make unrelated changes. If you notice something else that should be fixed, note it separately — do not fix it now.

---

## Step 6: Verify After Each Change

After each iteration in Step 5, run the appropriate verification:

### Verification Commands

```bash
# Does it compile / parse?
npx tsc --noEmit           # TypeScript
dotnet build               # .NET
cargo check                # Rust
python -m py_compile <file> # Python

# Does it pass lint?
npx eslint <changed-files>
ruff check <changed-files>

# If tests were written in this iteration, do they pass?
npx vitest run <test-file>
pytest <test-file>
dotnet test --filter <test-class>
```

### Rules

- If the verification fails: **stop and fix before continuing**. Do not proceed to the next iteration with broken code.
- Report the verification result: "Compiled successfully. Lint passed. Tests: 4 passed, 0 failed."
- If a failure is in code you did not write (pre-existing issue), note it clearly and ask the user whether to fix it or work around it.

---

## Step 7: Write and Update Tests

After the core implementation is complete, ensure test coverage is thorough.

### Testing Requirements

- **Every new function** must have at least one test covering the happy path.
- **Every error path** must have a test that triggers it (invalid input, missing config, timeout, etc.).
- **Edge cases** must be tested: empty inputs, null values, boundary values, concurrent access.
- **Integration points** must be tested: middleware registration, API endpoint behavior, database queries.

### Test Structure

Follow the project's existing test conventions. If no convention exists, use:

```
describe('<module or function name>', () => {
  describe('<method or scenario>', () => {
    it('should <expected behavior> when <condition>', () => {
      // Arrange
      // Act
      // Assert
    });
  });
});
```

### Test Quality Checks

- Tests must be deterministic (no flaky tests).
- Tests must be independent (no test depends on another test's side effects).
- Tests must clean up after themselves (no shared mutable state between tests).
- Tests must have descriptive names that explain what they verify, not how.

---

## Step 8: Run Full Verification

After all implementation and tests are complete, run the full project verification suite:

```bash
# Full build
npm run build / dotnet build / cargo build

# Full lint
npm run lint / dotnet format --verify-no-changes / ruff check .

# Full type check
npx tsc --noEmit / mypy . / cargo check

# Full test suite
npm test / dotnet test / pytest / cargo test
```

### Handling Failures

- **Build failure:** Fix immediately. This is a blocking issue.
- **Lint failure in your code:** Fix immediately.
- **Lint failure in other code:** Report it but do not fix it (minimal changes principle).
- **Type check failure in your code:** Fix immediately.
- **Test failure in your tests:** Fix immediately.
- **Test failure in other tests:** Report it. Investigate whether your change caused it. If yes, fix. If no, report as pre-existing.

All verification must pass before proceeding to Step 9.

---

## Step 9: Produce Change Summary

After all verification passes, produce a structured summary of everything that was done:

```
Implementation Summary
──────────────────────
Requirement: Add rate limiting to /api/search endpoint (Issue #234)

Files created:
  src/middleware/rate-limiter.ts — sliding window rate limiter (62 lines)
  src/middleware/__tests__/rate-limiter.test.ts — 12 tests (148 lines)

Files modified:
  src/config/env.ts — added RATE_LIMIT_WINDOW_MS, RATE_LIMIT_MAX_REQUESTS (+8 lines)
  src/app.ts — registered rate limiter middleware (+3 lines)
  .env.example — documented new environment variables (+4 lines)

Verification:
  Build: PASS
  Lint: PASS
  Type check: PASS
  Tests: 147 passed (12 new), 0 failed

Known limitations:
  - In-memory storage; not suitable for multi-instance without shared store
  - Follow-up: Redis adapter (tracked separately)

Ready for: commit and code review
```

---

## Rules and Constraints

### Hard Rules

- Never skip the planning phase. Even "quick fixes" get a lightweight plan.
- Never make changes that are out of scope, even if they seem like improvements.
- Never commit during implementation. The user decides when to commit (use `/ai-commit`).
- Never push during implementation. Pushing is a separate action.
- Never modify test fixtures or test data that other tests depend on without understanding the impact.
- Never ignore test failures. Every failure is investigated.

### Soft Guidelines

- Prefer modifying existing files over creating new ones when the change logically belongs in an existing file.
- Prefer smaller, focused files over large files when creating new code.
- Prefer composition over inheritance.
- Prefer explicit over implicit.
- When in doubt, ask the user rather than making assumptions.

---

## Error Recovery

| Failure                                      | Action                                                                                        |
| -------------------------------------------- | --------------------------------------------------------------------------------------------- |
| Cannot understand requirement                | Ask clarifying questions. Do not guess.                                                       |
| Codebase search finds nothing relevant       | Note the absence. Ask if the user expects existing patterns.                                  |
| Plan is rejected                             | Revise based on feedback and re-present.                                                      |
| Build breaks during iteration                | Stop. Fix. Verify. Then continue.                                                             |
| Tests fail after implementation              | Investigate root cause. Fix your code or your tests. Report pre-existing failures separately. |
| Full verification fails                      | Fix all issues before producing the summary.                                                  |
| User changes requirements mid-implementation | Stop current work. Re-do Steps 1-4 with updated requirements. Resume from Step 5.             |

---

## Implementation Checklist (verify before declaring done)

Before producing the final summary, verify every item:

- [ ] All new tests pass
- [ ] No lint warnings introduced
- [ ] No new `any` types introduced (TypeScript)
- [ ] Edge cases covered in tests
- [ ] Public API documentation updated if interfaces changed
- [ ] No unrelated changes included
- [ ] Build succeeds from clean state

If any item fails, fix it before proceeding to the summary.

---

## Learning Capture (on completion)

If during execution you discovered something useful for the project:

1. **New pattern** (e.g., discovered a useful abstraction, found a good testing approach) → Propose adding to `knowledge/patterns.md`
2. **Recurring error** (e.g., common mistake when working with a specific module) → Propose adding to `knowledge/anti-patterns.md`
3. **Lesson learned** (e.g., dependency quirk, configuration gotcha) → Propose adding to `knowledge/learnings.md`

Ask the user before writing to these files. Never modify them silently.

---

## What This Skill Does NOT Do

- It does not commit code. Use `/ai-commit-push` when ready.
- It does not create pull requests. Use `/ai-commit-push-pr` when ready.
- It does not deploy code. Deployment is a separate pipeline.
- It does not make architectural decisions. It follows existing patterns and asks when patterns are unclear.
- It does not refactor unrelated code. Scope discipline is absolute.
