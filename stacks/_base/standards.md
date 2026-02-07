# Universal Coding Standards

These standards apply to every technology stack. They define the baseline expectations for all code written or modified by AI assistants and human engineers alike. When a stack-specific standard conflicts with a universal one, the stack-specific standard takes precedence.

---

## Code Quality Principles

### Readability Is Non-Negotiable

Code is read far more often than it is written. Optimize for the reader, not the writer.

- Write code that a competent engineer unfamiliar with the project can understand within 60 seconds of reading a function.
- Avoid clever tricks, obscure operators, and implicit behavior. Explicit is better than implicit.
- Use vertical whitespace deliberately to separate logical blocks within a function.
- Keep related code close together. If two pieces of logic are always modified together, they belong near each other.

### Simplicity Over Abstraction

- Do not introduce an abstraction until a pattern has repeated at least three times (Rule of Three).
- Prefer flat code over deeply nested code. If a function has more than 3 levels of nesting, refactor it.
- Prefer composition over inheritance in all cases unless the language idiom strongly favors inheritance.
- When choosing between a simple solution that is slightly repetitive and a clever solution that is DRY but hard to follow, choose the simple solution.
- Avoid "clever" code that relies on operator precedence, short-circuit tricks, or language-specific quirks for core logic. Save cleverness for performance-critical hot paths where the trade-off is justified and documented.

```
// DON'T — clever but opaque
const name = user?.profile?.name || (config.defaults && config.defaults[role]) || "Unknown";

// DO — clear and traceable
let name = "Unknown";
if (user?.profile?.name) {
  name = user.profile.name;
} else if (config.defaults?.[role]) {
  name = config.defaults[role];
}
```

### DRY — But Not at the Cost of Clarity

- Extract repeated logic into named functions or constants when the same logic appears 3+ times.
- Do NOT extract code into a shared utility just because two pieces of code happen to look similar. They must share the same reason to change.
- Duplication is far cheaper than the wrong abstraction. If extracting creates coupling between unrelated modules, keep the duplication.
- When you do extract, name the shared function after *what it does*, not *where it is used*. `formatCurrency` is reusable; `formatPriceForCheckoutPage` is not.

### SOLID Principles

- **Single Responsibility**: Every module, class, or function should have one reason to change. If you cannot describe what it does in one sentence without using "and," split it.
- **Open/Closed**: Design modules so new behavior can be added without modifying existing code. Use interfaces, plugins, or configuration — not conditional branches.
- **Liskov Substitution**: Subtypes must be usable wherever their parent type is expected without breaking behavior.
- **Interface Segregation**: Do not force consumers to depend on methods they do not use. Prefer small, focused interfaces over large, general ones.
- **Dependency Inversion**: High-level modules should depend on abstractions, not on low-level implementation details. Inject dependencies rather than instantiating them directly.

---

## Naming Conventions

### General Rules

- Names must be descriptive and unambiguous. A reader should understand the purpose without reading the implementation.
- Do not abbreviate unless the abbreviation is universally understood within the domain (e.g., `url`, `id`, `http`, `db`).
- Avoid single-letter variable names except for loop counters (`i`, `j`, `k`) and lambda/closure parameters where the context makes the meaning obvious.
- Boolean variables and functions must read as a yes/no question: `isActive`, `hasPermission`, `canRetry`, `shouldValidate`.

### Variables

- Use `camelCase` for variables and function parameters (unless the language convention differs, e.g., `snake_case` in Python/Ruby).
- Constants use `UPPER_SNAKE_CASE`.
- Avoid generic names like `data`, `info`, `temp`, `result`, `value`, `item` unless narrowly scoped (under 5 lines).

```
// DON'T
const d = getUsers();
const temp = processData(d);

// DO
const activeUsers = getActiveUsers();
const enrichedProfiles = enrichUserProfiles(activeUsers);
```

### Functions and Methods

- Name functions with a verb that describes the action: `fetchUser`, `calculateTotal`, `validateEmail`, `sendNotification`.
- Functions that return booleans start with `is`, `has`, `can`, `should`, or `was`.
- Event handler functions use `on` or `handle` prefix: `onSubmit`, `handleClick`, `onUserCreated`.
- Avoid vague verbs: `process`, `handle`, `manage`, `do`. Be specific about what the function does.

```
// DON'T
function handleData(input) { ... }

// DO
function parseCSVToUserRecords(csvContent) { ... }
```

### Classes, Types, and Interfaces

- Classes and types use `PascalCase`.
- Interfaces should describe a capability or contract, not just mirror a class name. Prefer `Serializable`, `Cacheable`, `UserRepository` over `IUser`.
- Do not prefix interfaces with `I` unless the language convention mandates it (e.g., C# does, TypeScript does not).
- Enums use `PascalCase` for the type and `UPPER_SNAKE_CASE` for values.

### Files and Directories

- File names must match the primary export or class they contain.
- Use `kebab-case` for file names unless the language convention differs (e.g., `PascalCase` for React components, `snake_case` for Python modules).
- Group files by feature or domain, not by technical role (e.g., prefer `users/controller.ts` over `controllers/user-controller.ts`).
- Index files (`index.ts`, `__init__.py`) should only re-export. They must contain zero business logic.

---

## Code Organization

### File Size

- A single file should not exceed 300 lines of code (excluding imports and comments). If it does, find a natural boundary to split.
- If a file contains more than one public class or more than 5 public functions, it is doing too much.

### Function Length

- A function should fit on one screen (~40 lines). If it does not, extract sub-operations into well-named helper functions.
- A function should do one thing. If the function name requires "and" to describe it, split it.
- Aim for functions with 3 or fewer parameters. If a function takes more than 4 parameters, group them into a configuration object or struct.

### Complexity

- Cyclomatic complexity per function should not exceed 10. Refactor complex conditionals into guard clauses, early returns, or lookup tables.
- Avoid deeply nested callbacks. Use async/await, promises, or equivalent language patterns.
- Replace complex `if/else if/else if` chains with strategy patterns, maps, or switch statements.

```
// DON'T
function getDiscount(userType) {
  if (userType === 'premium') {
    return 0.2;
  } else if (userType === 'member') {
    return 0.1;
  } else if (userType === 'trial') {
    return 0.05;
  } else {
    return 0;
  }
}

// DO
const DISCOUNT_BY_USER_TYPE = {
  premium: 0.2,
  member: 0.1,
  trial: 0.05,
};

function getDiscount(userType) {
  return DISCOUNT_BY_USER_TYPE[userType] ?? 0;
}
```

### Module Boundaries

- Each module should have a clear public API and hide its implementation details. Consumers should interact with the module through its public interface, not reach into its internals.
- Avoid god modules — if a module is imported by more than half the codebase, it is likely doing too much. Split it by responsibility.
- Keep coupling low between modules. A change in module A should rarely require changes in module B. If it does, the boundary is in the wrong place.

### Imports and Dependencies

- Sort imports in a consistent order: standard library, external packages, internal modules, relative imports.
- Separate import groups with a blank line for visual clarity.
- Never import an entire module when you only use one function. Use named/selective imports.
- Avoid circular dependencies. If module A imports from B and B imports from A, extract the shared logic into a third module C.

```
// DON'T — unorganized imports
import { validateEmail } from './utils';
import express from 'express';
import { UserService } from '../services/user';
import fs from 'fs';
import { logger } from './logger';
import cors from 'cors';

// DO — grouped and ordered
import fs from 'fs';

import cors from 'cors';
import express from 'express';

import { UserService } from '../services/user';

import { logger } from './logger';
import { validateEmail } from './utils';
```

---

## Error Handling

### Principles

- Never swallow errors silently. Every catch/except block must either handle the error meaningfully, re-throw it, or log it with sufficient context.
- Use typed/specific errors over generic ones. Catch the narrowest exception type possible.
- Fail fast: validate inputs at the boundary and reject invalid data immediately rather than letting it propagate deep into the system.
- Distinguish between expected errors (validation failures, not-found) and unexpected errors (null pointers, connection timeouts). Handle them differently.

### Patterns

- Use guard clauses and early returns to handle error cases first, keeping the happy path un-indented.
- Return result types (e.g., `Result<T, E>`, `Either`) rather than throwing exceptions in contexts where errors are expected and frequent.
- Always include context in error messages: what operation failed, what input caused it, and what the caller should do about it.

```
// DON'T
throw new Error("Failed");

// DO
throw new ValidationError(
  `Failed to parse date from field "startDate": received "${rawValue}". Expected ISO 8601 format (YYYY-MM-DD).`
);
```

- Never use exceptions for control flow. Exceptions are for exceptional circumstances, not for branching logic.
- Clean up resources in `finally` blocks, `defer` statements, or language-equivalent constructs. Never rely on the happy path for cleanup.

### Error Hierarchy

- Define a project-level error hierarchy. At minimum, distinguish between:
  - **Operational errors**: Expected problems that the system can handle (network timeout, invalid input, resource not found). These are part of normal operation.
  - **Programmer errors**: Bugs in the code (null dereference, type error, assertion failure). These indicate code that needs fixing.
- Operational errors should be caught and handled gracefully (retry, fallback, user message). Programmer errors should crash loudly and be fixed immediately.
- Use custom error classes that carry structured context (error code, HTTP status, user-facing message, internal details) rather than passing strings around.

```
// DON'T — generic error with no context
catch (err) {
  console.log(err);
  return res.status(500).send("Error");
}

// DO — structured error handling
catch (err) {
  if (err instanceof NotFoundError) {
    return res.status(404).json({ error: { code: "NOT_FOUND", message: err.userMessage } });
  }
  logger.error({ err, requestId: req.id, operation: "fetchUser" });
  return res.status(500).json({ error: { code: "INTERNAL_ERROR", message: "An unexpected error occurred." } });
}
```

---

## Documentation

### When to Document

- **Public APIs**: Every public function, method, class, or module must have a doc comment explaining what it does, its parameters, its return value, and any exceptions it throws.
- **Why, not what**: Document the reasoning behind non-obvious decisions. If the code is clear about *what* it does, a comment explaining *what* is redundant. Explain *why*.
- **Workarounds and hacks**: If code works around a bug, references an external issue, or uses a non-obvious approach, leave a comment with a link or explanation.
- **Configuration**: Document all configuration options, their valid values, defaults, and effects.
- **Complex algorithms**: If a function implements a non-trivial algorithm, link to the source (paper, RFC, design doc) and summarize the approach.

### When NOT to Document

- Do not add comments that restate what the code already says. `// increment counter` above `counter++` is noise.
- Do not use comments as a substitute for good naming. If you need a comment to explain what a variable is, rename the variable.
- Do not leave commented-out code in the codebase. Delete it. Version control exists for a reason.
- Do not write TODO comments without an associated ticket or issue number. `// TODO: fix this` is not actionable. `// TODO(PROJ-1234): handle pagination` is.

### Documentation Formats

- Use the documentation format standard for your language: JSDoc for JavaScript/TypeScript, docstrings for Python, GoDoc for Go, Javadoc for Java, `///` for Rust.
- Include parameter types and descriptions, return types, and thrown exceptions in doc comments.
- For REST APIs, maintain an OpenAPI/Swagger specification. Keep it in sync with the implementation — automated generation is preferred.

```
/**
 * Calculates the shipping cost for an order based on destination and weight.
 *
 * @param destination - ISO 3166-1 alpha-2 country code (e.g., "US", "DE").
 * @param weightKg - Total weight of the order in kilograms. Must be positive.
 * @returns The shipping cost in USD cents.
 * @throws {InvalidDestinationError} If the country code is not supported.
 * @throws {WeightLimitExceededError} If weightKg exceeds 30.
 */
function calculateShippingCost(destination: string, weightKg: number): number {
  // ...
}
```

---

## Performance Awareness

- Do not optimize prematurely. Write clear, correct code first. Optimize only when profiling identifies a bottleneck.
- Be aware of algorithmic complexity. A nested loop over a large dataset (O(n^2)) is a red flag — consider whether a hash map, index, or different data structure would help.
- Avoid unnecessary allocations in hot paths: reuse buffers, avoid string concatenation in loops, prefer streaming over loading entire datasets into memory.
- Know the cost of your abstractions. ORMs, serialization frameworks, and middleware have overhead. In performance-critical paths, consider dropping down a level.
- Cache expensive computations, but always define a cache invalidation strategy. Unbounded caches are memory leaks.
- Prefer lazy evaluation and pagination when dealing with large collections. Never load an entire table into memory unless you are certain the table is small.

---

## Dependency Management

- Add a dependency only when the alternative is writing and maintaining significant code yourself. A 10-line utility function does not need a package.
- Before adding a dependency, evaluate: maintenance activity, open issue count, license compatibility, download/usage numbers, and transitive dependency count.
- Pin dependency versions explicitly in lock files. Never rely on floating ranges (e.g., `^1.0.0`) in production deployments.
- Audit dependencies regularly for known vulnerabilities. Integrate automated tools (Dependabot, Snyk, Renovate) into CI.
- Separate production dependencies from development dependencies. Test frameworks, linters, and build tools do not belong in the production bundle.
- When wrapping a third-party dependency, do so behind an internal interface. This allows replacement without rewriting consumers.

---

## Code Review Readiness

Before submitting code for review (or before an AI assistant considers a task complete), verify:

1. **It compiles and passes all tests.** Never submit code that has known failures.
2. **It includes tests.** Every behavioral change must have corresponding test coverage.
3. **It handles edge cases.** Empty inputs, null values, boundary conditions, and concurrent access have been considered.
4. **It follows the project style.** Formatting matches the project configuration. No linter warnings or errors.
5. **It has no debug artifacts.** Remove `console.log`, `print()`, `debugger`, commented-out code, and hard-coded test values.
6. **It is scoped correctly.** A single PR addresses a single concern. Do not mix refactoring with feature work. Do not mix formatting changes with logic changes.
7. **It is self-describing.** The PR description explains what changed and why. If context is needed, it links to the relevant issue or design document.
8. **It does not introduce tech debt without acknowledgment.** If a shortcut was taken, document it with a TODO and a ticket number.

---

## Summary Checklist

| Principle | Check |
|---|---|
| Readable | Can a new team member understand this in under 60 seconds? |
| Simple | Is the simplest possible approach used? |
| Named well | Do names convey intent without needing comments? |
| Sized right | Are files under 300 lines, functions under 40? |
| Errors handled | Are all error paths covered with context? |
| Documented | Are public APIs documented and non-obvious decisions explained? |
| Performant | Are there any O(n^2) or worse operations on large datasets? |
| Dependencies | Is every dependency justified and pinned? |
| Review-ready | Tests pass, no debug artifacts, single concern? |
