# Java Review Guidelines

## Update Metadata
- Rationale: Java-specific patterns for null safety, streams, and Spring conventions.

## Idiomatic Patterns
- Use `Optional<T>` for nullable return values — never return `null` from public APIs.
- Prefer streams + collectors over imperative loops for data transformation.
- Use `record` types (Java 16+) for immutable value objects.
- Constructor injection over field injection (`@Autowired` on fields is discouraged).

## Performance Anti-Patterns
- **N+1 in JPA/Hibernate**: Use `@EntityGraph` or `JOIN FETCH` to avoid lazy loading in loops.
- **Autoboxing in loops**: Prefer primitive types for counters and accumulators.
- **String concatenation in loops**: Use `StringBuilder`.

## Security Patterns
- Use prepared statements for all database queries.
- Validate input with Bean Validation (`@Valid`, `@NotNull`, `@Size`).
- Use `@PreAuthorize` / `@Secured` for method-level security.

## Testing Patterns
- JUnit 5 with `@ParameterizedTest` for data-driven tests.
- Use `@MockBean` / `@SpyBean` in Spring Boot tests.
- `@Testcontainers` for integration tests with real databases.

## Self-Challenge Questions
- Is this a Java version issue? Check the project's source compatibility level.
- Does the stream pipeline improve or hurt readability?

## References
- Enforcement: `standards/framework/stacks/java-kotlin.md`
