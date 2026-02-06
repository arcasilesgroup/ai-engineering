# Production Reliability Workflow

> The Boris Cherny workflow that transforms Claude from a code generator into a reliable engineering partner.

## The Core Problem

AI coding agents are powerful but unreliable without structure. They:
- Say "should work" without verifying
- Make architectural decisions silently
- Don't search for existing patterns
- Skip verification steps

The Production Reliability Workflow fixes this with 6 practices.

## Practice 1: Verification Protocol

**Never trust "should work." Always verify with exact commands.**

### Per-Stack Verification

**.NET:**
```bash
dotnet build --no-restore
dotnet test --no-build --verbosity normal
dotnet format --verify-no-changes
```

**TypeScript:**
```bash
npx tsc --noEmit
npm test
npx eslint .
```

**Python:**
```bash
pytest
ruff check .
mypy .
```

**Terraform:**
```bash
terraform fmt -check
terraform validate
terraform plan
```

### Example

Instead of:
> "I've updated the service. The tests should still pass."

Do this:
> "I've updated the service. Running verification:
> `dotnet build` -- passed
> `dotnet test` -- 42 passed, 0 failed
> `dotnet format --verify-no-changes` -- no changes needed"

## Practice 2: Reconnaissance Before Writing

**Before writing new code, ALWAYS search for existing patterns.**

### The Process

1. Search for 2+ similar examples in the codebase
2. Read the relevant standards file
3. Read the relevant learnings file
4. Explain the pattern you found
5. Implement following that pattern

### Example

Instead of:
> "I'll create a new provider class."

Do this:
> "I found 3 existing providers: OrderProvider, UserProvider, PaymentProvider. They all follow this pattern:
> - Interface with Result<T> return types
> - Constructor injection of services
> - IsError check before Value access
> I'll follow the same pattern for the new provider."

## Practice 3: Two Options for High Stakes

**For significant decisions, never choose silently.**

### When to Use

- Architecture changes
- New external dependencies
- Data model changes
- Performance-critical paths
- API contract changes

### Format

| | Option A | Option B |
|---|----------|----------|
| Approach | [description] | [description] |
| Pros | [list] | [list] |
| Cons | [list] | [list] |
| Risk | Low/Medium/High | Low/Medium/High |
| Files | X affected | Y affected |
| Reversibility | Easy/Moderate/Difficult | Easy/Moderate/Difficult |

Recommend one. Wait for approval.

## Practice 4: Danger Zones

**Some areas require extra caution.**

| Zone | Risk | Rules |
|------|------|-------|
| **Authentication** | Security breach | Never bypass auth. Test both paths. |
| **Database Migrations** | Data loss | Always reversible. Test rollback. |
| **Payment/Billing** | Financial loss | Idempotency required. Log everything. |
| **Permissions/RBAC** | Privilege escalation | Default deny. Test every role. |
| **Configuration** | Outages | Never hardcode. Validate at startup. |
| **API Contracts** | Breaking clients | Version the API. Never remove fields. |
| **CI/CD Pipelines** | Broken deploys | Test in branch first. |

When working in a danger zone:
1. Read the full context first
2. Run `/assess impact`
3. Use Two Options
4. Verify thoroughly

## Practice 5: Layered Memory

**Three tiers of context, loaded in order:**

| Layer | File | Who Maintains |
|-------|------|--------------|
| Global | `~/.claude/CLAUDE.md` | You (personal) |
| Project | `./CLAUDE.md` | Team (committed) |
| Personal | `./CLAUDE.local.md` | You (not committed) |

### Tips

- Put sprint context in `CLAUDE.local.md`
- Put personal preferences in `~/.claude/CLAUDE.md`
- Use `/learn` to record project learnings

## Practice 6: The Reliability Template

**For non-trivial tasks:**

1. **Goal** - What are you trying to achieve?
2. **Constraints** - What must not break?
3. **Reconnaissance** - Search for existing patterns
4. **Plan** - Outline steps. For high stakes: Two Options.
5. **Wait** - Get approval (high stakes only)
6. **Implement** - Follow the plan and patterns
7. **Verify** - Run the Verification Protocol
8. **Summarize** - Report what changed

## The Complete Loop

```
1. Receive a task
2. Reconnaissance → search patterns, read standards, read learnings
3. Plan → outline steps, identify danger zones
4. If high stakes → Two Options → wait for approval
5. Implement → follow existing patterns
6. Verify → run exact commands per stack
7. Summarize → report what was done
```

This is the loop that makes AI coding reliable for production code.

---
**See also:** [Standards Overview](Standards-Overview) | [Agents Overview](Agents-Overview)
