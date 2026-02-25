# Test Reports

## Test Report Template

```markdown
# Test Report: {Feature Name}

**Date**: YYYY-MM-DD
**Tester**: {Name}
**Version**: {App Version}

## Summary

| Metric | Value |
|--------|-------|
| Total Tests | X |
| Passed | X |
| Failed | X |
| Skipped | X |
| Coverage | X% |

## Test Scope

- [x] Unit tests
- [x] Integration tests
- [x] E2E tests
- [ ] Performance tests
- [ ] Security tests

## Findings

### [CRITICAL] {Issue Title}
- **Location**: src/api/users.ts:45
- **Steps to Reproduce**:
  1. {Step 1}
  2. {Step 2}
- **Expected**: {Should happen}
- **Actual**: {Actually happens}
- **Impact**: {Business/user impact}
- **Fix**: {Recommended solution}

### [HIGH] {Issue Title}
- **Location**: src/services/orders.ts:123
- **Description**: {Details}
- **Impact**: {Business/user impact}
- **Fix**: {Recommended solution}

## Coverage Analysis

| Module | Lines | Branches | Functions |
|--------|-------|----------|-----------|
| api/ | 85% | 78% | 90% |
| services/ | 92% | 85% | 95% |
| utils/ | 100% | 100% | 100% |

### Coverage Gaps
- `src/api/admin.ts` - 0% (no tests)
- `src/services/payment.ts:45-60` - Error handling untested

## Recommendations

1. **Immediate**: {Critical fixes}
2. **High Priority**: {Important improvements}
3. **Medium Priority**: {Additional coverage}

## Sign-off

- [ ] All critical issues addressed
- [ ] Coverage meets threshold
- [ ] Performance meets SLA
```

## Severity Definitions

| Severity | Criteria |
|----------|----------|
| **CRITICAL** | Security vulnerability, data loss, system crash |
| **HIGH** | Major functionality broken, severe performance |
| **MEDIUM** | Feature partially working, workaround exists |
| **LOW** | Minor issue, cosmetic, edge case |
