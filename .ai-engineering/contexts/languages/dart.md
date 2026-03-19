## Dart Best Practices

### Null Safety

**Sound null safety (Dart 2.12+):**

- Non-nullable by default: `String` cannot be null
- Nullable types with `?`: `String?` can be null
- `late` for lazy initialization
- `!` for asserting non-null (use sparingly)

**Pattern:**

```dart
// ✅ GOOD: Null safety
String? findUser(String id) {
  return users[id];
}

// ✅ GOOD: Late initialization
late final Database db;

void init() {
  db = Database();
}

// ✅ GOOD: Null-aware operators
final name = user?.name ?? 'Guest';
user?.updateProfile();

// ❌ BAD: Force unwrap without certainty
final name = user!.name;  // Crashes if user is null
```text

### Async/Await

**Asynchronous programming:**

- Use `async`/`await` for asynchronous operations
- Return `Future<T>` from async functions
- Use `Stream<T>` for multiple values over time
- Handle errors with try-catch

**Pattern:**

```dart
// ✅ GOOD: Async function
Future<User> fetchUser(String id) async {
  final response = await http.get(Uri.parse('$apiUrl/users/$id'));
  return User.fromJson(jsonDecode(response.body));
}

// ✅ GOOD: Error handling
try {
  final user = await fetchUser('123');
  print(user.name);
} catch (e) {
  print('Error: $e');
}

// ✅ GOOD: Stream
Stream<int> countStream() async* {
  for (int i = 0; i < 10; i++) {
    await Future.delayed(Duration(seconds: 1));
    yield i;
  }
}
```text

### Collections

**Use collection features:**

- Collection literals: `[]`, `{}`, `{:}`
- Spread operator: `...`
- Collection if and for
- Cascade notation: `..`

**Pattern:**

```dart
// ✅ GOOD: Collection literal
final numbers = [1, 2, 3];
final names = {'John', 'Jane'};
final userMap = {'id': '123', 'name': 'John'};

// ✅ GOOD: Spread operator
final all = [...numbers, 4, 5];

// ✅ GOOD: Collection if
final items = [
  'Always',
  if (condition) 'Sometimes',
];

// ✅ GOOD: Collection for
final squared = [
  for (var n in numbers) n * n
];

// ✅ GOOD: Cascade
final user = User()
  ..name = 'John'
  ..email = 'john@example.com'
  ..save();
```text

### Classes and Objects

**Object-oriented patterns:**

- Use factory constructors for complex initialization
- Use named constructors for clarity
- Prefer `final` for immutable fields
- Use getters/setters appropriately

**Pattern:**

```dart
// ✅ GOOD: Class with named constructor
class User {
  final String id;
  final String name;
  final String email;

  User({
    required this.id,
    required this.name,
    required this.email,
  });

  // Named constructor
  User.guest()
      : id = 'guest',
        name = 'Guest',
        email = 'guest@example.com';

  // Factory constructor
  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'],
      name: json['name'],
      email: json['email'],
    );
  }

  // Getter
  String get displayName => '$name <$email>';
}
```text

### Functional Programming

**Use functional patterns:**

- Higher-order functions: `map`, `where`, `reduce`
- Arrow functions for simple operations
- Immutable data structures
- Method chaining

**Pattern:**

```dart
// ✅ GOOD: Functional operations
final activeUsers = users
    .where((user) => user.isActive)
    .map((user) => user.name)
    .toList();

// ✅ GOOD: Arrow function
final doubled = numbers.map((n) => n * 2);

// ✅ GOOD: Reduce
final sum = numbers.reduce((a, b) => a + b);

// ✅ GOOD: Method chaining
final result = data
    .where((item) => item.isValid)
    .map((item) => item.value)
    .take(10)
    .toList();
```text

### Extension Methods

**Extend existing types:**

- Add functionality to existing classes
- Keep extensions focused
- Use for utility methods

**Pattern:**

```dart
// ✅ GOOD: String extension
extension StringExtensions on String {
  bool get isValidEmail {
    return contains('@') && contains('.');
  }

  String capitalize() {
    if (isEmpty) return this;
    return '${this[0].toUpperCase()}${substring(1)}';
  }
}

// Usage
if (email.isValidEmail) {
  sendEmail(email);
}

final name = 'john'.capitalize();
```text

### Mixins

**Code reuse with mixins:**

- Use `mixin` keyword for reusable behavior
- Can be applied to classes with `with`
- Keep mixins focused on single concern
- Use `on` clause to restrict mixin usage

**Pattern:**

```dart
// ✅ GOOD: Mixin
mixin Timestampable {
  DateTime? createdAt;
  DateTime? updatedAt;

  void initializeTimestamps() {
    final now = DateTime.now();
    createdAt = now;
    updatedAt = now;
  }

  void touch() {
    updatedAt = DateTime.now();
  }
}

// ✅ GOOD: Restricted mixin
mixin Loggable on Object {
  void log(String message) {
    print('${runtimeType}: $message');
  }
}

class User with Timestampable, Loggable {
  String name;

  User(this.name) {
    initializeTimestamps();
  }
}
```text

### Enums

**Use enums for fixed sets:**

- Enhanced enums (Dart 2.17+)
- Methods and properties on enums
- Pattern matching with switch

**Pattern:**

```dart
// ✅ GOOD: Enhanced enum
enum Status {
  active('Active', 1),
  inactive('Inactive', 0),
  pending('Pending', -1);

  final String label;
  final int code;

  const Status(this.label, this.code);

  bool get isActive => this == Status.active;
}

// Usage
final status = Status.active;
print(status.label);  // "Active"
print(status.code);   // 1

// Pattern matching
String getMessage(Status status) {
  return switch (status) {
    Status.active => 'User is active',
    Status.inactive => 'User is inactive',
    Status.pending => 'User is pending',
  };
}
```text

### Naming Conventions

**Dart style:**

- `lowerCamelCase` for variables, functions, parameters
- `UpperCamelCase` for classes, enums, typedefs
- `lowercase_with_underscores` for libraries and file names
- Prefix private members with `_`
- Use descriptive names

### Error Handling

**Exceptions and errors:**

- Throw exceptions for exceptional cases
- Catch specific exceptions when possible
- Use custom exceptions for domain errors
- Use `try-finally` for cleanup

**Pattern:**

```dart
// ✅ GOOD: Custom exception
class UserNotFoundException implements Exception {
  final String userId;
  UserNotFoundException(this.userId);

  @override
  String toString() => 'User not found: $userId';
}

// ✅ GOOD: Specific catch
try {
  final user = await fetchUser(id);
  process(user);
} on UserNotFoundException catch (e) {
  print('Not found: $e');
} on NetworkException catch (e) {
  print('Network error: $e');
} finally {
  cleanup();
}
```text

### Flutter-Specific

**Flutter best practices:**

- Use `const` constructors for immutable widgets
- Extract widgets for reusability
- Use `setState` only for local state
- Use state management for complex state (Provider, Riverpod, Bloc)
- Avoid deep widget trees

**Pattern:**

```dart
// ✅ GOOD: Const widget
class UserCard extends StatelessWidget {
  final User user;

  const UserCard({Key? key, required this.user}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      child: ListTile(
        title: Text(user.name),
        subtitle: Text(user.email),
      ),
    );
  }
}

// ✅ GOOD: Extract widget
Widget _buildHeader() {
  return const Text('Header');
}

// ✅ GOOD: StatefulWidget pattern
class Counter extends StatefulWidget {
  const Counter({Key? key}) : super(key: key);

  @override
  State<Counter> createState() => _CounterState();
}

class _CounterState extends State<Counter> {
  int _count = 0;

  void _increment() {
    setState(() {
      _count++;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Text('Count: $_count');
  }
}
```text

### Testing

**Testing best practices:**

- Unit tests for business logic
- Widget tests for UI components
- Integration tests for user flows
- Use test groups for organization
- Mock dependencies

**Pattern:**

```dart
// ✅ GOOD: Unit test
void main() {
  group('User', () {
    test('should create user from JSON', () {
      final json = {'id': '123', 'name': 'John', 'email': 'john@example.com'};
      final user = User.fromJson(json);

      expect(user.id, '123');
      expect(user.name, 'John');
    });

    test('displayName should format correctly', () {
      final user = User(id: '123', name: 'John', email: 'john@example.com');
      expect(user.displayName, 'John <john@example.com>');
    });
  });
}

// ✅ GOOD: Widget test
testWidgets('Counter increments', (WidgetTester tester) async {
  await tester.pumpWidget(const MaterialApp(home: Counter()));

  expect(find.text('Count: 0'), findsOneWidget);

  await tester.tap(find.byIcon(Icons.add));
  await tester.pump();

  expect(find.text('Count: 1'), findsOneWidget);
});
```text

### Common Anti-Patterns

**Avoid:**

- Using `!` to force unwrap without certainty
- Ignoring compiler warnings
- Deep widget nesting (extract to methods/widgets)
- Not using `const` for immutable widgets
- Mutable state in StatelessWidget
- Synchronous file I/O (use async)
- Using dynamic when types are known
- Not disposing controllers and streams
