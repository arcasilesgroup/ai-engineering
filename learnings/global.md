# Global Learnings

This file captures cross-cutting learnings that apply across all technology stacks.

## Format

Each learning follows this structure:

```markdown
### [Date] Learning Title

**Context:** Brief description of when this applies
**Learning:** What was learned
**Rationale:** Why this matters
**Examples:** If applicable
```

---

## Learnings

### [2024-01] Result Pattern is Non-Negotiable

**Context:** All business logic in providers and services
**Learning:** Always use Result<T> for operations that can fail, never exceptions for flow control
**Rationale:** Provides explicit error handling, composable operations, and clear API contracts
**Examples:** See `.ai/standards/dotnet/patterns/result-pattern.md`

---

### [2024-01] ADRs for Architectural Decisions

**Context:** When making decisions that affect system architecture or have long-term implications
**Learning:** Create an ADR before implementing significant architectural changes
**Rationale:** Documents the "why" behind decisions, helps future maintainers understand context

---

### [2024-01] Test Data Should Use Relative Dates

**Context:** Unit tests that depend on current time
**Learning:** Use dynamic relative dates (`DateTime.UtcNow.AddDays(75)`) over fixed dates or time abstractions
**Rationale:** Keeps tests simple, time-independent, and avoids modifying production code

---

### [2024-02] Separate Request/Response DTOs for External Services

**Context:** HTTP client integrations with external services
**Learning:** 
- Requests: Use `required` members for compile-time enforcement
- Responses: Use nullable properties to prevent deserialization failures
**Rationale:** Request models should enforce what we send; response models should be lenient about what we receive

---

### [2024-02] Lambda Parameters in Bind Operations

**Context:** Using `.Bind()` with Result pattern
**Learning:** Always declare the lambda parameter even if unused (`version =>` not `_ =>`)
**Rationale:** Required for compiler to infer generic types correctly in overload resolution

---

## Adding New Learnings

When a pattern or insight emerges from development work:

1. Determine if it's stack-specific or cross-cutting
2. If cross-cutting, add here; otherwise add to appropriate `by-stack/*.md`
3. Include date for temporal context
4. Keep format consistent
5. Update related documentation if needed

## Integration with copilot-instructions.md

Significant learnings should be added to the `Learnings` section in `.github/copilot-instructions.md` for AI assistant awareness.
