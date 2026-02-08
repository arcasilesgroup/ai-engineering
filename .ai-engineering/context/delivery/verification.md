# Verification Strategy

## Purpose

This document defines the **comprehensive verification strategy** for the ai-engineering framework, including E2E validation matrix, acceptance criteria, and dogfooding validation plan.

**Last Updated:** 2026-02-08 (Phase 0)

---

## E2E Validation Strategy Matrix

### Test Dimensions

The framework must be validated across multiple dimensions to ensure reliability:

| Dimension | Values | Priority |
|-----------|--------|----------|
| **Operating System** | macOS, Linux (Phase 1); Windows (Phase 3) | P0 |
| **Repository State** | Fresh repo, existing .ai-engineering/, migrated ADO/CLAUDE.md | P0 |
| **Git State** | Clean, staged changes, committed changes, merge conflicts | P0 |
| **Network Connectivity** | Online, offline (for remote standards/skills) | P1 |
| **Commands** | All core commands (install, session, gate, standards) | P0 |
| **Gates** | Pre-commit, pre-push, overrides | P0 |
| **Ownership Layers** | Local, repo, team, org, defaults | P1 |

---

## Phase 1 E2E Test Matrix

### Test Suite 1: Installation Scenarios

| Test ID | Scenario | OS | Expected Outcome | Priority |
|---------|----------|----|--------------------|----------|
| E2E-I-001 | Fresh repo, no existing config | macOS | `.ai-engineering/` created, hooks installed, default manifest | P0 |
| E2E-I-002 | Fresh repo, no existing config | Linux | Same as E2E-I-001 | P0 |
| E2E-I-003 | Existing `.azuredevops/ai-engineering.yml` | macOS | Migration prompt, config merged into manifest | P0 |
| E2E-I-004 | Existing `.github/CLAUDE.md` | macOS | Migration prompt, standards extracted | P0 |
| E2E-I-005 | Existing `.ai-engineering/` (re-install) | macOS | Idempotent, no data loss, warns user | P0 |
| E2E-I-006 | Existing git hooks | macOS | Detection, chaining prompt, preserves existing hooks | P1 |
| E2E-I-007 | Non-git directory | macOS | Error message: "Not a git repository" | P0 |

---

### Test Suite 2: Session Management

| Test ID | Scenario | Expected Outcome | Priority |
|---------|----------|-------------------|----------|
| E2E-S-001 | `ai session start` in clean repo | Session created, state/session.json written, context loaded | P0 |
| E2E-S-002 | `ai session status` during active session | Shows session ID, start time, branch, context summary | P0 |
| E2E-S-003 | `ai session end` | Session marked ended, summary logged to history.json | P0 |
| E2E-S-004 | `ai session pause` and `ai session resume` | Session paused, then resumed with same ID and context | P1 |
| E2E-S-005 | Multiple sessions (concurrent) | Error: "Session already active. End or pause first." | P1 |
| E2E-S-006 | `ai history --limit 5` | Shows last 5 sessions with summary stats | P0 |

---

### Test Suite 3: Gate Enforcement

| Test ID | Scenario | Expected Outcome | Priority |
|---------|----------|-------------------|----------|
| E2E-G-001 | `git commit` with staged `.env` file | Pre-commit gate blocks (secret scan) | P0 |
| E2E-G-002 | `git commit` with destructive op in commit msg | Pre-commit gate prompts for approval | P0 |
| E2E-G-003 | `git commit` with clean code | Pre-commit gate passes automatically | P0 |
| E2E-G-004 | `git commit --no-verify` (gate override) | Commit succeeds, override logged in audit.log | P0 |
| E2E-G-005 | `git push --force` detected by pre-push gate | Gate blocks or prompts based on manifest config | P0 |
| E2E-G-006 | `ai gate list` | Shows all configured gates with status | P0 |
| E2E-G-007 | Gate approval with justification | Approval logged with timestamp, user, justification | P0 |

---

### Test Suite 4: Standards Resolution

| Test ID | Scenario | Expected Outcome | Priority |
|---------|----------|-------------------|----------|
| E2E-ST-001 | `ai standards show` with default config only | Shows framework defaults with layer="defaults" | P0 |
| E2E-ST-002 | `ai standards show` with repo + org standards | Shows merged standards with layer attribution | P0 |
| E2E-ST-003 | Local override of org standard | `ai standards show` shows local value takes precedence | P1 |
| E2E-ST-004 | `ai standards diff repo org` | Shows differences between layers (added/changed/removed) | P1 |
| E2E-ST-005 | `ai standards validate` with valid manifest | Validation passes, green check | P0 |
| E2E-ST-006 | `ai standards validate` with invalid YAML | Validation fails with line number and error message | P0 |

---

### Test Suite 5: Context Optimization

| Test ID | Scenario | Expected Outcome | Priority |
|---------|----------|-------------------|----------|
| E2E-C-001 | `ai context show` in small repo (<50 files) | Lists all files to be loaded with token estimate | P0 |
| E2E-C-002 | `ai context show` in large repo (>500 files) | Respects token budget, shows prioritized files | P1 |
| E2E-C-003 | Context load with ignore patterns | Ignored files (node_modules/, *.pyc) excluded | P0 |
| E2E-C-004 | Context load with priority files | Priority files included even if token budget tight | P0 |
| E2E-C-005 | Context load time in typical repo | <15s (Phase 1 target; <10s Phase 2 target) | P1 |

---

### Test Suite 6: Cross-OS Compatibility

| Test ID | Command | macOS | Linux | Windows (Phase 3) | Priority |
|---------|---------|-------|-------|-------------------|----------|
| E2E-X-001 | `ai install` | ✅ | ✅ | 🔲 (deferred) | P0 |
| E2E-X-002 | `ai session start` | ✅ | ✅ | 🔲 | P0 |
| E2E-X-003 | `git commit` (pre-commit gate) | ✅ | ✅ | 🔲 | P0 |
| E2E-X-004 | `ai standards show` | ✅ | ✅ | 🔲 | P0 |
| E2E-X-005 | `ai doctor` | ✅ | ✅ | 🔲 | P0 |

---

### Test Suite 7: Audit Logging

| Test ID | Scenario | Expected Outcome | Priority |
|---------|----------|-------------------|----------|
| E2E-A-001 | Session start/end logged | Audit log contains session lifecycle events | P0 |
| E2E-A-002 | Gate approval logged | Audit log contains gate, user, justification, timestamp | P0 |
| E2E-A-003 | Gate override logged | Audit log contains override event with --no-verify flag | P0 |
| E2E-A-004 | Audit log immutability | Cannot modify/delete audit.log entries (append-only) | P1 |

---

## Module Verification Checklist

### Per-Module Acceptance Criteria

#### CLI Scaffolding (Module 1.1)
- [ ] `ai --version` displays correct version
- [ ] `ai help` shows all commands
- [ ] `ai help <command>` shows command-specific help
- [ ] Unknown command shows helpful error message
- [ ] Exit codes: 0 for success, 1 for errors

#### State Manager (Module 1.2)
- [ ] Session state persisted to `state/session.json`
- [ ] Session history appended to `state/history.json`
- [ ] Atomic file writes (no partial state on crash)
- [ ] Session IDs are unique and sortable (timestamp-based)
- [ ] Status queries return accurate current state

#### Manifest Parser (Module 2.2)
- [ ] Valid YAML loaded without errors
- [ ] Invalid YAML shows clear error with line number
- [ ] Schema validation catches required field omissions
- [ ] Schema validation catches type mismatches
- [ ] Supports comments in YAML

#### Standards Resolver (Module 2.3)
- [ ] Layered precedence correct (local > repo > team > org > defaults)
- [ ] Scalar replacement works (lower layer wins)
- [ ] List extension works (all layers combined)
- [ ] Dict deep merge works (lower layer precedence for conflicts)
- [ ] Caching invalidated on manifest change

#### Installer (Module 2.1)
- [ ] Creates `.ai-engineering/` structure correctly
- [ ] Detects existing ADO config
- [ ] Detects existing CLAUDE.md
- [ ] Migrates detected config to manifest.yml
- [ ] Installs git hooks without errors
- [ ] Idempotent (re-running doesn't break state)

#### Gate Engine (Module 2.4)
- [ ] Detects destructive operations
- [ ] Detects sensitive files (.env, .pem, etc.)
- [ ] Prompts user for approval when required
- [ ] Respects gate override (--no-verify)
- [ ] Logs all gate outcomes to audit log
- [ ] Returns correct exit codes (0=pass, 1=fail)

#### Context Optimizer (Module 3.2)
- [ ] Respects token budget (hard limit)
- [ ] Priority files always included
- [ ] Ignore patterns respected
- [ ] Token estimation within 10% of actual (validated with tiktoken)
- [ ] Caching reduces load time on repeated calls

#### Audit Logger (Module 3.3)
- [ ] Logs appended to `state/audit.log` (JSON Lines format)
- [ ] Each log entry has timestamp, event, user, details
- [ ] File is append-only (no modifications)
- [ ] Logs parseable with standard JSON tools
- [ ] Handles concurrent writes (file locking)

---

## Integration Verification Approach

### End-to-End Workflow Tests

**Workflow 1: New Repo Setup**
```bash
1. Create fresh git repo: `git init test-repo && cd test-repo`
2. Install framework: `ai install`
3. Verify structure: `ls -la .ai-engineering/`
4. Start session: `ai session start`
5. Make changes, commit: `echo "test" > test.txt && git add . && git commit -m "test"`
6. End session: `ai session end`
7. Verify history: `ai history`
8. Verify audit log: `cat .ai-engineering/state/audit.log | jq`

Expected: All steps succeed, audit log contains complete session trail
```

**Workflow 2: Migration from Existing Config**
```bash
1. Create repo with existing .github/CLAUDE.md
2. Run `ai install`
3. Verify migration prompt shown
4. Approve migration
5. Verify manifest.yml contains extracted standards
6. Verify original CLAUDE.md preserved (not deleted)

Expected: Successful migration, no data loss
```

**Workflow 3: Gate Enforcement**
```bash
1. Install framework in test repo
2. Create `.env` file with fake credentials
3. Stage file: `git add .env`
4. Attempt commit: `git commit -m "add env"`
5. Verify gate blocks commit (secret scan)
6. Remove `.env`, commit again
7. Verify commit succeeds

Expected: Gate blocks sensitive file, allows clean commit
```

---

## Dogfooding Validation Plan

### Phase 1: Self-Managed ai-engineering Repo

**Objective:** Use framework to manage its own development from day one

**Validation Steps:**

1. **Install Framework in ai-engineering Repo**
   - Run `ai install` in this repo
   - Verify `.ai-engineering/` structure created (already exists from Phase 0)
   - Merge any existing context with framework-generated manifest

2. **Use Framework for All Development**
   - All commits go through framework gates
   - All sessions logged with `ai session start/end`
   - All standards defined in manifest.yml

3. **Track Dogfooding Metrics**
   - Gate pass rate (target: 85%+)
   - Gate false positive rate (target: <5%)
   - Context load time (target: <15s)
   - Developer friction points (log in learnings.md)

4. **Iterate Based on Dogfooding Feedback**
   - Fix gate false positives immediately
   - Optimize context loading if >15s
   - Improve error messages based on real usage
   - Update docs to clarify confusing workflows

**Success Criteria:**
- [ ] Framework used for 100% of commits in ai-engineering repo (Phase 1)
- [ ] Zero critical bugs blocking daily development
- [ ] Developer satisfaction >3.5/5 (informal survey)
- [ ] All planned features functional in dogfooding context

---

## Performance Validation

### Performance Targets (Phase 1)

| Metric | Target | How to Measure |
|--------|--------|----------------|
| **Install Time** | <30s | Time `ai install` on fresh repo |
| **Context Load Time** | <15s (typical repo) | Time `ai session start` with context loading |
| **Gate Check Time** | <2s (pre-commit) | Time `ai gate pre-commit` on average commit |
| **Session Start Time** | <5s | Time from `ai session start` to ready prompt |
| **Memory Usage** | <100MB | Measure RSS during typical session |

### Performance Test Suite

```bash
# Test 1: Install Time
time ai install

# Test 2: Context Load Time
time ai session start

# Test 3: Gate Check Time
git add .
time ai gate pre-commit

# Test 4: Memory Usage
/usr/bin/time -l ai session start  # macOS
/usr/bin/time -v ai session start  # Linux
```

---

## Regression Testing

### Regression Test Suite

Run before every release to ensure no breaking changes:

```bash
# Run all E2E tests
pytest tests/e2e/ -v

# Run performance benchmarks
pytest tests/performance/ --benchmark-only

# Run cross-OS tests (macOS and Linux)
pytest tests/e2e/ --os=macos
pytest tests/e2e/ --os=linux

# Run security tests
pytest tests/security/ -v
```

### Breaking Change Detection

- [ ] Manifest schema backward compatible (can read old manifests)
- [ ] CLI commands backward compatible (no removed flags)
- [ ] State schema backward compatible (can read old state files)
- [ ] Migration path provided for any breaking changes

---

## Acceptance Criteria (Phase 1 Complete)

### Functional Acceptance:
- [ ] All E2E tests passing (>95% pass rate)
- [ ] All module verification checklists complete
- [ ] Dogfooding validation successful (used daily for 2+ weeks)
- [ ] Cross-OS tests passing (macOS and Linux)

### Performance Acceptance:
- [ ] All performance targets met
- [ ] No regressions from baseline
- [ ] Memory usage within limits

### Quality Acceptance:
- [ ] Test coverage >80% overall
- [ ] Zero critical bugs open
- [ ] Security review passed
- [ ] Documentation complete and validated

---

## References

- [Planning Document](./planning.md) - Implementation plan
- [Architecture Document](./architecture.md) - System design
- [Testing Strategy](./testing.md) - Test approach
- [Review Criteria](./review.md) - Quality gates
