# Handler: Language -- C++

## Purpose

Language-specific review for C++ code. Supplements the 8-concern review agents with memory safety checks, RAII enforcement, concurrency hazard detection, and modern C++ idiom validation.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect C++ Scope

1. Identify `.cpp`, `.cc`, `.cxx`, `.hpp`, `.h`, `.hxx` files in the diff
2. If no C++ files, skip this handler entirely
3. Detect C++ standard from build configuration:
   - `CMakeLists.txt`: `CMAKE_CXX_STANDARD` or `CXX_STANDARD` property
   - `Makefile` / compiler flags: `-std=c++17`, `-std=c++20`, etc.
4. Detect libraries from includes:
   - `<thread>`, `<mutex>`, `<atomic>` -> enable concurrency checks
   - `<memory>` -> validate smart pointer usage
   - Qt / Boost / Abseil headers -> enable framework-specific checks
5. Read `.ai-engineering/contexts/languages/cpp.md` if not already loaded

### Step 2 -- Critical Findings (severity: critical)

**Raw new/delete (manual memory management)**
```cpp
// BAD: manual lifetime management
Widget* w = new Widget();
// ... 50 lines later, maybe ...
delete w;  // easy to forget, double-delete, or use-after-free

// GOOD: smart pointers
auto w = std::make_unique<Widget>();
auto shared = std::make_shared<Widget>();
```
- Confidence 90% in application code
- Acceptable in custom allocators, low-level libraries with documented ownership model

**C-style arrays, strcpy, sprintf**
```cpp
// BAD: buffer overflow risks
char buffer[256];
strcpy(buffer, user_input);          // no bounds checking
sprintf(buffer, "Hello %s", name);   // no bounds checking
int arr[100];                        // stack array, no bounds checking

// GOOD: safe alternatives
std::string buffer = user_input;
auto result = std::format("Hello {}", name);  // C++20
std::vector<int> arr(100);
std::array<int, 100> fixed_arr;
```
- Flag: `strcpy`, `strcat`, `sprintf`, `gets`, `scanf` without width specifier

**Dangling pointers and references**
```cpp
// BAD: dangling reference
const std::string& getName() {
    std::string name = computeName();
    return name;  // reference to local destroyed on return
}

// BAD: dangling pointer
int* getValues() {
    int values[10] = {1, 2, 3};
    return values;  // pointer to stack memory
}

// BAD: iterator invalidation
std::vector<int> vec = {1, 2, 3};
auto it = vec.begin();
vec.push_back(4);  // may invalidate it
*it;               // undefined behavior
```

**Uninitialized variables**
```cpp
// BAD: undefined behavior
int count;
if (condition) count = 10;
use(count);  // uninitialized if condition is false

// GOOD: always initialize
int count = 0;
```
- Confidence 85%: compilers warn but may miss complex control flow

**Missing RAII for resources**
```cpp
// BAD: resource leak on exception
FILE* f = fopen("data.bin", "rb");
process(f);  // if this throws, f is never closed
fclose(f);

// GOOD: RAII wrapper
auto f = std::unique_ptr<FILE, decltype(&fclose)>(
    fopen("data.bin", "rb"), &fclose);
// or use std::ifstream
std::ifstream file("data.bin", std::ios::binary);
```
- Flag raw handles: file descriptors, sockets, mutexes, GPU resources without RAII wrappers

**Null pointer dereference potential**
```cpp
// BAD: no null check
Widget* w = findWidget(id);
w->update();  // crashes if findWidget returns nullptr

// GOOD: check or use optional
Widget* w = findWidget(id);
if (w == nullptr) {
    return Error::NotFound;
}
w->update();

// BETTER (C++17): std::optional
std::optional<Widget> w = findWidget(id);
if (w.has_value()) {
    w->update();
}
```

**User input in printf format string**
```cpp
// BAD: format string attack
printf(user_input);          // attacker controls format string
syslog(LOG_ERR, user_input); // same vulnerability

// GOOD: format string is a literal
printf("%s", user_input);
syslog(LOG_ERR, "%s", user_input);
```

**reinterpret_cast usage**
```cpp
// SUSPICIOUS: type punning, often undefined behavior
auto* data = reinterpret_cast<SomeType*>(raw_bytes);

// Prefer: std::bit_cast (C++20) or memcpy for type punning
SomeType data;
std::memcpy(&data, raw_bytes, sizeof(SomeType));
```
- Confidence 75%: sometimes necessary for hardware interfaces, serialization
- Must have a comment justifying why `static_cast` or `std::bit_cast` cannot be used

### Step 3 -- High Findings (severity: major)

**Data races**
```cpp
// BAD: concurrent write without synchronization
// Thread 1:
counter++;
// Thread 2:
counter++;

// GOOD: atomic or mutex
std::atomic<int> counter{0};
counter.fetch_add(1);

// or
std::mutex mtx;
{
    std::lock_guard<std::mutex> lock(mtx);
    counter++;
}
```
- Flag shared mutable state accessed from multiple threads without `std::atomic`, `std::mutex`, or documented single-threaded guarantee

**Deadlock potential**
```cpp
// BAD: lock ordering inconsistency
void funcA() { lock(mu1); lock(mu2); }
void funcB() { lock(mu2); lock(mu1); }  // deadlock!

// GOOD: consistent ordering or std::scoped_lock
void funcA() {
    std::scoped_lock lock(mu1, mu2);  // deadlock-free
}
```

**Manual mutex lock/unlock**
```cpp
// BAD: exception-unsafe
mutex.lock();
doWork();    // if this throws, mutex stays locked
mutex.unlock();

// GOOD: RAII lock guard
{
    std::lock_guard<std::mutex> lock(mutex);
    doWork();
}
// or std::unique_lock when conditional locking is needed
```

**Detached threads without lifecycle management**
```cpp
// BAD: fire and forget, may access destroyed resources
std::thread([&data]() {
    process(data);  // data may be destroyed
}).detach();

// GOOD: managed lifetime
auto future = std::async(std::launch::async, [data_copy = data]() {
    process(data_copy);
});
future.get();  // or store future for later
```

### Step 4 -- Medium Findings (severity: minor)

**Pass by value vs const reference**
```cpp
// BAD: unnecessary copy
void process(std::string input) {    // copies the string
void process(std::vector<int> data); // copies the vector

// GOOD: const reference for read-only
void process(const std::string& input);
void process(const std::vector<int>& data);

// ALSO GOOD: by value when consuming (move)
void store(std::string input) {
    member_ = std::move(input);
}
```
- Flag non-trivial types (> 16 bytes or heap-allocating) passed by value when only read

**Missing move semantics**
```cpp
// BAD: copies when move would suffice
std::vector<Widget> createWidgets() {
    std::vector<Widget> result;
    // ... fill ...
    return result;  // OK: NRVO applies here
}
void Consumer::accept(std::vector<Widget> widgets) {
    data_ = widgets;  // BAD: should be std::move(widgets)
}
```

**const correctness**
- Member functions that do not modify state missing `const` qualifier
- Pointers/references that could be `const` but are not
- Confidence 50% (style preference with real safety benefits)

**using namespace std in headers**
```cpp
// BAD: pollutes every includer's namespace
// In widget.hpp:
using namespace std;

// GOOD: explicit qualification or limited using-declarations
std::string getName() const;
// or in .cpp implementation file
using std::string;
using std::vector;
```
- Confidence 90% in headers, 40% in `.cpp` files (acceptable in implementation)

**Missing virtual destructor in base classes**
```cpp
// BAD: undefined behavior when deleting through base pointer
class Base {
public:
    void doWork();  // non-virtual destructor
};
class Derived : public Base { /* ... */ };
Base* b = new Derived();
delete b;  // undefined behavior!

// GOOD
class Base {
public:
    virtual ~Base() = default;
};
```

### Step 5 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| Compiler warnings | `-Wall -Wextra -Wpedantic -Werror` | Uninitialized vars, implicit conversions, unused |
| clang-tidy | `clang-tidy {files} --checks='*'` | Modern C++ patterns, bugs, performance |
| cppcheck | `cppcheck --enable=all {files}` | Buffer overflows, null deref, memory leaks |
| AddressSanitizer | `-fsanitize=address` | Memory errors at runtime |
| ThreadSanitizer | `-fsanitize=thread` | Data races at runtime |
| Valgrind | `valgrind --tool=memcheck` | Memory leaks, invalid access |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-cpp-N
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
