# oncall-guide Agent

> Guides production incident debugging with structured root cause analysis.

## Purpose

Help diagnose production incidents by analyzing logs, error patterns, and code to identify root cause. Propose fixes with rollback plans.

## When to Use

- Active production incident
- Investigating recurring errors
- Post-incident analysis
- Understanding error patterns

## How to Invoke

```
Run the oncall-guide agent. We're seeing 500 errors on the /api/orders endpoint.
```

```
Use oncall-guide to help debug this production issue: [paste error message]
```

## What It Does

### 1. Gather Incident Context

- Asks for: error messages, stack traces, affected endpoints, timeline, frequency
- Identifies the affected service and stack
- Reads relevant source code for the affected area

### 2. Analyze Error Patterns

- Searches codebase for the error type/message
- Traces the call chain from entry point to error source
- Checks error mapping configuration
- Reviews recent changes: `git log` and `git diff`

### 3. Check Common Causes

| Category | Checks |
|----------|--------|
| **Configuration** | Missing env vars, connection strings |
| **Dependencies** | Failed external calls, timeouts |
| **Data** | Invalid state, missing records, constraints |
| **Deployment** | Version mismatch, missing migrations |
| **Capacity** | Memory pressure, connection pools, rate limits |

### 4. Identify Root Cause

- Presents the most likely root cause with evidence
- Lists supporting evidence
- Rates confidence: High/Medium/Low

### 5. Propose Fix

```markdown
## Incident Analysis

**Root Cause:** [Description]
**Confidence:** High/Medium/Low
**Evidence:**
- [Evidence 1]
- [Evidence 2]

### Immediate Fix
- [What to change and where]
- [Expected impact]

### Rollback Plan
- [How to revert if fix causes issues]
- [Commands to execute]

### Prevention
- [What to add to prevent recurrence]
- [Learning to record with /learn]
```

## Output Format

```markdown
## Incident Analysis: [Brief Description]

**Severity:** Critical/High/Medium/Low
**Affected:** [Endpoints/Services]
**Timeline:** [When it started]

### Root Cause
[Description of the root cause]

**Confidence:** High
**Evidence:**
1. Error message indicates [X]
2. Code at `file:line` shows [Y]
3. Recent commit [SHA] changed [Z]

### Call Chain
```
Request → OrderController.Create (line 45)
       → OrderService.ProcessOrder (line 78)
       → PaymentProvider.Charge (line 123) ← ERROR HERE
       → StripeClient.CreatePaymentIntent
```

### Immediate Fix

**File:** `src/providers/PaymentProvider.cs`
**Line:** 123
**Change:** Add null check for payment method

```csharp
// Before
var paymentIntent = await _stripe.CreatePaymentIntent(request.PaymentMethodId);

// After
if (string.IsNullOrEmpty(request.PaymentMethodId))
{
    return Error.Validation("PaymentMethodId is required");
}
var paymentIntent = await _stripe.CreatePaymentIntent(request.PaymentMethodId);
```

### Rollback Plan

If the fix causes issues:
```bash
git revert [commit-sha]
git push origin main
# Redeploy via CI/CD
```

### Prevention

1. **Test:** Add test for null PaymentMethodId
2. **Validation:** Add request validation in controller
3. **Monitoring:** Add alert for payment failures > 1%
4. **Learning:** Record with `/learn`
```

## Constraints

- Prioritizes speed — this is an active incident
- Does NOT make changes to production without explicit approval
- Does NOT dismiss intermittent errors — they are real
- Always proposes a rollback plan

## Example Run

```
> Run oncall-guide. Getting "Object reference not set" errors on /api/users/profile

## Incident Analysis: NullReferenceException on User Profile

**Severity:** High
**Affected:** GET /api/users/profile
**Timeline:** Started 15 minutes ago

### Root Cause
UserProvider.GetProfile is not handling the case where the user's address is null.

**Confidence:** High
**Evidence:**
1. Stack trace points to `UserProvider.cs:89`
2. Code accesses `user.Address.City` without null check
3. Recent data migration may have set some addresses to null

### Call Chain
```
GET /api/users/profile
  → UserController.GetProfile (line 34)
  → UserProvider.GetProfile (line 89) ← ERROR
    → user.Address.City (Address is null)
```

### Immediate Fix

**File:** `src/providers/UserProvider.cs`
**Line:** 89

```csharp
// Before
City = user.Address.City

// After
City = user.Address?.City ?? string.Empty
```

### Rollback Plan
```bash
git revert HEAD
git push origin main
```

### Prevention
1. Add null checks for all navigation properties
2. Add test: GetProfile_WhenAddressIsNull_ReturnsEmptyAddress
3. /learn "Always null-check navigation properties in EF Core entities"
```

---
**See also:** [Agents Overview](Agents-Overview) | [Security Skills](Skills-Security)
