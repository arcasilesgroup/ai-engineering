## Java Best Practices

### Modern Java Features

**Use modern Java (11+):**

- Use `var` for local variables with obvious types (Java 10+)
- Use text blocks for multi-line strings (Java 15+)
- Use switch expressions (Java 14+)
- Use records for immutable data carriers (Java 16+)
- Use sealed classes for restricted hierarchies (Java 17+)

**Pattern:**

```java
// ✅ GOOD: Modern Java
var users = userRepository.findAll();

var json = """
    {
      "name": "John",
      "email": "john@example.com"
    }
    """;

// Switch expression
String result = switch (status) {
    case ACTIVE -> "User is active";
    case INACTIVE -> "User is inactive";
    default -> "Unknown status";
};
```text

### Null Safety

**Avoid null when possible:**

- Use `Optional<T>` for potentially absent values
- Never return null collections (return empty instead)
- Use `@NonNull` and `@Nullable` annotations
- Check parameters with `Objects.requireNonNull()`

**Pattern:**

```java
// ✅ GOOD: Using Optional
public Optional<User> findUser(String id) {
    return userRepository.findById(id);
}

// ✅ GOOD: Return empty collection
public List<User> getActiveUsers() {
    return users.stream()
        .filter(User::isActive)
        .toList();  // Never returns null
}

// ❌ BAD: Returning null
public List<User> getActiveUsers() {
    return null;  // Causes NullPointerException
}
```text

### Streams and Functional Programming

**Effective Stream usage:**

- Use streams for collection transformations
- Avoid side effects in stream operations
- Use method references when possible: `User::getName`
- Collect results appropriately: `toList()`, `toMap()`, `groupingBy()`

**Pattern:**

```java
// ✅ GOOD: Stream pipeline
List<String> activeNames = users.stream()
    .filter(User::isActive)
    .map(User::getName)
    .sorted()
    .toList();

// ❌ BAD: Side effects in stream
users.stream()
    .forEach(user -> {
        user.setProcessed(true);  // Mutating state
        repository.save(user);     // Side effect
    });
```text

### Exception Handling

**Best practices:**

- Catch specific exceptions, not `Exception` or `Throwable`
- Use try-with-resources for `AutoCloseable` objects
- Don't swallow exceptions without logging
- Create custom exceptions for domain errors

**Pattern:**

```java
// ✅ GOOD: try-with-resources
try (var connection = dataSource.getConnection();
     var statement = connection.prepareStatement(sql)) {
    // Use resources
} catch (SQLException e) {
    log.error("Database error", e);
    throw new DataAccessException("Failed to query", e);
}

// ❌ BAD: Swallowing exception
try {
    riskyOperation();
} catch (Exception e) {
    // Silent failure
}
```text

### Generics

**Proper generic usage:**

- Use bounded wildcards for flexibility: `? extends T`, `? super T`
- Don't use raw types (use `List<String>` not `List`)
- Use `<T>` for methods that need type parameters
- Follow PECS: Producer Extends, Consumer Super

**Pattern:**

```java
// ✅ GOOD: Bounded wildcard
public void processUsers(List<? extends User> users) {
    // Can read User or subtype
}

public void addUsers(List<? super User> users) {
    // Can write User or supertype
}
```text

### Immutability

**Prefer immutable objects:**

- Make fields `final` when possible
- Use records for data carriers (Java 16+)
- Return unmodifiable collections: `List.copyOf()`, `Collections.unmodifiableList()`
- Use builder pattern for complex objects

**Pattern:**

```java
// ✅ GOOD: Immutable with record (Java 16+)
public record User(String name, String email) {}

// ✅ GOOD: Immutable class
public final class User {
    private final String name;
    private final String email;

    public User(String name, String email) {
        this.name = Objects.requireNonNull(name);
        this.email = Objects.requireNonNull(email);
    }

    // Only getters, no setters
}
```text

### Naming Conventions

**Java style:**

- `camelCase` for methods, variables, parameters
- `PascalCase` for classes, interfaces, enums, records
- `UPPER_SNAKE_CASE` for constants
- Interfaces without `I` prefix: `Repository` not `IRepository`
- Implementations with descriptive suffix: `JdbcUserRepository`

### Collections

**Choose right collection:**

- `ArrayList` for random access and iteration
- `LinkedList` rarely (usually `ArrayList` is better)
- `HashMap` for key-value lookup
- `HashSet` for unique elements
- `TreeMap`/`TreeSet` for sorted collections
- Use `List.of()`, `Map.of()` for immutable collections (Java 9+)

### Concurrency

**Thread-safe patterns:**

- Use `java.util.concurrent` classes
- Prefer `ExecutorService` over raw `Thread`
- Use `CompletableFuture` for async operations
- Avoid `synchronized` when `Lock` or atomic classes work
- Use thread-safe collections: `ConcurrentHashMap`

**Pattern:**

```java
// ✅ GOOD: ExecutorService
ExecutorService executor = Executors.newFixedThreadPool(10);
Future<Result> future = executor.submit(() -> {
    return computeResult();
});

// ✅ GOOD: CompletableFuture
CompletableFuture.supplyAsync(this::fetchData)
    .thenApply(this::transform)
    .thenAccept(this::save);
```text

### Dependency Injection

**Use DI frameworks:**

- Constructor injection (preferred over field injection)
- Inject interfaces, not implementations
- Use `@Autowired` sparingly (constructor injection doesn't need it in Spring)
- Avoid circular dependencies

### Testing

**JUnit 5 best practices:**

- Use `@Test` for test methods
- Use `@BeforeEach`/`@AfterEach` for setup/teardown
- Use `@ParameterizedTest` for data-driven tests
- Use descriptive test method names
- One assertion concept per test

**Pattern:**

```java
@Test
void shouldReturnUserWhenExists() {
    // Given
    var user = new User("John", "john@example.com");
    when(repository.findById("123")).thenReturn(Optional.of(user));

    // When
    var result = userService.getUser("123");

    // Then
    assertTrue(result.isPresent());
    assertEquals("John", result.get().name());
}
```text

### Common Anti-Patterns

**Avoid:**

- Catching `Exception` or `Throwable` (too broad)
- Using `finalize()` (use try-with-resources or `Cleaner`)
- Public fields (use getters/setters or records)
- Raw types (always use generics)
- String concatenation in loops (use `StringBuilder`)
- Premature optimization
