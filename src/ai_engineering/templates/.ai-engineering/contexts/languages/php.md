## PHP Best Practices

### Modern PHP (8.0+)

**Use modern PHP features:**

- Named arguments for clarity
- Constructor property promotion (PHP 8.0+)
- Union types and nullable types
- Match expressions instead of switch
- Attributes instead of docblock annotations

**Pattern:**

```php
// ✅ GOOD: Constructor property promotion
class User {
    public function __construct(
        public readonly string $name,
        public readonly string $email,
        private string $password,
    ) {}
}

// ✅ GOOD: Named arguments
$user = new User(
    name: 'John',
    email: 'john@example.com',
    password: 'secret',
);

// ✅ GOOD: Match expression
$message = match($status) {
    'active' => 'User is active',
    'inactive' => 'User is inactive',
    default => 'Unknown status',
};
```text

### Type Declarations

**Use strict types:**

- Enable strict_types at the top of every file
- Declare parameter types and return types
- Use union types (PHP 8.0+) and intersection types (PHP 8.1+)
- Use `mixed` when type truly varies

**Pattern:**

```php
<?php
declare(strict_types=1);

// ✅ GOOD: Full type declarations
function findUser(string $id): ?User {
    return $this->repository->find($id);
}

// ✅ GOOD: Union types
function process(string|int $id): User {
    // Implementation
}

// ❌ BAD: No types
function findUser($id) {
    return $this->repository->find($id);
}
```text

### Null Safety

**Handle nulls explicitly:**

- Use nullable types: `?string`
- Use null coalescing: `??`
- Use null safe operator: `?->` (PHP 8.0+)
- Return null or throw, don't return mixed types

**Pattern:**

```php
// ✅ GOOD: Nullable return
function findUser(string $id): ?User {
    return $this->users[$id] ?? null;
}

// ✅ GOOD: Null coalescing
$name = $user->name ?? 'Guest';

// ✅ GOOD: Null safe operator (PHP 8.0+)
$email = $user?->profile?->email;

// ❌ BAD: Mixed return types
function findUser($id) {
    return $this->users[$id] ?? false;  // null or false?
}
```text

### Error Handling

**Use exceptions properly:**

- Throw exceptions for exceptional cases
- Catch specific exceptions, not `\Exception`
- Use custom exceptions for domain errors
- Always provide context in exception messages

**Pattern:**

```php
// ✅ GOOD: Custom exception
class UserNotFoundException extends \RuntimeException {
    public function __construct(string $userId) {
        parent::__construct("User not found: {$userId}");
    }
}

// ✅ GOOD: Specific catch
try {
    $user = $this->findUser($id);
} catch (UserNotFoundException $e) {
    // Handle not found
} catch (\PDOException $e) {
    // Handle database error
}

// ❌ BAD: Catching everything
catch (\Exception $e) {
    // Too broad
}
```text

### Arrays and Collections

**Modern array handling:**

- Use array destructuring (PHP 7.1+)
- Use array spread operator (PHP 7.4+)
- Use array functions: `array_map`, `array_filter`, `array_reduce`
- Consider collections library for complex operations

**Pattern:**

```php
// ✅ GOOD: Array destructuring
[$first, $second] = $array;

// ✅ GOOD: Spread operator
$merged = [...$array1, ...$array2];

// ✅ GOOD: Functional style
$activeUsers = array_filter(
    $users,
    fn($user) => $user->isActive()
);

$names = array_map(
    fn($user) => $user->name,
    $users
);
```text

### Object-Oriented Design

**SOLID principles:**

- Single Responsibility: One class, one job
- Dependency Injection: Constructor injection preferred
- Interface over implementation: Type-hint interfaces
- Immutability: Use `readonly` properties (PHP 8.1+)
- Final by default: Use `final` unless extension needed

**Pattern:**

```php
// ✅ GOOD: Constructor injection with readonly
final class UserService {
    public function __construct(
        private readonly UserRepository $repository,
        private readonly EmailService $emailService,
    ) {}

    public function register(string $email): User {
        $user = User::create($email);
        $this->repository->save($user);
        $this->emailService->sendWelcome($user);
        return $user;
    }
}

// ✅ GOOD: Interface injection
interface UserRepository {
    public function save(User $user): void;
    public function find(string $id): ?User;
}
```text

### Enums (PHP 8.1+)

**Use enums for fixed sets:**

- Backed enums for string/int values
- Methods on enums for behavior
- Pattern matching with match

**Pattern:**

```php
// ✅ GOOD: Backed enum
enum Status: string {
    case Active = 'active';
    case Inactive = 'inactive';
    case Pending = 'pending';

    public function label(): string {
        return match($this) {
            self::Active => 'Active User',
            self::Inactive => 'Inactive User',
            self::Pending => 'Pending Approval',
        };
    }
}

// Usage
$status = Status::Active;
echo $status->label();  // "Active User"
echo $status->value;    // "active"
```text

### Traits

**Use traits for code reuse:**

- Use for horizontal functionality (not inheritance)
- Keep traits focused and cohesive
- Resolve conflicts explicitly
- Don't overuse - composition often better

**Pattern:**

```php
// ✅ GOOD: Focused trait
trait Timestampable {
    private \DateTimeImmutable $createdAt;
    private \DateTimeImmutable $updatedAt;

    private function initializeTimestamps(): void {
        $now = new \DateTimeImmutable();
        $this->createdAt = $now;
        $this->updatedAt = $now;
    }

    public function touch(): void {
        $this->updatedAt = new \DateTimeImmutable();
    }
}

class User {
    use Timestampable;

    public function __construct() {
        $this->initializeTimestamps();
    }
}
```text

### Naming Conventions

**PHP style (PSR-12):**

- `PascalCase` for class names
- `camelCase` for methods and properties
- `UPPER_CASE` for constants
- `snake_case` for array keys
- Descriptive names, avoid abbreviations

### Namespaces and Autoloading

**PSR-4 autoloading:**

- One class per file
- Namespace matches directory structure
- Use `use` statements for clarity
- Group related classes in namespaces

**Pattern:**

```php
<?php
declare(strict_types=1);

namespace App\User\Domain;

use App\User\Repository\UserRepository;
use App\Email\EmailService;

final class UserService {
    // Implementation
}
```text

### Security

**Common security practices:**

- Use prepared statements (PDO/MySQLi)
- Never trust user input
- Use `password_hash()` and `password_verify()`
- Validate and sanitize input
- Use CSRF tokens
- Enable `strict_types`

**Pattern:**

```php
// ✅ GOOD: Prepared statements
$stmt = $pdo->prepare('SELECT * FROM users WHERE id = :id');
$stmt->execute(['id' => $userId]);

// ✅ GOOD: Password hashing
$hash = password_hash($password, PASSWORD_DEFAULT);
if (password_verify($inputPassword, $hash)) {
    // Valid
}

// ❌ BAD: SQL injection risk
$query = "SELECT * FROM users WHERE id = {$userId}";
```text

### Testing

**PHPUnit best practices:**

- Use type hints in tests
- One assertion concept per test
- Use data providers for parameterized tests
- Mock dependencies with interfaces
- Test behavior, not implementation

**Pattern:**

```php
final class UserServiceTest extends TestCase {
    public function test_register_creates_user(): void {
        $repository = $this->createMock(UserRepository::class);
        $repository->expects($this->once())
            ->method('save');

        $service = new UserService($repository);
        $user = $service->register('test@example.com');

        $this->assertEquals('test@example.com', $user->email);
    }

    /**
     * @dataProvider statusProvider
     */
    public function test_status_labels(Status $status, string $expected): void {
        $this->assertEquals($expected, $status->label());
    }

    public function statusProvider(): array {
        return [
            [Status::Active, 'Active User'],
            [Status::Inactive, 'Inactive User'],
        ];
    }
}
```text

### Common Anti-Patterns

**Avoid:**

- Global variables and superglobals (use dependency injection)
- `eval()` - security risk
- `@` error suppression (handle errors properly)
- Type juggling (use `===` not `==`)
- Mutable static state
- God objects (classes that do too much)
- Using arrays when objects would be clearer
- Ignoring return values from important functions
