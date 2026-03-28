# Handler: Language -- Java

## Purpose

Language-specific review for Java code. Supplements the 8-concern review agents with Spring-aware patterns, JPA/Hibernate checks, concurrency safety, and a dedicated workflow/state machine review section for enterprise applications.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Java Scope

1. Identify `.java` files in the diff
2. If no Java files, skip this handler entirely
3. Detect frameworks from imports and build files:
   - `org.springframework` imports -> enable Spring checks
   - `jakarta.persistence` / `javax.persistence` imports -> enable JPA checks
   - `io.quarkus` -> enable Quarkus checks
   - `io.micronaut` -> enable Micronaut checks
4. Check Java version from `pom.xml` (`maven.compiler.source`) or `build.gradle` (`sourceCompatibility`)
5. Read `.ai-engineering/contexts/languages/java.md` if not already loaded

### Step 2 -- Critical Findings (severity: critical)

**SQL injection**
```java
// BAD: string concatenation
String query = "SELECT * FROM users WHERE id = '" + userId + "'";
statement.executeQuery(query);

// BAD: String.format
statement.executeQuery(String.format("SELECT * FROM users WHERE id = '%s'", userId));

// GOOD: parameterized query
PreparedStatement ps = conn.prepareStatement("SELECT * FROM users WHERE id = ?");
ps.setString(1, userId);

// GOOD: Spring JPA
@Query("SELECT u FROM User u WHERE u.id = :id")
User findById(@Param("id") String id);
```

**ProcessBuilder / Runtime.exec with user input**
```java
// BAD: command injection
Runtime.getRuntime().exec("ls " + userInput);
new ProcessBuilder("sh", "-c", userInput).start();

// GOOD: argument list, no shell interpretation
new ProcessBuilder("ls", sanitizedPath).start();
```

**@RequestBody without @Valid**
```java
// BAD: unvalidated input
@PostMapping("/users")
public ResponseEntity<User> create(@RequestBody UserRequest request) {

// GOOD: validation enforced
@PostMapping("/users")
public ResponseEntity<User> create(@Valid @RequestBody UserRequest request) {
```
- Confidence 90% for POST/PUT/PATCH endpoints

**Optional.get() without isPresent() check**
```java
// BAD: throws NoSuchElementException
User user = userRepository.findById(id).get();

// GOOD: safe alternatives
User user = userRepository.findById(id)
    .orElseThrow(() -> new UserNotFoundException(id));

// ALSO GOOD
userRepository.findById(id).ifPresent(this::processUser);
```

### Step 3 -- High Findings (severity: major)

**@Autowired field injection**
```java
// BAD: hidden dependencies, hard to test
@Service
public class UserService {
    @Autowired
    private UserRepository userRepository;
}

// GOOD: constructor injection
@Service
public class UserService {
    private final UserRepository userRepository;

    public UserService(UserRepository userRepository) {
        this.userRepository = userRepository;
    }
}

// ALSO GOOD: Lombok
@Service
@RequiredArgsConstructor
public class UserService {
    private final UserRepository userRepository;
}
```

**Business logic in controllers**
```java
// BAD: controller does too much
@PostMapping("/orders")
public ResponseEntity<Order> createOrder(@Valid @RequestBody OrderRequest req) {
    var total = req.getItems().stream().mapToDouble(Item::getPrice).sum();
    var tax = total * 0.21;
    var order = new Order(req.getItems(), total + tax);
    orderRepository.save(order);
    emailService.sendConfirmation(order);
    return ResponseEntity.ok(order);
}

// GOOD: delegated to service
@PostMapping("/orders")
public ResponseEntity<Order> createOrder(@Valid @RequestBody OrderRequest req) {
    var order = orderService.create(req);
    return ResponseEntity.ok(order);
}
```

**@Transactional on wrong layer**
- `@Transactional` on controller methods -> should be on service layer
- `@Transactional` on private methods -> Spring proxy ignores it
- `@Transactional` missing on methods that perform multiple writes
- `@Transactional(readOnly = true)` missing on read-only service methods

**FetchType.EAGER on entity relationships**
```java
// BAD: loads entire object graph
@OneToMany(fetch = FetchType.EAGER)
private List<Order> orders;

// GOOD: lazy loading with explicit fetch when needed
@OneToMany(fetch = FetchType.LAZY)
private List<Order> orders;
```
- `@ManyToOne` defaults to EAGER; flag when not explicitly set to LAZY on large entities

**JPA entity exposed directly as API response**
```java
// BAD: internal representation leaked
@GetMapping("/users/{id}")
public User getUser(@PathVariable Long id) {
    return userRepository.findById(id).orElseThrow();  // entity returned directly
}

// GOOD: DTO mapping
@GetMapping("/users/{id}")
public UserResponse getUser(@PathVariable Long id) {
    User user = userRepository.findById(id).orElseThrow();
    return UserResponse.from(user);
}
```
- Exposes internal fields, risks lazy-load exceptions, prevents API evolution

### Step 4 -- Medium Findings (severity: minor)

**CompletableFuture without custom Executor**
```java
// BAD: uses ForkJoinPool.commonPool (shared, limited)
CompletableFuture.supplyAsync(() -> expensiveCall());

// GOOD: dedicated executor
CompletableFuture.supplyAsync(() -> expensiveCall(), taskExecutor);
```

**instanceof without pattern matching (Java 16+)**
```java
// BAD: pre-16 style
if (shape instanceof Circle) {
    Circle c = (Circle) shape;
    return c.radius();
}

// GOOD: pattern matching
if (shape instanceof Circle c) {
    return c.radius();
}
```
- Only flag for projects using Java 16+

**@SpringBootTest for unit tests**
```java
// BAD: loads entire application context for unit test
@SpringBootTest
class UserServiceTest {

// GOOD: plain unit test with mocks
@ExtendWith(MockitoExtension.class)
class UserServiceTest {
    @Mock UserRepository userRepository;
    @InjectMocks UserService userService;
}
```
- `@SpringBootTest` acceptable only for integration tests

**Missing @Override annotation**
- Methods that override parent but lack `@Override`

### Step 5 -- Workflow and State Machine Review

For codebases implementing workflows, sagas, or state machines:

**Idempotency**
```java
// BAD: non-idempotent operation
@PostMapping("/payments/{id}/process")
public void processPayment(@PathVariable Long id) {
    paymentService.charge(id);  // double-call = double-charge
}

// GOOD: idempotent with idempotency key
@PostMapping("/payments/{id}/process")
public void processPayment(
    @PathVariable Long id,
    @RequestHeader("Idempotency-Key") String key
) {
    paymentService.chargeIdempotent(id, key);
}
```
- Flag state-mutating operations without idempotency protection

**Illegal state transitions**
```java
// BAD: allows any transition
public void updateStatus(OrderStatus newStatus) {
    this.status = newStatus;
}

// GOOD: validated transitions
public void updateStatus(OrderStatus newStatus) {
    if (!this.status.canTransitionTo(newStatus)) {
        throw new IllegalStateTransitionException(this.status, newStatus);
    }
    this.status = newStatus;
}
```
- Flag direct enum/status field assignment without transition validation

**Missing dead-letter / failure handling**
- Message consumers without error handling or dead-letter queue configuration
- `@KafkaListener` / `@RabbitListener` without `errorHandler`
- Async operations without retry policy or compensation logic

**Missing audit trail for state changes**
- State transitions without event emission or audit logging
- Critical for regulated industries (finance, healthcare)

### Step 6 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| javac | `mvn compile` / `gradle compileJava` | Compilation correctness |
| SpotBugs | `mvn spotbugs:check` | Bug pattern detection |
| PMD | `mvn pmd:check` | Code quality, dead code |
| OWASP DC | `mvn dependency-check:check` | Vulnerable dependencies |
| JUnit | `mvn test` / `gradle test` | Test correctness and coverage |
| ArchUnit | Architectural rule tests | Layer violation detection |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-java-N
    severity: critical|major|minor
    confidence: 0-100
    file: path
    line: N
    finding: "description"
    evidence: "code snippet"
    remediation: "how to fix"
    self_challenge:
      counter: "why this might be wrong"
      resolution: "why it stands or adjustment"
      adjusted_confidence: N
```
