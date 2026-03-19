## iOS Development Best Practices

### Project Structure

**Organize by feature:**

- Group related files (View, ViewModel, Model)
- Use MVVM or MVC architecture
- Separate UI from business logic
- Use folders for modules/features

**Pattern:**

```text
MyApp/
  Features/
    User/
      Views/
        UserProfileView.swift
        UserListView.swift
      ViewModels/
        UserViewModel.swift
      Models/
        User.swift
      Services/
        UserService.swift
    Products/
      ...
  Core/
    Networking/
    Database/
    Extensions/
```text

### SwiftUI Views

**Build efficient views:**

- Keep views small and focused
- Extract subviews for reusability
- Use @State for local state
- Use @StateObject for owned objects
- Use @ObservedObject for passed objects

**Pattern:**

```swift
// ✅ GOOD: Small, focused view
struct UserProfileView: View {
    @StateObject private var viewModel: UserViewModel

    init(userId: String) {
        _viewModel = StateObject(wrappedValue: UserViewModel(userId: userId))
    }

    var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                UserHeaderView(user: viewModel.user)
                UserStatsView(user: viewModel.user)
                UserActivityView(activities: viewModel.activities)
            }
        }
        .task {
            await viewModel.loadUser()
        }
    }
}

// ✅ GOOD: Extract subview
struct UserHeaderView: View {
    let user: User

    var body: some View {
        VStack {
            AsyncImage(url: user.avatarURL) { image in
                image.resizable()
            } placeholder: {
                ProgressView()
            }
            .frame(width: 80, height: 80)
            .clipShape(Circle())

            Text(user.name)
                .font(.headline)
            Text(user.email)
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
    }
}
```text

### View Models

**MVVM pattern:**

- Conform to ObservableObject
- Use @Published for observable properties
- Keep view models testable
- Handle async operations properly

**Pattern:**

```swift
// ✅ GOOD: ViewModel
@MainActor
class UserViewModel: ObservableObject {
    @Published private(set) var user: User?
    @Published private(set) var isLoading = false
    @Published private(set) var error: Error?

    private let userService: UserService

    init(userId: String, userService: UserService = .shared) {
        self.userService = userService
    }

    func loadUser() async {
        isLoading = true
        error = nil

        do {
            user = try await userService.fetchUser(userId)
        } catch {
            self.error = error
        }

        isLoading = false
    }
}
```text

### Networking

**URLSession best practices:**

- Use async/await
- Handle errors properly
- Decode with Codable
- Use proper HTTP methods
- Handle authentication

**Pattern:**

```swift
// ✅ GOOD: Networking layer
enum NetworkError: Error {
    case invalidURL
    case invalidResponse
    case decodingError
}

class APIClient {
    static let shared = APIClient()
    private let session: URLSession

    init(session: URLSession = .shared) {
        self.session = session
    }

    func fetch<T: Decodable>(
        _ endpoint: String,
        method: String = "GET",
        body: Encodable? = nil
    ) async throws -> T {
        guard let url = URL(string: endpoint) else {
            throw NetworkError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let body = body {
            request.httpBody = try JSONEncoder().encode(body)
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw NetworkError.invalidResponse
        }

        do {
            return try JSONDecoder().decode(T.self, from: data)
        } catch {
            throw NetworkError.decodingError
        }
    }
}

// Usage
struct UserService {
    static let shared = UserService()
    private let client = APIClient.shared

    func fetchUser(_ id: String) async throws -> User {
        try await client.fetch("https://api.example.com/users/\(id)")
    }
}
```text

### Data Persistence

**Core Data or SwiftData:**

- Use for local data storage
- Handle concurrency properly
- Use fetch requests efficiently
- Migrate schema carefully

**Pattern:**

```swift
// ✅ GOOD: Core Data manager
class CoreDataManager {
    static let shared = CoreDataManager()

    lazy var persistentContainer: NSPersistentContainer = {
        let container = NSPersistentContainer(name: "MyApp")
        container.loadPersistentStores { _, error in
            if let error = error {
                fatalError("Core Data failed to load: \(error)")
            }
        }
        return container
    }()

    var context: NSManagedObjectContext {
        persistentContainer.viewContext
    }

    func save() {
        guard context.hasChanges else { return }

        do {
            try context.save()
        } catch {
            print("Failed to save context: \(error)")
        }
    }
}

// ✅ GOOD: SwiftData (iOS 17+)
@Model
class User {
    @Attribute(.unique) var id: String
    var name: String
    var email: String

    init(id: String, name: String, email: String) {
        self.id = id
        self.name = name
        self.email = email
    }
}
```text

### Navigation

**Navigation patterns:**

- Use NavigationStack for hierarchical navigation
- Use TabView for tab-based navigation
- Use sheet for modals
- Handle deep linking

**Pattern:**

```swift
// ✅ GOOD: Navigation
struct ContentView: View {
    @State private var path = NavigationPath()

    var body: some View {
        NavigationStack(path: $path) {
            UserListView()
                .navigationDestination(for: User.self) { user in
                    UserDetailView(user: user)
                }
        }
    }
}

// ✅ GOOD: Modal presentation
struct UserListView: View {
    @State private var showingAddUser = false

    var body: some View {
        List {
            // List content
        }
        .toolbar {
            Button("Add User") {
                showingAddUser = true
            }
        }
        .sheet(isPresented: $showingAddUser) {
            AddUserView()
        }
    }
}
```text

### Concurrency

**Swift concurrency:**

- Use async/await
- Use actors for thread-safe state
- Use @MainActor for UI updates
- Handle cancellation

**Pattern:**

```swift
// ✅ GOOD: Actor for thread safety
actor UserCache {
    private var cache: [String: User] = [:]

    func get(_ id: String) -> User? {
        cache[id]
    }

    func set(_ user: User) {
        cache[user.id] = user
    }

    func clear() {
        cache.removeAll()
    }
}

// ✅ GOOD: Task with cancellation
struct UserView: View {
    @State private var users: [User] = []

    var body: some View {
        List(users) { user in
            UserRow(user: user)
        }
        .task {
            do {
                users = try await loadUsers()
            } catch {
                print("Failed to load users: \(error)")
            }
        }
    }

    func loadUsers() async throws -> [User] {
        // This is automatically cancelled when view disappears
        try await userService.fetchUsers()
    }
}
```text

### Dependency Injection

**Inject dependencies:**

- Use protocols for abstractions
- Inject in initializers
- Use environment for SwiftUI
- Make code testable

**Pattern:**

```swift
// ✅ GOOD: Protocol abstraction
protocol UserServiceProtocol {
    func fetchUser(_ id: String) async throws -> User
}

class UserService: UserServiceProtocol {
    func fetchUser(_ id: String) async throws -> User {
        // Implementation
    }
}

// ✅ GOOD: Constructor injection
@MainActor
class UserViewModel: ObservableObject {
    private let userService: UserServiceProtocol

    init(userService: UserServiceProtocol = UserService.shared) {
        self.userService = userService
    }
}

// ✅ GOOD: Environment for SwiftUI
struct UserServiceKey: EnvironmentKey {
    static let defaultValue: UserServiceProtocol = UserService.shared
}

extension EnvironmentValues {
    var userService: UserServiceProtocol {
        get { self[UserServiceKey.self] }
        set { self[UserServiceKey.self] = newValue }
    }
}

// Usage
struct UserView: View {
    @Environment(\.userService) private var userService
}
```text

### Error Handling

**Handle errors properly:**

- Use Result type for success/failure
- Throw errors when appropriate
- Display errors to users
- Log errors for debugging

**Pattern:**

```swift
// ✅ GOOD: Custom errors
enum UserError: LocalizedError {
    case notFound
    case invalidData
    case networkError(Error)

    var errorDescription: String? {
        switch self {
        case .notFound:
            return "User not found"
        case .invalidData:
            return "Invalid user data"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        }
    }
}

// ✅ GOOD: Error handling in view
struct UserView: View {
    @State private var user: User?
    @State private var error: Error?

    var body: some View {
        Group {
            if let error = error {
                ErrorView(error: error) {
                    self.error = nil
                }
            } else if let user = user {
                UserDetailView(user: user)
            } else {
                ProgressView()
            }
        }
        .task {
            do {
                user = try await fetchUser()
            } catch {
                self.error = error
            }
        }
    }
}
```text

### Testing

**Testing best practices:**

- Unit test view models
- UI test critical flows
- Mock dependencies
- Test async code

**Pattern:**

```swift
// ✅ GOOD: Mock service
class MockUserService: UserServiceProtocol {
    var userToReturn: User?
    var errorToThrow: Error?

    func fetchUser(_ id: String) async throws -> User {
        if let error = errorToThrow {
            throw error
        }
        return userToReturn ?? User(id: id, name: "Test", email: "test@example.com")
    }
}

// ✅ GOOD: Unit test
@MainActor
final class UserViewModelTests: XCTestCase {
    func testLoadUserSuccess() async {
        let mockService = MockUserService()
        mockService.userToReturn = User(id: "123", name: "John", email: "john@example.com")

        let viewModel = UserViewModel(userService: mockService)
        await viewModel.loadUser()

        XCTAssertNotNil(viewModel.user)
        XCTAssertEqual(viewModel.user?.name, "John")
        XCTAssertNil(viewModel.error)
    }

    func testLoadUserFailure() async {
        let mockService = MockUserService()
        mockService.errorToThrow = UserError.notFound

        let viewModel = UserViewModel(userService: mockService)
        await viewModel.loadUser()

        XCTAssertNil(viewModel.user)
        XCTAssertNotNil(viewModel.error)
    }
}
```text

### Performance

**Optimize for performance:**

- Use lazy loading for heavy views
- Cache images and data
- Avoid unnecessary redraws
- Profile with Instruments

**Pattern:**

```swift
// ✅ GOOD: Image caching
class ImageCache {
    static let shared = ImageCache()
    private let cache = NSCache<NSString, UIImage>()

    func get(url: URL) -> UIImage? {
        cache.object(forKey: url.absoluteString as NSString)
    }

    func set(image: UIImage, for url: URL) {
        cache.setObject(image, forKey: url.absoluteString as NSString)
    }
}

// ✅ GOOD: Lazy loading
struct UserListView: View {
    @State private var users: [User] = []

    var body: some View {
        List(users) { user in
            LazyVStack {
                UserRow(user: user)
            }
        }
    }
}
```text

### Common Anti-Patterns

**Avoid:**

- Using force unwrapping (`!`) without safety
- Blocking main thread
- Retain cycles in closures
- Massive view controllers
- Not using async/await for network calls
- Ignoring memory warnings
- Not handling state restoration
- Hardcoding values instead of using constants
