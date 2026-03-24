---
name: ai-review
description: Use when reviewing code changes (PRs, diffs, or files) with parallel specialized agents. 8-agent review with self-challenge protocol and cross-agent corroboration.
effort: max
argument-hint: "review|find|learn [PR number or file paths]"
mode: agent
---



# Review

## Purpose

Parallel specialized code review. Dispatches 8 review agents, each analyzing the same code from a different angle. Every agent argues AGAINST its own findings (self-challenge). Cross-agent corroboration filters noise from signal.

## When to Use

- Before merging a PR
- After completing a feature (pre-commit review)
- When reviewing someone else's code
- Periodic architecture review

## Process

1. **Explore first** -- run `/ai-explore` on the changed files to build architectural context
2. **Dispatch reviewers** -- follow `handlers/review.md` (8 parallel specialized agents)
3. **Aggregate findings** -- correlate, deduplicate, confidence-score
4. **Self-challenge** -- each finding is argued against by its own agent
5. **Filter** -- drop solo findings below 40% confidence
6. **Report** -- produce review summary with actionable findings

See `handlers/review.md` for the full review workflow, `handlers/find.md` for finding existing reviews, and `handlers/learn.md` for the continuous improvement loop.

## Quick Reference

| Mode | What it does |
|------|-------------|
| `review` | Full parallel review (default) |
| `find` | Find and summarize existing review comments on a PR |
| `learn` | Extract lessons from past reviews for future improvement |

## The 8 Review Agents

| Agent | Focus | Looks for |
|-------|-------|-----------|
| Security | OWASP, injection, auth | SQL injection, XSS, auth bypass, secret exposure |
| Performance | Speed, memory, I/O | N+1 queries, O(n^2), memory leaks, blocking I/O |
| Correctness | Logic, edge cases | Off-by-one, null handling, race conditions, missing cases |
| Maintainability | Readability, complexity | God functions, deep nesting, unclear naming, magic numbers |
| Testing | Coverage, quality | Missing tests, weak assertions, testing implementation |
| Compatibility | Breaking changes, API | Public API changes, backward compat, deprecation |
| Architecture | Boundaries, patterns | Layer violations, circular deps, pattern inconsistency |
| Frontend | UX, a11y, rendering | Missing aria labels, layout shifts, unhandled states |

## Confidence Scoring

Each finding gets a confidence score (20-100%):

| Score | Meaning | Action |
|-------|---------|--------|
| 80-100% | High confidence, clear evidence | Must address |
| 60-79% | Moderate confidence | Should address |
| 40-59% | Low confidence, single agent | Consider |
| 20-39% | Solo finding, uncertain | Dropped unless critical severity |

**Corroboration bonus**: when 2+ agents flag the same issue, confidence increases by 20%.
**Solo penalty**: single-agent findings below 40% are dropped from the report.

## Self-Challenge Protocol

For each finding, the reviewing agent must:

1. **State the finding** (what is wrong)
2. **Argue against it** (why this might be acceptable)
3. **Resolve** (finding stands, confidence adjusted, or finding withdrawn)

Example:
```
Finding: Function handles 5 different concerns (god function)
Counter: This is a CLI command handler -- some breadth is expected in the entry point
Resolution: Finding stands but severity reduced to minor. The handler delegates
  to helpers for the complex logic. Confidence: 55%
```

## Common Mistakes

- Reviewing without architectural context (always explore first)
- Treating all findings equally (use confidence scoring)
- Not self-challenging (every finding must be argued against)
- Reviewing only the diff without understanding the surrounding code
- Flagging style preferences as bugs

## Integration

- **Called by**: user directly, `/ai-pr` (pre-merge review)
- **Calls**: `/ai-explore` (context), `handlers/review.md`, `handlers/find.md`, `handlers/learn.md`
- **Read-only**: never modifies code -- produces review findings

$ARGUMENTS

---

# Handler: Find Reviews

## Purpose

Find and summarize existing review comments on a PR or in the codebase. Useful for understanding prior feedback before starting a new review.

## Procedure

### Step 1 -- Identify Source

Determine where to look for reviews:

- **PR number provided**: use `gh api repos/{owner}/{repo}/pulls/{number}/comments` to fetch PR comments
- **No PR number**: check `git log --format='%H %s' -20` for recent review-related commits
- **File paths provided**: search for TODO/FIXME/HACK/REVIEW comments in those files

### Step 2 -- Collect Comments

For PR comments:
1. Fetch all review comments via GitHub API
2. Group by file and line number
3. Classify: approved, changes-requested, comment-only

For inline comments in code:
1. Grep for review markers: `TODO`, `FIXME`, `HACK`, `REVIEW`, `XXX`
2. Include surrounding context (3 lines before/after)
3. Check git blame for age and author

### Step 3 -- Summarize

Produce a summary grouped by theme:

```markdown
## Review Comments Summary

### Open Issues (N)
- [file:line] [severity] [comment summary]

### Resolved (N)
- [file:line] [what was resolved]

### Patterns
- [recurring themes across comments]
```

### Step 4 -- Feed Forward

If transitioning to a new review (`/ai-review review`), carry forward:
- Unresolved issues from prior reviews (check if they still apply)
- Recurring patterns (things this codebase gets wrong repeatedly)

---

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

---

# Handler: Language -- Flutter/Dart

## Purpose

Language-specific review for Flutter and Dart code. Supplements the 8-concern review agents with state management agnostic checks (BLoC, Riverpod, GetX), widget composition patterns, resource lifecycle management, accessibility enforcement, and i18n readiness.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Flutter Scope

1. Identify `.dart` files in the diff
2. If no Dart files, skip this handler entirely
3. Check `pubspec.yaml` for dependencies:
   - `flutter_bloc` / `bloc` -> BLoC state management context
   - `flutter_riverpod` / `riverpod` -> Riverpod context
   - `get` / `getx` -> GetX context
   - `provider` -> Provider context
4. Detect architecture from directory structure:
   - `lib/domain/`, `lib/data/`, `lib/presentation/` -> clean architecture
   - `lib/features/` -> feature-first organization
5. Read `.ai-engineering/contexts/languages/dart.md` or `flutter.md` if not already loaded

### Step 2 -- Critical Findings (severity: critical)

**Boolean flag soup instead of sealed state**
```dart
// BAD: combinatorial explosion, impossible states representable
class UserState {
  final bool isLoading;
  final bool isError;
  final bool hasData;
  final String? errorMessage;
  final User? user;
  // Can represent isLoading=true AND isError=true -- nonsensical!
}

// GOOD: sealed class makes impossible states unrepresentable
sealed class UserState {}
class UserInitial extends UserState {}
class UserLoading extends UserState {}
class UserLoaded extends UserState {
  final User user;
  UserLoaded(this.user);
}
class UserError extends UserState {
  final String message;
  UserError(this.message);
}
```
- Flag: classes with 2+ boolean state flags (`isLoading`, `isError`, `hasData`, `isEmpty`)
- Confidence 85%: nearly always a design problem

**Non-exhaustive state handling**
```dart
// BAD: misses states silently
Widget build(BuildContext context) {
  if (state is UserLoading) return CircularProgressIndicator();
  if (state is UserLoaded) return UserView(state.user);
  return SizedBox.shrink();  // silently swallows errors!
}

// GOOD: exhaustive switch (Dart 3+)
Widget build(BuildContext context) {
  return switch (state) {
    UserInitial() => const Text('Welcome'),
    UserLoading() => const CircularProgressIndicator(),
    UserLoaded(:final user) => UserView(user: user),
    UserError(:final message) => ErrorView(message: message),
  };
}
```
- Flag: if/else chains or switch without exhaustive state coverage

**Stream and subscription leaks**
```dart
// BAD: never cancelled
class MyWidget extends StatefulWidget {
  @override
  State<MyWidget> createState() => _MyWidgetState();
}
class _MyWidgetState extends State<MyWidget> {
  @override
  void initState() {
    super.initState();
    stream.listen((data) {  // never cancelled!
      setState(() => _data = data);
    });
  }
}

// GOOD: cancel in dispose
class _MyWidgetState extends State<MyWidget> {
  late final StreamSubscription _subscription;

  @override
  void initState() {
    super.initState();
    _subscription = stream.listen((data) {
      setState(() => _data = data);
    });
  }

  @override
  void dispose() {
    _subscription.cancel();
    super.dispose();
  }
}
```
- Flag: `.listen()` without corresponding `.cancel()` in `dispose()`
- Flag: `StreamController` created without `.close()` in `dispose()`
- Flag: `AnimationController`, `TextEditingController`, `ScrollController` without `dispose()`

**.listen() called inside build()**
```dart
// BAD: creates new subscription every rebuild
@override
Widget build(BuildContext context) {
  stream.listen((data) {  // called every rebuild!
    setState(() {});
  });
  return Container();
}

// GOOD: listen in initState or use StreamBuilder
@override
Widget build(BuildContext context) {
  return StreamBuilder<Data>(
    stream: stream,
    builder: (context, snapshot) => /* ... */,
  );
}
```

**Domain layer importing Flutter**
```dart
// BAD: domain depends on framework
import 'package:flutter/material.dart';  // in domain/

// Domain should only import dart:core, dart:async, dart:collection
// and other domain-layer packages
```
- Scan files under `lib/domain/` for `package:flutter/` imports

### Step 3 -- High Findings (severity: major)

**_build helper methods instead of widget extraction**
```dart
// BAD: private build methods prevent framework optimization
class MyWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(children: [
      _buildHeader(),   // cannot be independently rebuilt
      _buildContent(),  // no separate Element in widget tree
    ]);
  }

  Widget _buildHeader() => /* ... */;
  Widget _buildContent() => /* ... */;
}

// GOOD: extract to separate widgets
class MyWidget extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Column(children: [
      HeaderWidget(),   // separate Element, independent rebuild
      ContentWidget(),  // framework can skip if unchanged
    ]);
  }
}
```
- Flag `_build*()` methods that return `Widget` -- recommend extraction to separate widget classes

**Missing const constructors**
```dart
// BAD: rebuilt unnecessarily
return Padding(
  padding: EdgeInsets.all(16),
  child: Text('Hello'),
);

// GOOD: const enables compile-time optimization
return const Padding(
  padding: EdgeInsets.all(16),
  child: Text('Hello'),
);
```
- Flag widget constructors that could be `const` but are not
- Flag custom widget classes missing `const` constructor when all fields are final

**MediaQuery.of overuse causing unnecessary rebuilds**
```dart
// BAD: rebuilds on ANY MediaQuery change (keyboard, orientation, etc.)
final width = MediaQuery.of(context).size.width;

// GOOD: targeted query (Flutter 3.10+)
final width = MediaQuery.sizeOf(context).width;
// Even better for specific properties:
final padding = MediaQuery.paddingOf(context);
```

**BuildContext used after await**
```dart
// BAD: context may be invalid after async gap
onPressed: () async {
  await fetchData();
  if (!mounted) return;  // required check!
  Navigator.of(context).push(/* ... */);
}

// GOOD: check mounted
onPressed: () async {
  await fetchData();
  if (!context.mounted) return;  // Dart 3.7+
  Navigator.of(context).push(/* ... */);
}
```

**Missing ErrorBoundary-equivalent setup**
- No `ErrorWidget.builder` override for release mode
- No `FlutterError.onError` handler configured
- No `PlatformDispatcher.instance.onError` for async errors

### Step 4 -- Medium Findings (severity: minor)

**! bang operator overuse**
```dart
// BAD: crash on null
final name = user!.name;

// GOOD: safe access
final name = user?.name ?? 'Unknown';
```
- Confidence 70% in widget code, 50% in test code
- Acceptable immediately after null check in same scope

**Overly broad catch**
```dart
// BAD: swallows everything
try {
  await fetchData();
} catch (e) {
  // catches TypeError, RangeError, everything
}

// GOOD: specific exceptions
try {
  await fetchData();
} on NetworkException catch (e) {
  showError(e.message);
} on TimeoutException {
  showRetryDialog();
}
```

**late overuse**
```dart
// BAD: runtime error if accessed before initialization
late final UserService _userService;

// GOOD: nullable with explicit initialization check, or constructor injection
final UserService? _userService;
// or
required this.userService  // constructor parameter
```
- Flag `late` fields that could be constructor parameters or nullable

**Unawaited futures**
```dart
// BAD: fire and forget, errors silently lost
fetchData();  // returns Future but not awaited

// GOOD: explicit
await fetchData();
// or intentionally fire-and-forget with annotation
unawaited(analytics.track('event'));
```

### Step 5 -- Accessibility Checks

**Missing semantic labels**
```dart
// BAD: icon button with no semantic meaning for screen readers
IconButton(
  icon: Icon(Icons.delete),
  onPressed: _deleteItem,
)

// GOOD: semantic label
IconButton(
  icon: Icon(Icons.delete),
  onPressed: _deleteItem,
  tooltip: 'Delete item',  // also serves as semantic label
)
// or
Semantics(
  label: 'Delete item',
  child: IconButton(/* ... */),
)
```

**Tap targets below 48x48**
```dart
// BAD: too small for accessibility
SizedBox(
  width: 24,
  height: 24,
  child: GestureDetector(onTap: _handleTap),
)

// GOOD: minimum 48x48 logical pixels
SizedBox(
  width: 48,
  height: 48,
  child: GestureDetector(onTap: _handleTap),
)
```
- Flag interactive widgets (`GestureDetector`, `InkWell`, `IconButton`) with explicit size constraints below 48x48

### Step 6 -- Internationalization Checks

**Hardcoded strings in UI**
```dart
// BAD: not localizable
Text('Submit Order')
AppBar(title: Text('Settings'))

// GOOD: localized
Text(AppLocalizations.of(context)!.submitOrder)
// or with intl package
Text(S.of(context).submitOrder)
```
- Flag string literals passed directly to `Text()`, `AppBar(title:)`, tooltip, label, hint parameters
- Acceptable: debug widgets, developer-facing strings, log messages

### Step 7 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| dart analyze | `dart analyze` | Type safety, unused imports, style |
| flutter test | `flutter test --coverage` | Test coverage |
| dart fix | `dart fix --dry-run` | Automated fix suggestions |
| custom_lint | Per `analysis_options.yaml` | Project-specific rules |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-flutter-N
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

---

# Handler: Language -- Go

## Purpose

Language-specific review for Go code. Supplements the 8-concern review agents with Go-idiomatic checks, concurrency safety patterns, and diagnostic tool integration.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Go Scope

1. Identify `.go` files in the diff
2. If no Go files, skip this handler entirely
3. Check `go.mod` for module path and Go version
4. Detect frameworks from imports:
   - `net/http` / `gin` / `echo` / `chi` -> enable HTTP handler checks
   - `database/sql` / `gorm` / `sqlx` -> enable database checks
   - `grpc` -> enable gRPC checks
5. Read `.ai-engineering/contexts/languages/go.md` if not already loaded

### Step 2 -- Critical Findings (severity: critical)

**SQL string concatenation**
```go
// BAD: SQL injection
db.Query("SELECT * FROM users WHERE id = '" + userID + "'")
db.Query(fmt.Sprintf("SELECT * FROM users WHERE id = '%s'", userID))

// GOOD: parameterized
db.Query("SELECT * FROM users WHERE id = $1", userID)
db.QueryRow("SELECT * FROM users WHERE id = ?", userID)
```

**Blank identifier discarding errors**
```go
// BAD: error silently ignored
result, _ := riskyOperation()
_ = file.Close() // in cases where close errors matter (writes)

// GOOD: handle the error
result, err := riskyOperation()
if err != nil {
    return fmt.Errorf("risky operation failed: %w", err)
}
```
- Confidence 90% for I/O, network, database operations
- Confidence 50% for known-safe operations (e.g., `fmt.Fprintf` to `bytes.Buffer`)

**panic() for recoverable errors**
```go
// BAD: crashes the process
if config == nil {
    panic("config is nil")
}

// GOOD: return error
if config == nil {
    return nil, fmt.Errorf("config must not be nil")
}
```
- Acceptable in `init()` functions and test helpers only

**Missing errors.Is / errors.As for error comparison**
```go
// BAD: breaks error wrapping
if err == sql.ErrNoRows {

// GOOD: unwraps wrapped errors
if errors.Is(err, sql.ErrNoRows) {
```

**Unchecked type assertions**
```go
// BAD: panics if wrong type
value := iface.(ConcreteType)

// GOOD: comma-ok pattern
value, ok := iface.(ConcreteType)
if !ok {
    return fmt.Errorf("expected ConcreteType, got %T", iface)
}
```

### Step 3 -- High Findings (severity: major)

**Goroutine leaks**
```go
// BAD: goroutine never terminates
go func() {
    for {
        data := <-ch // blocks forever if ch is never closed
        process(data)
    }
}()

// GOOD: context cancellation or done channel
go func() {
    for {
        select {
        case data, ok := <-ch:
            if !ok {
                return
            }
            process(data)
        case <-ctx.Done():
            return
        }
    }
}()
```

**Unbuffered channel deadlock potential**
- Sending on unbuffered channel without a guaranteed receiver
- Channel created but never read from in any visible code path

**Missing sync.WaitGroup for goroutine coordination**
- Multiple goroutines launched without WaitGroup, errgroup, or other synchronization
- Goroutines outliving the function that spawned them without lifecycle management

**Mutex misuse**
```go
// BAD: Lock without guaranteed Unlock
mu.Lock()
doWork() // if this panics, mutex stays locked

// GOOD: defer immediately
mu.Lock()
defer mu.Unlock()
doWork()
```
- Also flag: copying a mutex (passed by value instead of pointer)

**Missing error wrapping context**
```go
// BAD: no context
if err != nil {
    return err
}

// GOOD: context for debugging
if err != nil {
    return fmt.Errorf("loading user %d: %w", id, err)
}
```

### Step 4 -- Medium Findings (severity: minor)

**String building in loops**
```go
// BAD: O(n^2) string allocation
result := ""
for _, s := range items {
    result += s
}

// GOOD: strings.Builder
var b strings.Builder
for _, s := range items {
    b.WriteString(s)
}
result := b.String()
```

**Slice pre-allocation**
```go
// BAD: multiple reallocations
var result []Item
for _, raw := range rawItems {
    result = append(result, convert(raw))
}

// GOOD: pre-allocate
result := make([]Item, 0, len(rawItems))
for _, raw := range rawItems {
    result = append(result, convert(raw))
}
```

**Context as first parameter**
```go
// BAD: ctx not first
func ProcessOrder(order Order, ctx context.Context) error {

// GOOD: ctx first, per convention
func ProcessOrder(ctx context.Context, order Order) error {
```

**Table-driven tests**
- Test functions with repeated setup/assertion patterns -> suggest table-driven format
- Confidence 50% (style preference, not a bug)

**Exported functions missing doc comments**
- Per `go doc` conventions, exported names should have comments starting with the name

### Step 5 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| go vet | `go vet ./...` | Correctness findings (printf args, struct tags, unreachable code) |
| staticcheck | `staticcheck ./...` | Style, performance, correctness |
| go build -race | `go build -race ./...` | Data race findings |
| govulncheck | `govulncheck ./...` | Known vulnerabilities in dependencies |
| golangci-lint | `golangci-lint run` | Aggregated linting |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-go-N
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

---

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

---

# Handler: Language -- Kotlin

## Purpose

Language-specific review for Kotlin code, with emphasis on Android/KMP architecture. Supplements the 8-concern review agents with clean architecture boundary enforcement, coroutine safety, Compose stability checks, and Android security patterns.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Kotlin Scope

1. Identify `.kt`, `.kts` files in the diff
2. If no Kotlin files, skip this handler entirely
3. Detect project type from build files and imports:
   - `build.gradle.kts` with `com.android.application` -> Android app
   - `build.gradle.kts` with `com.android.library` -> Android library
   - `@Composable` imports -> enable Compose checks
   - `kotlinx.coroutines` imports -> enable coroutine checks
   - Multi-module project -> enable module boundary checks
4. Read `.ai-engineering/contexts/languages/kotlin.md` if not already loaded
5. Map module structure: identify `domain`, `data`, `presentation`, `app` modules

### Step 2 -- Critical Findings (severity: critical)

**Domain module importing framework**
```kotlin
// BAD: domain module depends on Android/framework
// In domain/src/main/kotlin/com/example/domain/usecase/GetUserUseCase.kt
import android.content.Context         // framework leak
import androidx.lifecycle.ViewModel    // presentation concern
import retrofit2.Response              // data layer concern

// GOOD: domain depends only on Kotlin stdlib and domain interfaces
import com.example.domain.repository.UserRepository
import com.example.domain.model.User
```
- Scan import statements in files under `domain/` module paths
- Confidence 95%: this is a fundamental architecture violation

**Data entities leaking to presentation layer**
```kotlin
// BAD: API/DB entity used directly in UI
@Composable
fun UserScreen(user: UserApiResponse) {  // data layer type in UI

// GOOD: mapped to domain/presentation model
@Composable
fun UserScreen(user: UserUiModel) {
```
- Flag data-layer types (`Entity`, `Dto`, `Response`, `ApiModel`) in Composable parameters or ViewModel state

**Business logic in ViewModel**
```kotlin
// BAD: ViewModel contains business rules
class OrderViewModel : ViewModel() {
    fun placeOrder(items: List<Item>) {
        val total = items.sumOf { it.price * it.quantity }
        val tax = total * 0.21  // business rule!
        val discount = if (total > 100) total * 0.1 else 0.0  // business rule!
        // ...
    }
}

// GOOD: delegated to use case
class OrderViewModel(
    private val placeOrderUseCase: PlaceOrderUseCase
) : ViewModel() {
    fun placeOrder(items: List<Item>) {
        viewModelScope.launch {
            placeOrderUseCase(items)
        }
    }
}
```
- Flag: calculations, conditionals, data transformations beyond simple UI state mapping

**Circular module dependencies**
- Module A imports from Module B AND Module B imports from Module A
- Check `build.gradle.kts` `dependencies` blocks and import statements across modules

### Step 3 -- High Findings (severity: major)

**GlobalScope usage**
```kotlin
// BAD: unstructured concurrency, outlives lifecycle
GlobalScope.launch {
    fetchData()
}

// GOOD: structured concurrency
viewModelScope.launch {
    fetchData()
}
// or
lifecycleScope.launch {
    fetchData()
}
// or inject a CoroutineScope
```

**Catching CancellationException without rethrow**
```kotlin
// BAD: breaks structured concurrency cancellation
try {
    suspendingWork()
} catch (e: Exception) {
    // CancellationException is caught here!
    logger.error("Failed", e)
}

// GOOD: rethrow CancellationException
try {
    suspendingWork()
} catch (e: CancellationException) {
    throw e  // must rethrow!
} catch (e: Exception) {
    logger.error("Failed", e)
}

// ALSO GOOD: use runCatching carefully
runCatching { suspendingWork() }
    .onFailure { e ->
        if (e is CancellationException) throw e
        logger.error("Failed", e)
    }
```
- Confidence 85%: catching `Exception` or `Throwable` in a suspend function almost always catches `CancellationException`

**Compose unstable parameters**
```kotlin
// BAD: lambda causes recomposition every time
@Composable
fun ItemList(items: List<Item>, onClick: (Item) -> Unit) {
    // List and lambda are unstable -> recomposes every parent recomposition
}

// GOOD: stable types
@Composable
fun ItemList(items: ImmutableList<Item>, onClick: (Item) -> Unit) {
    // ImmutableList is stable; lambda should be remembered at call site
}
```
- Flag `List`, `Map`, `Set` parameters in Composable functions (use `kotlinx.collections.immutable`)

**NavController passed deep into composable tree**
```kotlin
// BAD: tight coupling to navigation
@Composable
fun UserCard(user: User, navController: NavController) {
    Button(onClick = { navController.navigate("details/${user.id}") })
}

// GOOD: event callback
@Composable
fun UserCard(user: User, onNavigateToDetails: (String) -> Unit) {
    Button(onClick = { onNavigateToDetails(user.id) })
}
```

**remember {} missing keys**
```kotlin
// BAD: stale computation when input changes
val formatted = remember { formatCurrency(amount) }

// GOOD: recomputes when amount changes
val formatted = remember(amount) { formatCurrency(amount) }
```

### Step 4 -- Medium Findings (severity: minor)

**!! (non-null assertion) overuse**
```kotlin
// BAD: crash if null
val name = user!!.name

// GOOD: safe handling
val name = user?.name ?: "Unknown"
```
- Confidence 70% in production code, 40% in test code
- Acceptable after explicit null check in the same scope

**Java-style patterns in Kotlin**
- `getInstance()` singleton -> `object` declaration
- JavaBean getters/setters -> Kotlin properties
- `static` utility class -> top-level functions or `object`
- `StringBuilder` manual building -> string templates

**Hardcoded strings in UI**
```kotlin
// BAD: not localizable
Text("Submit Order")

// GOOD: string resource
Text(stringResource(R.string.submit_order))
```

**Missing sealed class/interface for state modeling**
- Multiple boolean flags (`isLoading`, `isError`, `hasData`) instead of sealed state hierarchy

### Step 5 -- Android Security Checks

**Exported components without permission protection**
```xml
<!-- BAD: any app can start this -->
<activity android:name=".DeepLinkActivity" android:exported="true" />

<!-- GOOD: protected -->
<activity
    android:name=".DeepLinkActivity"
    android:exported="true"
    android:permission="com.example.DEEP_LINK" />
```
- Check `AndroidManifest.xml` for `exported="true"` without `permission` attribute

**WebView JavaScript bridge exposure**
```kotlin
// BAD: exposes Kotlin objects to JS
webView.addJavascriptInterface(bridge, "Android")
webView.settings.javaScriptEnabled = true

// Requires: validate URL before enabling JS, restrict interface methods with @JavascriptInterface
```
- Confidence 80% if URL is not validated before loading

**Cleartext traffic in production**
- `android:usesCleartextTraffic="true"` in manifest
- HTTP URLs in network calls without TLS

### Step 6 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| ktlint | `ktlint --reporter=json` | Code style findings |
| detekt | `detekt --report xml` | Complexity, style, potential bugs |
| Android Lint | `./gradlew lint` | Android-specific issues |
| Dependency Check | `./gradlew dependencyCheckAnalyze` | Vulnerable dependencies |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-kotlin-N
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

---

# Handler: Language -- Python

## Purpose

Language-specific review for Python code. Supplements the 8-concern review agents with Python-idiomatic checks, framework-aware patterns, and diagnostic tool integration.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Python Scope

1. Identify `.py` files in the diff
2. If no Python files, skip this handler entirely
3. Detect frameworks from imports:
   - `django` imports -> enable Django checks
   - `fastapi` imports -> enable FastAPI checks
   - `flask` imports -> enable Flask checks
   - `sqlalchemy` imports -> enable SQLAlchemy checks
4. Read `.ai-engineering/contexts/languages/python.md` if not already loaded

### Step 2 -- Critical Findings (severity: critical)

Scan every changed line for:

**SQL Injection via f-strings or format()**
```python
# BAD: injectable
cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
cursor.execute("SELECT * FROM users WHERE id = %s" % user_id)
cursor.execute("SELECT * FROM users WHERE id = {}".format(user_id))

# GOOD: parameterized
cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
```

**Command Injection via subprocess**
```python
# BAD: shell=True with user input
subprocess.run(f"ls {user_input}", shell=True)
os.system(f"echo {user_input}")

# GOOD: argument list, no shell
subprocess.run(["ls", user_input], shell=False)
```

**eval/exec with untrusted input**
- Flag any `eval()` or `exec()` call
- Confidence 90% if argument includes variables, 60% if string literal

**Unsafe deserialization**
- `pickle.loads()`, `pickle.load()` on untrusted data
- `yaml.load()` without `Loader=SafeLoader` or `yaml.safe_load()`
- `marshal.loads()`, `shelve.open()` on user-controlled paths

**Bare except swallowing errors**
```python
# BAD: swallows everything including KeyboardInterrupt
except:
    pass

# GOOD: specific exceptions
except ValueError:
    logger.warning("Invalid value")
```

### Step 3 -- High Findings (severity: major)

**Missing type hints on public functions**
- Public functions (no leading underscore) missing parameter or return type annotations
- Confidence 70% for library code, 50% for scripts

**Mutable default arguments**
```python
# BAD: shared mutable default
def append_to(item, target=[]):
    target.append(item)
    return target

# GOOD: None sentinel
def append_to(item, target=None):
    if target is None:
        target = []
    target.append(item)
    return target
```

**Imperative loops replaceable with comprehensions**
- `for` loops that build a list via `.append()` -> list comprehension
- Only flag when the comprehension would be a single readable expression

**Raw string concatenation for paths**
- `path + "/" + filename` -> `pathlib.Path` or `os.path.join()`

### Step 4 -- Medium Findings (severity: minor)

**PEP 8 violations not caught by formatter**
- Semantic naming violations (single-letter variables outside comprehensions/lambdas)
- Module-level code organization (imports, constants, classes, functions)

**print() instead of logging**
- `print()` in library/application code -> `logging.getLogger(__name__)`
- Acceptable in CLI entry points and scripts

**Identity checks for singletons**
```python
# BAD
if value == None:
if value == True:

# GOOD
if value is None:
if value is True:
```

**Unnecessary else after return**
```python
# BAD
if condition:
    return x
else:
    return y

# GOOD
if condition:
    return x
return y
```

### Step 5 -- Framework-Specific Checks

**Django**
- Missing `select_related()` / `prefetch_related()` in querysets accessed in loops (N+1)
- Database writes outside `transaction.atomic()` in multi-step operations
- Raw SQL in views without parameterization
- Missing `@login_required` or permission checks on views
- `Model.objects.all()` without pagination in API views

**FastAPI**
- Overly permissive CORS (`allow_origins=["*"]` in production)
- Missing Pydantic model validation on request bodies
- Synchronous blocking calls in async endpoints
- Missing `status_code` on response models
- `@app.on_event("startup")` instead of lifespan context manager

**Flask**
- `app.secret_key` hardcoded in source
- Missing CSRF protection on forms
- `render_template_string()` with user input (SSTI)
- Debug mode enabled in production config

### Step 6 -- Diagnostic Tool Cross-Reference

When feasible, validate findings against tool output:

| Tool | Command | Validates |
|------|---------|-----------|
| mypy | `mypy --strict {files}` | Type safety findings |
| ruff | `ruff check {files}` | Style, import, complexity findings |
| bandit | `bandit -r {files}` | Security findings |
| pytest | `pytest --cov --cov-report=term-missing` | Test coverage gaps |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-python-N
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

---

# Handler: Language -- Rust

## Purpose

Language-specific review for Rust code. Supplements the 8-concern review agents with ownership-aware checks, unsafe block auditing, error handling patterns, and performance-sensitive idiom validation.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Detect Rust Scope

1. Identify `.rs` files in the diff
2. If no Rust files, skip this handler entirely
3. Check `Cargo.toml` for dependencies and edition
4. Detect usage patterns from imports:
   - `tokio` / `async-std` -> enable async runtime checks
   - `actix-web` / `axum` / `rocket` -> enable web framework checks
   - `diesel` / `sqlx` / `sea-orm` -> enable database checks
   - `serde` -> enable serialization checks
5. Read `.ai-engineering/contexts/languages/rust.md` if not already loaded

### Step 2 -- Critical Findings (severity: critical)

**unwrap() / expect() in production code**
```rust
// BAD: panics at runtime
let value = map.get("key").unwrap();
let file = File::open("config.toml").unwrap();

// GOOD: propagate or handle
let value = map.get("key").ok_or_else(|| Error::MissingKey("key"))?;
let file = File::open("config.toml").context("failed to open config")?;
```
- Confidence 90% in `src/` (non-test) code
- Acceptable in tests, examples, build scripts, and provably-safe cases with documented invariant

**unsafe blocks without SAFETY comment**
```rust
// BAD: no justification
unsafe {
    ptr::write(dest, value);
}

// GOOD: documented invariant
// SAFETY: `dest` is valid for writes because it was allocated on line 42
// and has not been deallocated. Alignment is guaranteed by the layout.
unsafe {
    ptr::write(dest, value);
}
```
- Every `unsafe` block must have a `// SAFETY:` comment explaining why it is sound

**Discarding #[must_use] values**
```rust
// BAD: Result silently ignored
let _ = sender.send(message);  // send returns Result
map.insert(key, value);        // when return value matters

// GOOD: handle the result
sender.send(message).map_err(|e| warn!("send failed: {e}"))?;
if let Some(old) = map.insert(key, value) {
    debug!("replaced existing value: {old:?}");
}
```
- Flag `let _ =` on `#[must_use]` types: `Result`, `MustUse`, iterator adaptors

**Return Err without context**
```rust
// BAD: loses context chain
fn load_config(path: &Path) -> Result<Config> {
    let content = fs::read_to_string(path)?;  // bare ? loses "what were we doing"
    toml::from_str(&content)?;
}

// GOOD: contextual errors (anyhow or thiserror)
fn load_config(path: &Path) -> Result<Config> {
    let content = fs::read_to_string(path)
        .with_context(|| format!("reading config from {}", path.display()))?;
    toml::from_str(&content).context("parsing config TOML")?;
}
```

**panic!, todo!, unreachable! in production paths**
```rust
// BAD: process crashes
panic!("unexpected state");
todo!("implement later");
unreachable!();  // without proof

// GOOD: return error or use debug_assert
return Err(Error::UnexpectedState(state));
```
- Acceptable: `unreachable!()` after exhaustive match, `todo!()` behind feature flags in dev branches

### Step 3 -- High Findings (severity: major)

**Unnecessary .clone()**
```rust
// BAD: cloning when a borrow suffices
let name = user.name.clone();
println!("{}", name);

// GOOD: borrow
println!("{}", user.name);
```
- Flag `.clone()` where the cloned value is only read, never mutated or moved into owned context
- Confidence 70% (borrow checker sometimes requires clone for valid reasons)

**String when &str suffices**
```rust
// BAD: unnecessary allocation
fn greet(name: String) {
    println!("Hello, {name}");
}

// GOOD: accepts both &str and String
fn greet(name: &str) {
    println!("Hello, {name}");
}
```
- Flag function parameters that take `String` but never mutate or store it

**Blocking in async context**
```rust
// BAD: blocks the async runtime thread
async fn handle_request() {
    let data = std::fs::read_to_string("file.txt");  // blocking!
    std::thread::sleep(Duration::from_secs(1));       // blocking!
}

// GOOD: async alternatives
async fn handle_request() {
    let data = tokio::fs::read_to_string("file.txt").await;
    tokio::time::sleep(Duration::from_secs(1)).await;
}
```
- Flag `std::fs::*`, `std::thread::sleep`, `std::net::*` inside `async fn`

**Unbounded channels**
```rust
// CAUTION: unbounded can consume unlimited memory
let (tx, rx) = tokio::sync::mpsc::unbounded_channel();

// BETTER: bounded with backpressure
let (tx, rx) = tokio::sync::mpsc::channel(100);
```
- Confidence 60% (unbounded is sometimes intentional for low-volume signals)

### Step 4 -- Medium Findings (severity: minor)

**to_string() / format!() in hot paths**
- Allocations in loops, iterators, or frequently-called functions
- Suggest `write!` to a buffer or `Cow<str>` for conditional allocation

**Vec without with_capacity**
```rust
// BAD: multiple reallocations
let mut items = Vec::new();
for i in 0..known_count {
    items.push(compute(i));
}

// GOOD: pre-allocate
let mut items = Vec::with_capacity(known_count);
```
- Only flag when the size is known or estimable at creation time

**Derive order convention**
```rust
// Convention: Debug, Clone, Copy first; then PartialEq, Eq, Hash; then Serialize, Deserialize
#[derive(Debug, Clone, PartialEq, Eq, Hash, Serialize, Deserialize)]
```
- Confidence 40% (style preference)

**Missing #[must_use] on public functions returning values**
- Public functions that return `Result`, `Option`, or meaningful values without `#[must_use]`

### Step 5 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| cargo clippy | `cargo clippy -- -W clippy::all -W clippy::pedantic` | Idiomatic patterns, performance, correctness |
| cargo-audit | `cargo audit` | Known vulnerabilities in dependencies |
| cargo-deny | `cargo deny check` | License compliance, duplicate deps, advisories |
| cargo test | `cargo test` | Test coverage verification |
| miri | `cargo +nightly miri test` | Undefined behavior in unsafe code |

If a diagnostic tool contradicts a finding, note the discrepancy and adjust confidence accordingly.

## Output Format

```yaml
findings:
  - id: lang-rust-N
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

---

# Handler: Language -- TypeScript

## Purpose

Language-specific review for TypeScript and JavaScript code. Supplements the 8-concern review agents with type-safety checks, framework-aware patterns (React, Node.js, Next.js), and pre-review PR readiness validation.

## Integration

Dispatched as **Step 2b** (between Step 2 dispatch and Step 3 aggregate). Findings use the same YAML format. Language findings receive a **+10% confidence bonus** when corroborated by a concern agent.

## Procedure

### Step 1 -- Pre-Review PR Readiness

Before analyzing code, check PR health:

1. **Detect base branch**: `gh pr view --json baseRefName,headRefName,mergeable,statusCheckRollup`
2. **Check merge readiness**: report conflicting files, failing checks
3. **Run project typecheck**: `npx tsc --noEmit` (or project-specific command from `package.json`)
4. If typecheck fails, report type errors as critical findings before proceeding

### Step 2 -- Detect TypeScript Scope

1. Identify `.ts`, `.tsx`, `.js`, `.jsx` files in the diff
2. If no TypeScript/JavaScript files, skip this handler entirely
3. Detect frameworks from imports and config:
   - `react` imports -> enable React checks
   - `next` imports or `next.config.*` -> enable Next.js checks
   - `express` / `fastify` / `nestjs` imports -> enable Node.js server checks
4. Read `.ai-engineering/contexts/languages/typescript.md` if not already loaded
5. Check `tsconfig.json` for `strict` mode -- if disabled, increase confidence on type findings

### Step 3 -- Critical Findings (severity: critical)

**eval() and Function constructor**
```typescript
// BAD: code injection
eval(userInput);
new Function("return " + userInput)();
setTimeout(userInput, 0); // string overload

// GOOD: parse data, not code
JSON.parse(userInput);
```

**innerHTML XSS**
```typescript
// BAD: XSS vector
element.innerHTML = userInput;
el.outerHTML = `<div>${data}</div>`;

// GOOD: safe alternatives
element.textContent = userInput;
// React: dangerouslySetInnerHTML requires explicit opt-in and sanitization
```

**SQL string concatenation**
```typescript
// BAD: SQL injection
db.query(`SELECT * FROM users WHERE id = '${userId}'`);

// GOOD: parameterized
db.query("SELECT * FROM users WHERE id = $1", [userId]);
```

**Prototype pollution**
```typescript
// BAD: user-controlled key assignment
obj[userKey] = userValue;
Object.assign(target, untrustedSource);
{ ...defaults, ...userInput }  // shallow merge of untrusted data

// Flag when: key or source originates from request body, query params, or headers
```

### Step 4 -- High Findings (severity: major)

**`any` type without justification**
- Flag every `any` annotation not accompanied by a comment explaining why
- Confidence 80% in library code, 60% in test code
- Check for `// eslint-disable-next-line @typescript-eslint/no-explicit-any` without explanation

**Non-null assertion abuse**
```typescript
// BAD: hiding potential null
const name = user!.name;
document.getElementById("root")!.textContent;

// GOOD: explicit handling
const name = user?.name ?? "Unknown";
const el = document.getElementById("root");
if (el) el.textContent = value;
```

**`as` type casts bypassing type safety**
```typescript
// BAD: lying to the compiler
const data = response as UserData;

// GOOD: runtime validation
const data = UserDataSchema.parse(response);
```
- Acceptable for test fixtures with comment; flag in production code

**Async forEach (parallel execution, no await)**
```typescript
// BAD: fires and forgets
items.forEach(async (item) => {
  await processItem(item);
});

// GOOD: sequential
for (const item of items) {
  await processItem(item);
}
// GOOD: parallel with error handling
await Promise.all(items.map((item) => processItem(item)));
```

**Unhandled promise rejections**
- Floating promises (async calls without `await`, `.catch()`, or `void` operator)
- Missing `.catch()` on promise chains in non-async contexts

**JSON.parse without try/catch**
```typescript
// BAD: throws on invalid JSON
const data = JSON.parse(rawInput);

// GOOD: safe parsing
let data: unknown;
try {
  data = JSON.parse(rawInput);
} catch {
  return { error: "Invalid JSON" };
}
```

### Step 5 -- Medium Findings (severity: minor)

**React hooks dependency issues**
- Missing dependencies in `useEffect`, `useMemo`, `useCallback` dep arrays
- Object/array literals in dep arrays (new reference every render)
- Functions defined inside component used as deps without `useCallback`

**console.log in production code**
- `console.log` / `console.debug` in non-test, non-script files
- Acceptable: `console.error`, `console.warn` for error reporting

**Magic numbers**
- Numeric literals in logic without named constants
- Acceptable: 0, 1, -1, common HTTP status codes, array indices

**Missing error boundaries in React trees**
- Component trees without `ErrorBoundary` wrapping async data sources

### Step 6 -- Node.js Server Checks

**readFileSync in request handlers**
```typescript
// BAD: blocks event loop
app.get("/data", (req, res) => {
  const data = fs.readFileSync("large-file.json");
});

// GOOD: async
app.get("/data", async (req, res) => {
  const data = await fs.promises.readFile("large-file.json");
});
```

**Unvalidated process.env access**
```typescript
// BAD: undefined at runtime
const port = process.env.PORT;

// GOOD: validated with fallback or schema
const port = process.env.PORT ?? "3000";
// Better: zod schema validation of entire env
const env = envSchema.parse(process.env);
```

**Missing rate limiting on public endpoints**

**Missing helmet/security headers in Express apps**

### Step 7 -- Diagnostic Tool Cross-Reference

| Tool | Command | Validates |
|------|---------|-----------|
| tsc | `npx tsc --noEmit` | Type safety findings |
| eslint | `npx eslint {files}` | Style, pattern findings |
| vitest/jest | `npx vitest run --coverage` | Test coverage gaps |

## Output Format

```yaml
findings:
  - id: lang-typescript-N
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

---

# Handler: Learn from Reviews

## Purpose

Extract lessons from past reviews to improve future review quality. Continuous improvement loop: reviews teach the reviewer what matters in this codebase.

## Procedure

### Step 1 -- Collect Review History

Gather data from:
1. Recent PR comments: `gh api repos/{owner}/{repo}/pulls?state=closed&per_page=10`
2. Review comments on those PRs
3. Commit messages that reference review feedback (e.g., "address review comment")
4. Decision store entries tagged with review context

### Step 2 -- Identify Patterns

Classify findings by frequency and impact:

```markdown
## Recurring Findings (found 3+ times)
| Finding Pattern | Frequency | Severity | Agent(s) |
|----------------|-----------|----------|----------|
| Missing null check | 7 | major | correctness |
| No error boundary | 4 | major | frontend |
| N+1 query | 3 | critical | performance |

## False Positives (findings that were dismissed)
| Finding Pattern | Times Dismissed | Reason |
|----------------|----------------|--------|
| Complex function | 3 | CLI handlers, acceptable breadth |
```

### Step 3 -- Generate Learnings

For each recurring pattern:
1. Should this become a lint rule? (automate the check)
2. Should this become a standard? (codify in `standards/`)
3. Should the review agent's confidence be adjusted?

For each false positive pattern:
1. Should the review agent skip this in certain contexts?
2. Should the self-challenge protocol catch this?

### Step 4 -- Update Review Config

If actionable learnings exist, recommend updates to:
- Review agent confidence thresholds
- Context-aware skipping rules
- New lint rules or standards

Output as recommendations -- the user decides what to implement.

---

# Handler: Review

## Purpose

Full parallel code review workflow. Dispatches 8 specialized agents, each analyzing the same diff from a different angle, then aggregates findings with self-challenge and corroboration.

## Procedure

### Step 1 -- Gather Context

Before any review agent runs:

1. Run `/ai-explore` on the changed files to produce an Architecture Map
2. Identify the diff scope: `git diff --stat` for file list, `git diff` for full content
3. Detect languages in the diff (file extensions) and read:
   - `.ai-engineering/contexts/languages/{lang}.md` for each language found
   - `.ai-engineering/contexts/frameworks/{framework}.md` if framework imports detected
   - `.ai-engineering/contexts/team/*.md` for team conventions
4. Read `decision-store.json` for relevant architectural decisions

### Step 2 -- Dispatch 8 Agents

Each agent reviews the same diff independently. For each agent:

**Input**:
```
You are reviewing code as the [AGENT] specialist.
Context: [Architecture Map from Step 1]
Diff: [full diff]
Standards: [applicable standards]
Focus: [agent-specific focus area]
```

**Each agent produces**:
```yaml
findings:
  - id: [AGENT]-1
    severity: blocker|critical|major|minor|info
    confidence: 20-100
    file: path/to/file
    line: N
    finding: "What is wrong"
    evidence: "Code snippet or reasoning"
    remediation: "How to fix"
    self_challenge:
      counter: "Why this might be acceptable"
      resolution: "Finding stands|withdrawn|severity adjusted"
      adjusted_confidence: N
```

### Step 3 -- Aggregate and Correlate

After all 8 agents report:

1. **Deduplicate**: merge findings that flag the same line/issue
2. **Corroborate**: when 2+ agents flag the same issue:
   - Merge into one finding with combined evidence
   - Add 20% confidence bonus (capped at 100%)
   - List contributing agents
3. **Filter**: drop solo findings with adjusted_confidence < 40%
   - Exception: solo findings with severity `blocker` or `critical` are never dropped

### Step 4 -- Produce Review Report

```markdown
## Code Review Summary

**Files reviewed**: N
**Findings**: N (blocker: N, critical: N, major: N, minor: N, info: N)
**Corroborated findings**: N (flagged by 2+ agents)

### Blockers (must fix before merge)
[findings with severity: blocker]

### Critical (should fix before merge)
[findings with severity: critical]

### Major (address in this PR or follow-up)
[findings with severity: major]

### Minor (nice to have)
[findings with severity: minor]

### Observations (informational)
[findings with severity: info]

### Dropped Findings (low confidence, for transparency)
[findings that were dropped with reasons]
```

## Agent Specialization Details

### Security Agent
- OWASP Top 10 2025 mapping
- Input validation: SQL injection, XSS, command injection, path traversal
- Authentication: token handling, session management, privilege escalation
- Data exposure: logging sensitive data, error message information leaks
- Dependencies: known CVEs in imports

### Performance Agent
- Query patterns: N+1, missing indexes, full table scans
- Algorithmic: O(n^2) in loops, unnecessary allocations, blocking I/O
- Memory: unbounded collections, missing cleanup, reference cycles
- Bundle: tree-shaking opportunities, code splitting

### Correctness Agent
- Logic: off-by-one, wrong operator, missing early return
- Null safety: unhandled None/null/undefined, optional chaining gaps
- Concurrency: race conditions, deadlocks, lost updates
- Edge cases: empty input, max values, unicode, timezone

### Maintainability Agent
- Complexity: cyclomatic > 10, cognitive > 15, nesting > 3 levels
- Naming: unclear variable/function names, misleading names
- Structure: god functions (> 50 lines), god classes, hidden coupling
- DRY: duplicated logic (> 3 occurrences)

### Testing Agent
- Missing tests for new public functions
- Weak assertions (assertTrue with no condition, no assert at all)
- Testing implementation details instead of behavior
- Missing edge case tests for changed code

### Compatibility Agent
- Public API changes without deprecation
- Breaking changes in function signatures
- Version compatibility (Python 3.9+, Node 18+, etc.)
- Config format changes

### Architecture Agent
- Layer violations (controller calling repository directly)
- Circular dependencies (import cycles)
- Pattern inconsistency (some modules use pattern A, this uses B)
- Missing abstractions (concrete dependencies where interfaces belong)

### Frontend Agent (skip if no frontend files in diff)
- Missing aria labels on interactive elements
- Layout shift risks (images without dimensions, dynamic content)
- Unhandled loading/error/empty states
- Accessibility: color contrast, keyboard navigation, screen reader support
