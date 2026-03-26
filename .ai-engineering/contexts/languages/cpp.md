## C++ Best Practices

### Modern C++ Standard

**Target C++17 minimum, prefer C++20 features where available:**

- Use `std::optional` instead of sentinel values or output parameters
- Use `std::variant` instead of unions or type tags with void pointers
- Use `std::string_view` for non-owning string parameters
- Use structured bindings: `auto [key, value] = map_entry;`
- Use `if constexpr` for compile-time branching
- Use `std::filesystem` for path operations (not raw string manipulation)
- Use `constexpr` functions where possible for compile-time evaluation

### Memory Management

**Smart pointers over raw pointers -- always:**

- `std::unique_ptr` for exclusive ownership (default choice)
- `std::shared_ptr` only when ownership is genuinely shared
- `std::weak_ptr` to break circular references
- Never use `new`/`delete` directly -- use `std::make_unique` / `std::make_shared`

**RAII (Resource Acquisition Is Initialization):**

- Wrap every resource (files, sockets, locks, handles) in an RAII class
- Destructors handle cleanup -- no explicit release calls needed
- If a class manages a resource, implement the Rule of Five (or `= delete` what you don't need)

**Common mistakes:**

```cpp
// BAD: raw new/delete, exception-unsafe
Widget* w = new Widget();
process(w);
delete w;

// GOOD: RAII via unique_ptr
auto w = std::make_unique<Widget>();
process(*w);
// Automatically cleaned up
```

### Naming Conventions

**Consistent naming:**

- `PascalCase` for types, classes, structs, enums, and template parameters
- `snake_case` for functions, methods, variables, and namespaces
- `UPPER_SNAKE_CASE` for constants and macros
- `k` prefix for compile-time constants if project convention: `kMaxRetries`
- Prefix member variables with `m_` or suffix with `_` (be consistent per project)
- No Hungarian notation

**Examples:**

```cpp
class HttpClient {
public:
    void send_request(std::string_view url);
    [[nodiscard]] bool is_connected() const;

private:
    std::string base_url_;
    int max_retries_;
};

static constexpr int MAX_BUFFER_SIZE = 4096;
```

### Error Handling

**Choose one strategy per project and be consistent:**

**Exceptions (preferred for application code):**

- Throw by value, catch by const reference
- Use standard exception types or derive from `std::runtime_error`
- Mark functions that never throw as `noexcept`
- RAII ensures cleanup during stack unwinding

**Error codes / `std::expected` (preferred for library and embedded code):**

- Use `std::expected<T, E>` (C++23) or equivalent for recoverable errors
- Use `std::error_code` / `std::errc` for system-level errors
- Never ignore return values -- use `[[nodiscard]]`

**Anti-patterns:**

```cpp
// BAD: catch everything silently
try { do_work(); } catch (...) { }

// BAD: error codes without checking
auto result = open_file(path);  // Return value ignored

// GOOD: explicit handling
try {
    do_work();
} catch (const NetworkError& e) {
    log_error("Network failure: {}", e.what());
    throw;  // Re-throw if can't handle
}
```

### Const Correctness

**Apply const everywhere it is valid:**

- Pass by `const&` for read-only parameters larger than a pointer
- Mark methods that don't modify state as `const`
- Use `constexpr` for values computable at compile time
- Use `const_cast` only at API boundaries with legacy code (document why)

```cpp
// GOOD: const-correct interface
class Cache {
public:
    [[nodiscard]] std::optional<Value> get(std::string_view key) const;
    void put(std::string_view key, Value value);
    [[nodiscard]] size_t size() const noexcept;
};

// GOOD: constexpr for compile-time values
constexpr size_t hash(std::string_view sv) noexcept {
    size_t result = 0;
    for (char c : sv) result = result * 31 + c;
    return result;
}
```

### Concurrency

**Thread safety primitives:**

- Use `std::mutex` with `std::scoped_lock` (not `lock_guard` -- `scoped_lock` handles multiple mutexes)
- Use `std::shared_mutex` with `std::shared_lock` for read-heavy workloads
- Use `std::atomic` for simple shared counters and flags
- Use `std::jthread` (C++20) over `std::thread` for automatic joining
- Never detach threads in production code

**Common mistakes:**

```cpp
// BAD: manual lock/unlock (exception-unsafe)
mutex_.lock();
do_work();
mutex_.unlock();

// GOOD: scoped lock (RAII)
{
    std::scoped_lock lock(mutex_);
    do_work();
}

// BAD: data race -- no synchronization
int counter = 0;
// Thread 1: counter++;
// Thread 2: counter++;

// GOOD: atomic for simple shared state
std::atomic<int> counter{0};
// Thread 1: counter.fetch_add(1, std::memory_order_relaxed);
```

### Move Semantics

**Enable efficient resource transfer:**

- Implement move constructor and move assignment for resource-owning types
- Use `std::move` to transfer ownership explicitly
- After moving, leave the source in a valid but unspecified state
- Mark moved-from objects and don't use them

```cpp
// GOOD: move-aware container usage
std::vector<std::string> names;
std::string name = build_name();
names.push_back(std::move(name));
// name is now empty -- don't read it

// GOOD: move constructor
class Buffer {
public:
    Buffer(Buffer&& other) noexcept
        : data_(std::exchange(other.data_, nullptr))
        , size_(std::exchange(other.size_, 0)) {}
};
```

### Templates and Generic Code

**Keep templates simple and constrained:**

- Use `concepts` (C++20) to constrain template parameters
- Use `static_assert` for compile-time validation in C++17
- Prefer `if constexpr` over SFINAE for conditional compilation
- Keep template definitions in headers (or use explicit instantiation)

```cpp
// GOOD: C++20 concepts
template<typename T>
concept Serializable = requires(T t) {
    { t.serialize() } -> std::convertible_to<std::string>;
};

template<Serializable T>
void save(const T& obj) {
    write_to_disk(obj.serialize());
}
```

### Common Pitfalls

**Undefined behavior -- always avoid:**

- Dangling references (returning reference to local variable)
- Iterator invalidation (modifying container while iterating)
- Signed integer overflow
- Uninitialized variables (use `{}` initialization)
- Use-after-move
- Buffer overflows (use `.at()` or range-based for loops)

**Dangling reference example:**

```cpp
// BAD: dangling reference
const std::string& get_name() {
    std::string name = "test";
    return name;  // UB: reference to destroyed local
}

// GOOD: return by value (RVO applies)
std::string get_name() {
    std::string name = "test";
    return name;
}
```

### Performance

**Optimize allocation and data layout:**

- Pass large objects by `const&`, small ones by value
- Reserve container capacity when size is known: `vec.reserve(n)`
- Prefer `std::array` over `std::vector` for fixed-size collections
- Prefer contiguous containers (`vector`, `array`) for cache locality
- Use `emplace_back` over `push_back` to construct in-place
- Avoid unnecessary copies -- profile with sanitizers before optimizing

**Move semantics for efficiency:**

```cpp
// GOOD: reserve + emplace
std::vector<Widget> widgets;
widgets.reserve(count);
for (const auto& config : configs) {
    widgets.emplace_back(config.name, config.size);
}
```

### Build and Tooling

**Compiler warnings (always enable):**

```
-Wall -Wextra -Wpedantic -Werror
-Wshadow -Wnon-virtual-dtor -Wold-style-cast
-Wcast-align -Wunused -Woverloaded-virtual
-Wconversion -Wsign-conversion -Wnull-dereference
```

**Static analysis:**

- `clang-tidy` with a `.clang-tidy` config (enable modernize-*, bugprone-*, performance-*)
- `cppcheck` for supplemental analysis
- `include-what-you-use` to minimize header dependencies

**Sanitizers (use in CI):**

- AddressSanitizer (`-fsanitize=address`): buffer overflows, use-after-free
- UndefinedBehaviorSanitizer (`-fsanitize=undefined`): signed overflow, null deref
- ThreadSanitizer (`-fsanitize=thread`): data races
- MemorySanitizer (`-fsanitize=memory`): uninitialized reads

### Testing Patterns

**Google Test / Catch2:**

- One test file per source file: `widget.cpp` -> `widget_test.cpp`
- Use descriptive test names: `TEST(Cache, returns_empty_optional_for_missing_key)`
- Use test fixtures for shared setup/teardown
- Test edge cases: empty input, max values, boundary conditions
- Use mocking frameworks (Google Mock) for dependency isolation

```cpp
// Google Test example
TEST(HttpClient, throws_on_connection_timeout) {
    HttpClient client(Config{.timeout_ms = 1});
    EXPECT_THROW(client.get("http://slow-server"), TimeoutError);
}

TEST(Parser, handles_empty_input) {
    auto result = parse("");
    EXPECT_FALSE(result.has_value());
}
```

### Header Hygiene

**Minimize include dependencies:**

- Use forward declarations where possible
- Include what you use, don't rely on transitive includes
- Use `#pragma once` or include guards
- Keep headers self-contained (each header compiles independently)
- Prefer `<iosfwd>` over `<iostream>` in headers

### Anti-Patterns

**Avoid these:**

- C-style casts (`(int)x`) -- use `static_cast`, `dynamic_cast`, `reinterpret_cast`
- Macros for constants or functions -- use `constexpr` and `inline`
- Global mutable state -- use dependency injection
- Deep inheritance hierarchies -- prefer composition
- `std::endl` for newlines -- use `'\n'` (avoids unnecessary flush)
- Raw arrays -- use `std::array` or `std::vector`
- `void*` for type erasure -- use `std::any`, `std::variant`, or templates
