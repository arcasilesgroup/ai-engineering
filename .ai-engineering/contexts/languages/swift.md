## Swift Best Practices

### Optionals

**Proper optional handling:**

- Use optional binding (`if let`, `guard let`) instead of force unwrapping
- Use optional chaining (`?.`) for safe property access
- Use nil coalescing (`??`) for default values
- Avoid force unwrapping (`!`) except for IBOutlets or known-safe cases

**Pattern:**

```swift
// ✅ GOOD: Optional binding
if let user = findUser(id: userId) {
    print(user.name)
}

// ✅ GOOD: Guard for early exit
guard let user = findUser(id: userId) else {
    return
}

// ✅ GOOD: Optional chaining
let email = user?.profile?.email

// ✅ GOOD: Nil coalescing
let name = user?.name ?? "Guest"

// ❌ BAD: Force unwrapping
let user = findUser(id: userId)!  // Crashes if nil
```text

### Error Handling

**Use Swift's error handling:**

- Define errors as enums conforming to `Error`
- Use `throws` for functions that can fail
- Use `do-catch` for error handling
- Use `try?` when you don't care about the error
- Use `try!` only for known-safe operations

**Pattern:**

```swift
// ✅ GOOD: Error enum
enum NetworkError: Error {
    case invalidURL
    case noData
    case decodingFailed
}

// ✅ GOOD: Throwing function
func fetchUser(id: String) throws -> User {
    guard let url = URL(string: apiURL) else {
        throw NetworkError.invalidURL
    }
    // Implementation
}

// ✅ GOOD: Error handling
do {
    let user = try fetchUser(id: "123")
    process(user)
} catch NetworkError.invalidURL {
    print("Invalid URL")
} catch {
    print("Error: \(error)")
}

// ✅ GOOD: When error doesn't matter
let user = try? fetchUser(id: "123")
```text

### Value Types vs Reference Types

**When to use each:**

- Structs (value types) for data models, immutable state
- Classes (reference types) for shared mutable state, inheritance
- Prefer structs by default (copy semantics are safer)
- Use classes when you need identity or reference counting

**Pattern:**

```swift
// ✅ GOOD: Struct for data model
struct User {
    let id: String
    let name: String
    var email: String
}

// ✅ GOOD: Class for shared state
class UserSession {
    var currentUser: User?
    // Shared across app
}
```text

### Property Wrappers

**Common property wrappers:**

- `@State` for local view state (SwiftUI)
- `@Binding` for two-way bindings (SwiftUI)
- `@Published` for observable properties (Combine)
- `@ObservedObject` for external observable objects (SwiftUI)
- `@StateObject` for owned observable objects (SwiftUI)

**Pattern:**

```swift
// ✅ GOOD: State management in SwiftUI
struct ContentView: View {
    @State private var count = 0
    @StateObject private var viewModel = ViewModel()

    var body: some View {
        Text("Count: \(count)")
    }
}
```text

### Protocol-Oriented Programming

**Prefer protocols over inheritance:**

- Define behavior with protocols
- Use protocol extensions for default implementations
- Conform to protocols rather than subclassing
- Use associated types for generic protocols

**Pattern:**

```swift
// ✅ GOOD: Protocol with extension
protocol Identifiable {
    var id: String { get }
}

extension Identifiable {
    func isEqual(to other: Self) -> Bool {
        return id == other.id
    }
}

struct User: Identifiable {
    let id: String
    let name: String
}
```text

### Memory Management

**ARC best practices:**

- Use `weak` for delegates and parent references (avoid retain cycles)
- Use `unowned` when reference is never nil after initialization
- Use capture lists in closures: `[weak self]` or `[unowned self]`
- Avoid strong reference cycles in closures

**Pattern:**

```swift
// ✅ GOOD: Weak self in closure
class ViewController {
    func loadData() {
        apiClient.fetch { [weak self] result in
            guard let self = self else { return }
            self.process(result)
        }
    }
}

// ✅ GOOD: Weak delegate
protocol UserDelegate: AnyObject {
    func didUpdate(user: User)
}

class UserManager {
    weak var delegate: UserDelegate?
}
```text

### Naming Conventions

**Swift style:**

- `camelCase` for variables, functions, parameters
- `PascalCase` for types (classes, structs, enums, protocols)
- Use descriptive names, avoid abbreviations
- Verb phrases for methods: `calculateTotal()`, `updateUser()`
- Boolean properties start with `is`, `has`, `can`: `isActive`, `hasPermission`

### Enums

**Powerful enum features:**

- Use associated values for data
- Use raw values for simple mappings
- Make enums conform to `CaseIterable` for iteration
- Use pattern matching in switch statements

**Pattern:**

```swift
// ✅ GOOD: Enum with associated values
enum Result<T> {
    case success(T)
    case failure(Error)
}

// ✅ GOOD: Pattern matching
switch result {
case .success(let user):
    print("Got user: \(user)")
case .failure(let error):
    print("Error: \(error)")
}

// ✅ GOOD: CaseIterable
enum Status: CaseIterable {
    case active, inactive, pending
}

// Can iterate: Status.allCases.forEach { ... }
```text

### Closures

**Closure best practices:**

- Use trailing closure syntax when last parameter
- Use shorthand argument names (`$0`, `$1`) for simple closures
- Use capture lists to avoid retain cycles
- Prefer explicit types when closure is complex

**Pattern:**

```swift
// ✅ GOOD: Trailing closure
users.map { user in
    user.name
}

// ✅ GOOD: Shorthand arguments
users.filter { $0.isActive }

// ✅ GOOD: Capture list
{ [weak self] in
    self?.updateUI()
}
```text

### Extensions

**Organize code with extensions:**

- Separate protocol conformance into extensions
- Group related functionality
- Add computed properties and convenience methods
- Don't add stored properties (use computed or associated objects)

**Pattern:**

```swift
// ✅ GOOD: Protocol conformance in extension
extension User: Codable {
    // Codable implementation
}

extension User {
    var displayName: String {
        return "\(name) <\(email)>"
    }
}
```text

### SwiftUI Patterns

**SwiftUI best practices:**

- Extract subviews for complex views
- Use `@State` for local state, `@StateObject` for owned objects
- Use `@Binding` for child views that modify parent state
- Keep views pure (no side effects in body)
- Use `.task` for async operations

**Pattern:**

```swift
// ✅ GOOD: Small, focused views
struct UserView: View {
    @StateObject private var viewModel = UserViewModel()

    var body: some View {
        VStack {
            UserHeaderView(user: viewModel.user)
            UserDetailsView(user: $viewModel.user)
        }
        .task {
            await viewModel.loadUser()
        }
    }
}
```text

### Async/Await (Swift 5.5+)

**Modern concurrency:**

- Use `async`/`await` instead of completion handlers
- Use `Task` to bridge sync to async
- Use `@MainActor` for UI updates
- Avoid mixing async/await with completion handlers

**Pattern:**

```swift
// ✅ GOOD: Async function
func fetchUser(id: String) async throws -> User {
    let (data, _) = try await URLSession.shared.data(from: url)
    return try JSONDecoder().decode(User.self, from: data)
}

// ✅ GOOD: MainActor for UI
@MainActor
func updateUI(with user: User) {
    self.nameLabel.text = user.name
}

// ✅ GOOD: Task bridge
Task {
    let user = try await fetchUser(id: "123")
    await updateUI(with: user)
}
```text

### Common Anti-Patterns

**Avoid:**

- Force unwrapping optionals unnecessarily
- Using `as!` force casting (use `as?` and handle nil)
- Massive view controllers (break into smaller components)
- Retain cycles in closures
- Using `NSObject` subclasses when structs would work
- Implicit self in closures (be explicit with capture lists)
