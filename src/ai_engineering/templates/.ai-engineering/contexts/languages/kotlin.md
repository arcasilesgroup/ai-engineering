## Kotlin Best Practices

### Null Safety

**Kotlin's null safety system:**

- Non-nullable by default: `String` cannot be null
- Nullable types with `?`: `String?` can be null
- Safe call operator `?.` for safe access
- Elvis operator `?:` for default values
- `!!` for asserting non-null (avoid unless certain)

**Pattern:**

```kotlin
// ✅ GOOD: Null safety
fun processUser(user: User?) {
    // Safe call
    val name = user?.name

    // Elvis operator
    val displayName = user?.name ?: "Guest"

    // Safe let
    user?.let {
        println(it.name)
    }
}

// ❌ BAD: Force unwrap
val name = user!!.name  // Crashes if user is null
```text

### Data Classes

**Use data classes for models:**

- Automatic `equals()`, `hashCode()`, `toString()`
- `copy()` method for immutable updates
- Destructuring support
- Keep them immutable with `val`

**Pattern:**

```kotlin
// ✅ GOOD: Immutable data class
data class User(
    val id: String,
    val name: String,
    val email: String
)

// Usage
val user = User("1", "John", "john@example.com")
val updated = user.copy(name = "Jane")

// Destructuring
val (id, name, email) = user
```text

### Coroutines

**Structured concurrency:**

- Use `suspend` functions for async operations
- Use `launch` for fire-and-forget
- Use `async`/`await` for results
- Use `withContext` to switch dispatchers
- Always use structured concurrency (scopes)

**Pattern:**

```kotlin
// ✅ GOOD: Suspend function
suspend fun fetchUser(id: String): User {
    return withContext(Dispatchers.IO) {
        api.getUser(id)
    }
}

// ✅ GOOD: Structured concurrency
viewModelScope.launch {
    try {
        val user = fetchUser("123")
        updateUI(user)
    } catch (e: Exception) {
        handleError(e)
    }
}

// ✅ GOOD: Parallel async
val user = async { fetchUser(id) }
val profile = async { fetchProfile(id) }
Result(user.await(), profile.await())
```text

### Extension Functions

**Extend types cleanly:**

- Add functionality to existing classes
- Keep focused and cohesive
- Prefer extension over utility classes
- Use receiver type for clarity

**Pattern:**

```kotlin
// ✅ GOOD: Extension function
fun String.isValidEmail(): Boolean {
    return contains("@") && contains(".")
}

// Usage
if (email.isValidEmail()) {
    sendEmail(email)
}

// ✅ GOOD: Extension on nullable type
fun String?.orDefault(default: String): String {
    return this ?: default
}
```text

### When Expression

**Powerful pattern matching:**

- Exhaustive for enums and sealed classes
- Can be used as expression or statement
- Smart casts in branches
- Multiple conditions per branch

**Pattern:**

```kotlin
// ✅ GOOD: When as expression
val message = when (status) {
    Status.ACTIVE -> "User is active"
    Status.INACTIVE -> "User is inactive"
    Status.PENDING -> "User is pending"
}

// ✅ GOOD: Smart cast
when (val result = fetchUser()) {
    is Success -> println(result.data)
    is Error -> println(result.message)
}

// ✅ GOOD: Multiple conditions
when (value) {
    0, 1 -> "Small"
    in 2..10 -> "Medium"
    else -> "Large"
}
```text

### Sealed Classes

**Type-safe hierarchies:**

- Restricted class hierarchies
- Exhaustive when expressions
- Great for representing states/results
- All subclasses must be in same file

**Pattern:**

```kotlin
// ✅ GOOD: Sealed class for result
sealed class Result<out T> {
    data class Success<T>(val data: T) : Result<T>()
    data class Error(val message: String) : Result<Nothing>()
    object Loading : Result<Nothing>()
}

// Exhaustive when
fun handleResult(result: Result<User>) {
    when (result) {
        is Result.Success -> println(result.data)
        is Result.Error -> println(result.message)
        Result.Loading -> showLoading()
    }
}
```text

### Collections

**Functional operations:**

- Use immutable collections by default: `List`, `Map`, `Set`
- Use mutable only when needed: `MutableList`, `MutableMap`
- Chain operations: `filter`, `map`, `reduce`
- Use sequences for lazy evaluation

**Pattern:**

```kotlin
// ✅ GOOD: Immutable by default
val users: List<User> = listOf(...)

// ✅ GOOD: Functional operations
val activeNames = users
    .filter { it.isActive }
    .map { it.name }
    .sorted()

// ✅ GOOD: Sequence for large collections
val result = users.asSequence()
    .filter { it.isActive }
    .map { it.name }
    .take(10)
    .toList()
```text

### Scope Functions

**Choose the right scope function:**

- `let`: Transform object, null safety
- `run`: Execute block, return result
- `with`: Call multiple methods on object
- `apply`: Configure object, return object
- `also`: Side effects, return object

**Pattern:**

```kotlin
// ✅ GOOD: let for null safety
user?.let {
    println(it.name)
    updateDatabase(it)
}

// ✅ GOOD: apply for configuration
val user = User().apply {
    name = "John"
    email = "john@example.com"
}

// ✅ GOOD: also for side effects
val saved = user.also {
    log("Saving user: ${it.name}")
}.save()
```text

### Delegation

**Delegate properties and implementations:**

- `by lazy` for lazy initialization
- `by` for interface delegation
- Custom delegates for reusable behavior
- Observable properties

**Pattern:**

```kotlin
// ✅ GOOD: Lazy initialization
val database: Database by lazy {
    createDatabase()
}

// ✅ GOOD: Interface delegation
class Repository(
    private val api: ApiService
) : ApiService by api {
    // Can override specific methods
    override fun getUser(id: String) = api.getUser(id)
}
```text

### Type System

**Leverage Kotlin's type system:**

- Use type aliases for clarity
- Prefer sealed classes over enums for complex states
- Use inline classes for type safety without overhead
- Use reified type parameters in inline functions

**Pattern:**

```kotlin
// ✅ GOOD: Type alias
typealias UserId = String
typealias UserMap = Map<UserId, User>

// ✅ GOOD: Inline class (value class)
@JvmInline
value class Email(val value: String)

// ✅ GOOD: Reified generics
inline fun <reified T> Gson.fromJson(json: String): T {
    return fromJson(json, T::class.java)
}
```text

### Naming Conventions

**Kotlin style:**

- `camelCase` for functions, variables, parameters
- `PascalCase` for classes, interfaces, objects
- `UPPER_SNAKE_CASE` for constants
- Prefix interfaces with `I` is discouraged
- Use descriptive names, avoid abbreviations

### Object Declarations

**Singletons and companions:**

- `object` for singletons
- `companion object` for static-like members
- Anonymous objects for one-off implementations

**Pattern:**

```kotlin
// ✅ GOOD: Singleton
object NetworkManager {
    fun connect() { }
}

// ✅ GOOD: Companion for factory
class User(val name: String) {
    companion object {
        fun create(name: String): User {
            return User(name)
        }
    }
}

// Usage: User.create("John")
```text

### Android-Specific

**Android best practices:**

- Use `viewModelScope` for ViewModels
- Use `lifecycleScope` for lifecycle-aware coroutines
- Use `Flow` for reactive streams
- Use `StateFlow`/`SharedFlow` for state management
- Use View Binding instead of findViewById

**Pattern:**

```kotlin
// ✅ GOOD: ViewModel with Flow
class UserViewModel : ViewModel() {
    private val _users = MutableStateFlow<List<User>>(emptyList())
    val users: StateFlow<List<User>> = _users.asStateFlow()

    fun loadUsers() {
        viewModelScope.launch {
            _users.value = repository.getUsers()
        }
    }
}

// ✅ GOOD: Collect in Fragment
viewLifecycleOwner.lifecycleScope.launch {
    viewModel.users.collect { users ->
        updateUI(users)
    }
}
```text

### Common Anti-Patterns

**Avoid:**

- Using `!!` operator (prefer safe calls or elvis)
- Mutable collections everywhere (prefer immutable)
- Ignoring coroutine exceptions
- Blocking main thread with `runBlocking`
- Not using data classes for models
- Java-style getters/setters (use properties)
- `lateinit var` when nullable would work
