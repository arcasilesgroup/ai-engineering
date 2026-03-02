# QA Methodology

## Manual Testing Types

### Exploratory Testing

```markdown
**Charter**: Explore {feature} with focus on {aspect}
**Duration**: 60-90 min
**Mission**: Find defects in {specific functionality}

Test Ideas:
- Boundary conditions & edge cases
- Error handling & recovery
- User workflow variations
- Integration points

Findings:
1. [HIGH] {Issue + impact}
2. [MED] {Issue + impact}

Coverage: {Areas explored} | Risks: {Identified risks}
```

### Usability Testing

```markdown
**Task**: Can users complete {action} intuitively?
**Metrics**: Time to complete, errors made, satisfaction (1-5)
**Success**: 80% complete without help in <5 min
```

### Accessibility Testing (WCAG 2.1 AA)

```typescript
test('accessibility compliance', async ({ page }) => {
  await page.keyboard.press('Tab');
  expect(['A', 'BUTTON', 'INPUT']).toContain(
    await page.evaluate(() => document.activeElement.tagName)
  );

  // ARIA labels
  expect(await page.getByRole('button').first().getAttribute('aria-label')).toBeTruthy();

  // Color contrast (axe-core)
  const violations = await page.evaluate(async () => {
    const axe = await import('axe-core');
    return (await axe.run()).violations;
  });
  expect(violations).toHaveLength(0);
});
```

## Test Design Techniques

### Risk-Based Testing

| Risk | Probability | Impact | Priority | Test Effort |
|------|-------------|--------|----------|-------------|
| Critical | High | High | P0 | Exhaustive |
| High | Med-High | High | P1 | Comprehensive |
| Medium | Low-Med | Med | P2 | Standard |
| Low | Low | Low | P3 | Smoke only |

### Defect Root Cause Analysis (5 Whys)

```markdown
1. Why did defect occur? {User input not validated}
2. Why wasn't it validated? {Validation logic missing}
3. Why was it missing? {Requirement unclear}
4. Why was requirement unclear? {Acceptance criteria incomplete}
5. Why incomplete? {No QA review in planning}

**Root Cause**: QA not involved in requirements phase
**Prevention**: Add QA to all planning meetings
```

## Quality Metrics

```typescript
// Defect Removal Efficiency (target: >95%)
const dre = (defectsInTesting / (defectsInTesting + defectsInProd)) * 100;

// Defect Leakage (target: <5%)
const leakage = (defectsInProd / totalDefects) * 100;

// Test Effectiveness (target: >90%)
const effectiveness = (defectsFoundByTests / totalDefects) * 100;
```

## Shift-Left Activities

- Review requirements for testability.
- Create test cases during design.
- TDD: unit tests with code.
- Automated tests in CI pipeline.
- Static analysis on commit.
- Security scanning pre-merge.

**Benefits**: 10x cheaper defect fixes, faster feedback.

### Feedback Cycle Targets

| Stage | Target |
|-------|--------|
| Unit tests | < 5 min (on save) |
| Integration | < 15 min (on commit) |
| E2E | < 30 min (on PR) |
| Regression | < 2 hours (nightly) |

## Quick Reference

| Testing Type | When | Duration |
|--------------|------|----------|
| Exploratory | New features | 60-120 min |
| Usability | UI changes | 2-4 hours |
| Accessibility | Every release | 1-2 hours |
| Localization | Multi-region | 1 day/locale |

| Metric | Excellent | Good | Needs Work |
|--------|-----------|------|------------|
| Coverage | >90% | 70-90% | <70% |
| Leakage | <2% | 2-5% | >5% |
| Automation | >80% | 60-80% | <60% |
| MTTR | <24h | 24-48h | >48h |
