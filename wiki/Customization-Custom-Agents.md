# Custom Agents

> Create team-specific background workers.

## Overview

Agents are markdown files that define autonomous verification tasks. Custom agents handle team-specific validation needs.

## Location

Custom agents go in `.claude/agents/custom/`:

```
.claude/
└── agents/
    ├── verify-app.md       # Framework agents
    ├── code-architect.md
    ├── oncall-guide.md
    └── custom/             # Your custom agents
        ├── deploy-checker.md
        ├── compliance-scanner.md
        └── perf-analyzer.md
```

The `custom/` directory is never overwritten by framework updates.

## Agent Anatomy

```markdown
---
description: One-line description for agent list
tools: [Bash, Read, Glob, Grep]
---

## Objective
What this agent accomplishes (one sentence).

## Process
1. Step one
2. Step two
3. Step three

## Success Criteria
How to know it completed successfully.

## Constraints
What NOT to do.
```

## Creating a Custom Agent

### Example: Compliance Scanner

**File:** `.claude/agents/custom/compliance-scanner.md`

```markdown
---
description: Scan for compliance violations (GDPR, PCI-DSS, HIPAA)
tools: [Read, Glob, Grep]
---

## Objective
Verify codebase complies with regulatory requirements and flag violations.

## Process

### 1. Identify Compliance Scope
Determine which regulations apply based on:
- `context/compliance.md` (if present)
- File patterns (payment processing, user data, health records)

### 2. GDPR Checks
For code handling personal data:
- [ ] Consent mechanism present
- [ ] Data deletion capability exists
- [ ] Data export functionality available
- [ ] Privacy policy link in UI
- [ ] PII is encrypted at rest

Search patterns:
- `email`, `address`, `phone`, `birthDate`
- `personalData`, `userData`, `customerInfo`

### 3. PCI-DSS Checks
For payment processing code:
- [ ] No credit card numbers in logs
- [ ] Card data encrypted in transit
- [ ] No card data stored locally
- [ ] Tokenization used for storage

Search patterns:
- `creditCard`, `cardNumber`, `cvv`, `expirationDate`
- `paymentMethod`, `billingInfo`

### 4. HIPAA Checks
For health data:
- [ ] PHI is encrypted
- [ ] Access logging present
- [ ] Minimum necessary principle applied

Search patterns:
- `healthRecord`, `medicalHistory`, `diagnosis`
- `patientId`, `healthInfo`

### 5. Report

```markdown
## Compliance Report

**Scan Date:** [date]
**Regulations Checked:** GDPR, PCI-DSS

### Findings

| Regulation | File | Line | Issue | Severity |
|------------|------|------|-------|----------|
| GDPR | user-service.cs | 45 | PII logged without masking | High |
| PCI-DSS | payment.ts | 123 | Card number in error message | Critical |

### Recommendations
1. [Specific fix for each finding]
```

## Success Criteria
- All relevant files scanned
- All applicable regulations checked
- Findings include specific locations and fixes

## Constraints
- Do NOT modify any files
- Do NOT skip any regulation check
- Report ALL findings, even minor ones
```

### Example: Performance Analyzer

**File:** `.claude/agents/custom/perf-analyzer.md`

```markdown
---
description: Analyze code for performance anti-patterns
tools: [Read, Glob, Grep]
---

## Objective
Identify performance issues and optimization opportunities.

## Process

### 1. Database Queries
Check for N+1 queries:
- Loops containing database calls
- Missing `.Include()` or eager loading
- Unbounded `SELECT *` queries

### 2. Memory Patterns
Check for memory issues:
- Large object allocations in loops
- Missing `IDisposable` implementations
- String concatenation in loops (use StringBuilder)

### 3. Async Patterns
Check for blocking calls:
- `.Result` or `.Wait()` on tasks
- Missing `ConfigureAwait(false)` in libraries
- Sync-over-async patterns

### 4. Caching Opportunities
Identify cacheable operations:
- Repeated identical database queries
- Expensive computations with same inputs
- External API calls that could be cached

### 5. Report

```markdown
## Performance Analysis

### Critical Issues
1. **N+1 Query** - `OrderService.cs:45`
   Loading orders in a loop without eager loading

### Optimization Opportunities
1. **Cache Candidate** - `ProductService.cs:78`
   `GetCategories()` called 50+ times per request

### Recommendations
1. Use `.Include(o => o.Items)` for order loading
2. Add 5-minute cache for categories
```

## Success Criteria
- Common anti-patterns checked
- Specific locations provided
- Actionable recommendations

## Constraints
- Read-only analysis
- Focus on high-impact issues
- Provide evidence for each finding
```

## Agent Best Practices

### Single Purpose

Each agent should do one thing well:

```markdown
# Good: Focused
Scan for compliance violations.

# Bad: Too broad
Check security, performance, and compliance.
```

### Read-Only by Default

Most agents should only analyze, not modify:

```markdown
## Constraints
- Do NOT modify any files
- Report findings, don't fix them
```

### Specific Output Format

Define exactly what the report should look like:

```markdown
### Report Format
| Column | Description |
|--------|-------------|
| File | Path to file with issue |
| Line | Line number |
| Issue | Description of problem |
| Severity | Critical/High/Medium/Low |
```

### Error Handling

```markdown
### If Errors Occur
- Report which checks could not complete
- Continue with remaining checks
- Never fail silently
```

## Invoking Custom Agents

```
Run the compliance-scanner agent.
Dispatch perf-analyzer on the order service.
Use deploy-checker before releasing.
```

## Parallel Agents

Run multiple agents simultaneously:

```
Run compliance-scanner and perf-analyzer in parallel.
```

---
**See also:** [Agents Overview](Agents-Overview) | [Custom Skills](Customization-Custom-Skills)
