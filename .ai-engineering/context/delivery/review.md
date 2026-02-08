# Review Criteria and Quality Gates

## Purpose

This document defines **review criteria, PR standards, and quality gates** for the ai-engineering framework. All code changes must meet these standards before merge.

**Last Updated:** 2026-02-08 (Phase 0)

---

## Code Review Checklist

### General Code Quality

- [ ] **Readability:** Code is self-documenting with clear naming
- [ ] **Simplicity:** No unnecessary complexity; YAGNI principle followed
- [ ] **Consistency:** Follows established patterns in codebase
- [ ] **Type Hints:** All functions have type annotations (Python 3.9+ syntax)
- [ ] **Docstrings:** Public functions/classes have docstrings (Google style)
- [ ] **Error Handling:** Appropriate exceptions with clear messages
- [ ] **Security:** No hardcoded secrets, SQL injection, command injection, etc.

### Testing

- [ ] **Test Coverage:** New code has >80% test coverage
- [ ] **Test Quality:** Tests are clear, isolated, and deterministic
- [ ] **Edge Cases:** Common edge cases tested (empty input, None, large values)
- [ ] **Integration Tests:** E2E tests for user-facing features
- [ ] **No Regressions:** All existing tests still pass

### Documentation

- [ ] **README Updated:** If user-facing feature, update README.md
- [ ] **CHANGELOG Updated:** Add entry to CHANGELOG.md (for releases)
- [ ] **API Docs:** If new public API, update docs/
- [ ] **Inline Comments:** Complex logic has explanatory comments (sparingly)

### Performance

- [ ] **Token Efficiency:** Context optimization doesn't degrade token usage
- [ ] **Load Time:** No significant regression in startup/load time
- [ ] **Memory:** No obvious memory leaks or excessive allocations

### Compatibility

- [ ] **Cross-OS:** Works on macOS and Linux (Phase 1); Windows considered (Phase 3)
- [ ] **Python Version:** Compatible with Python 3.9+
- [ ] **Dependencies:** New dependencies justified and minimal

---

## Architecture Review Triggers

Certain changes require **architecture review** before PR approval. Trigger architecture review if PR includes:

### Structural Changes:
- New module or major refactor of existing module
- Changes to data schemas (manifest, state, audit log)
- Changes to ownership model or precedence logic
- New external dependencies (especially for core functionality)

### Security-Sensitive Changes:
- Changes to gate enforcement logic
- Changes to audit logging
- New sensitive operation detection patterns
- Changes to remote skill integrity checking

### User-Facing Changes:
- New commands or command signature changes
- Changes to error messages or user prompts
- Changes to installation/upgrade flow

### Process:
1. PR author adds `architecture-review` label
2. Platform Engineering or Framework Maintainer reviews within 2 business days
3. Review focuses on alignment with discovery/architecture docs
4. Approval required before merge

---

## Security Review Requirements

### Automatic Security Review (Required for):
- Changes to gate enforcement (gate engine, hooks)
- Audit logging modifications
- Sensitive operation detection patterns
- Remote resource fetching (skills, standards)
- Credential handling or storage

### Security Review Checklist:
- [ ] **Input Validation:** All external inputs validated and sanitized
- [ ] **Injection Prevention:** No SQL, command, or code injection vectors
- [ ] **Secret Management:** No secrets in code, logs, or error messages
- [ ] **Audit Trail:** Sensitive operations logged with sufficient detail
- [ ] **Least Privilege:** Code runs with minimal necessary permissions
- [ ] **Secure Defaults:** Default configuration is secure
- [ ] **Dependency Audit:** New dependencies scanned for known vulnerabilities

### Process:
1. PR author adds `security-review` label
2. Security or designated security champion reviews within 3 business days
3. Security approval required before merge

---

## Documentation Review Standards

### User-Facing Documentation (README, Guides):
- [ ] **Clarity:** Non-experts can follow instructions
- [ ] **Completeness:** All steps included, no assumed knowledge
- [ ] **Accuracy:** Tested/validated on fresh environment
- [ ] **Examples:** Realistic examples with expected output
- [ ] **Troubleshooting:** Common issues addressed

### Developer Documentation (API Docs, ADRs):
- [ ] **Up-to-Date:** Reflects current implementation
- [ ] **Rationale:** Explains "why" not just "what"
- [ ] **Trade-offs:** Documents alternatives considered and trade-offs
- [ ] **Versioning:** Version-specific docs for breaking changes

---

## PR Approval Process

### Standard PR (Code Changes):
1. **Author:** Create PR with clear title and description (template provided)
2. **CI/CD:** Automated tests must pass (linting, unit tests, E2E tests)
3. **Reviewer(s):** At least 1 approval required; 2+ for critical modules
4. **Checks:** All checklist items above addressed
5. **Merge:** Squash and merge with clean commit message

### Architecture/Security PR (Flagged):
1. Same as Standard PR above
2. **Additional Approval:** Architecture or Security review as needed
3. **Sign-off:** Explicit approval from designated reviewer
4. **Merge:** After all approvals received

---

## Non-Negotiable Policies

These policies **cannot be overridden** and block merge if violated:

### Security Non-Negotiables:
- ❌ **No secrets in code** (API keys, passwords, tokens)
- ❌ **No bypassing audit logging** for sensitive operations
- ❌ **No weakening of default gate enforcement** without architecture approval
- ❌ **No unauthenticated remote code execution**

### Quality Non-Negotiables:
- ❌ **No merging failing tests** (CI must be green)
- ❌ **No uncovered critical paths** (core logic must have tests)
- ❌ **No breaking changes without migration path** (post-1.0)
- ❌ **No new lint violations** (code must pass ruff checks)

### Process Non-Negotiables:
- ❌ **No direct commits to main** (all changes via PR)
- ❌ **No force-pushing to main** (protected branch)
- ❌ **No merging own PRs** (require external approval)

---

## PR Templates

### Standard PR Template

```markdown
## Summary
[Brief description of what this PR does]

## Motivation
[Why is this change needed? Link to issue/epic if applicable]

## Changes
- [List of key changes]
- [E.g., "Added `ai gate list` command"]

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated (if applicable)
- [ ] Manually tested on [macOS/Linux]

## Checklist
- [ ] Code follows style guide (ruff clean)
- [ ] Tests pass locally
- [ ] Documentation updated (if user-facing)
- [ ] CHANGELOG.md updated (for releases)
- [ ] No breaking changes (or migration path provided)

## Screenshots/Output (if applicable)
[Paste command output or screenshots demonstrating the change]

## Related Issues
Closes #XXX
```

### Architecture Review PR Template

```markdown
[Include all from Standard PR Template above, plus:]

## Architecture Review Needed
**Reason:** [Why architecture review is required]
**Impact:** [What parts of the system are affected]
**Alternatives Considered:** [What other approaches were considered and why this was chosen]
**Trade-offs:** [What are we giving up with this approach]

## Migration Path (if breaking change)
[Step-by-step migration instructions for existing users]

## Backward Compatibility
[How does this affect existing repos using the framework?]
```

---

## Sign-Off Process

### Phase 1 MVP (Pre-1.0):
- **Code Owner:** 1 approval required from framework maintainer
- **Architecture Changes:** Additional approval from tech lead
- **Security Changes:** Additional approval from security champion

### Post-1.0 (Stable):
- **Code Owner:** 2 approvals required
- **Breaking Changes:** 3 approvals + community feedback period (1 week minimum)
- **Security Fixes:** Expedited review (24-hour turnaround)

---

## Quality Gates (CI/CD)

### Pre-Merge Checks (Automated):
1. **Linting:** `ruff check src/ tests/` (must pass)
2. **Type Checking:** `mypy src/` (must pass)
3. **Unit Tests:** `pytest tests/unit/` (must pass, >80% coverage)
4. **Integration Tests:** `pytest tests/integration/` (must pass)
5. **E2E Tests:** `pytest tests/e2e/` (must pass on macOS and Linux)

### Post-Merge Checks:
1. **Dogfooding:** Framework used to manage ai-engineering repo itself
2. **Smoke Tests:** Basic commands run successfully on fresh install
3. **Performance:** Context load time <15s for typical repo (Phase 1 target)

---

## Common Review Feedback Patterns

### Code Smells to Watch For:
- **God Objects/Functions:** Functions >50 lines, classes with too many responsibilities
- **Magic Numbers:** Unexplained constants (use named constants)
- **Premature Optimization:** Complex optimization without profiling data
- **Over-Engineering:** Abstractions for single use case
- **Tight Coupling:** Modules directly importing from each other (use interfaces)

### Documentation Smells:
- **Stale Comments:** Comments that don't match code
- **Obvious Comments:** `i = i + 1  # increment i` (remove)
- **Missing Context:** Complex logic without "why" explanation
- **Unclear Naming:** Variables like `data`, `temp`, `x` (be specific)

---

## Escalation Path

If review is blocked or disputed:

1. **Reviewer and Author:** Discuss in PR comments (async)
2. **If Unresolved:** Schedule sync review meeting (30 min max)
3. **If Still Unresolved:** Escalate to Tech Lead for final decision
4. **If Policy Issue:** Bring to team retrospective for process improvement

---

## Review SLAs

### Target Review Times:
- **Small PRs (<100 lines):** 24 hours
- **Medium PRs (100-500 lines):** 48 hours
- **Large PRs (>500 lines):** 3 business days (consider splitting)

### Expedited Reviews:
- **Security Fixes:** 24 hours
- **Critical Bugs:** 24 hours
- **Blockers:** 24 hours (mark with `urgent` label)

---

## References

- [Discovery Findings](./discovery.md) - Requirements and constraints
- [Architecture Document](./architecture.md) - System design reference
- [Planning Document](./planning.md) - Implementation plan
- [Testing Strategy](./testing.md) - Test requirements
